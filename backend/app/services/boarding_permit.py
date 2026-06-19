from datetime import datetime
from typing import Sequence

from fastapi import HTTPException
from sqlalchemy import and_
from sqlalchemy.orm import Session

from app.models.boarding_permit import BoardingPermit
from app.models.boarding_personnel import BoardingPersonnel
from app.models.maintenance_plan import MaintenancePlan
from app.models.operation_window import OperationWindow
from app.models.personnel_certificate import PersonnelCertificate
from app.models.sea_condition import SeaCondition
from app.schemas.boarding_permit import (
    BoardingPermitCreate,
    BoardingPersonnelItem,
    CaptainConfirmRequest,
    RejectRequest,
    SafetyClearRequest,
)


class BoardingPermitService:
    def create_permit(self, db: Session, data: BoardingPermitCreate) -> BoardingPermit:
        plan = db.query(MaintenancePlan).filter(MaintenancePlan.id == data.maintenance_plan_id).first()
        if not plan:
            raise HTTPException(status_code=404, detail="运维计划不存在")
        if plan.status not in ("approved", "submitted"):
            raise HTTPException(status_code=422, detail="运维计划状态不允许提交登乘许可")

        permit = BoardingPermit(
            permit_code=data.permit_code,
            maintenance_plan_id=data.maintenance_plan_id,
            vessel_id=data.vessel_id,
            boarding_date=data.boarding_date,
            status="submitted",
            submitted_by=data.submitted_by,
        )
        db.add(permit)
        db.flush()

        for p in data.personnel:
            bp = BoardingPersonnel(
                boarding_permit_id=permit.id,
                personnel_id=p.personnel_id,
                role_on_board=p.role_on_board,
            )
            db.add(bp)

        db.commit()
        db.refresh(permit)
        return permit

    def _get_permit_or_404(self, db: Session, permit_id: str) -> BoardingPermit:
        permit = db.query(BoardingPermit).filter(BoardingPermit.id == permit_id).first()
        if not permit:
            raise HTTPException(status_code=404, detail="登乘许可不存在")
        return permit

    def _get_permit_personnel_ids(self, db: Session, permit_id: str) -> list[str]:
        rows = db.query(BoardingPersonnel.personnel_id).filter(
            BoardingPersonnel.boarding_permit_id == permit_id
        ).all()
        return [r[0] for r in rows]

    def captain_confirm(self, db: Session, permit_id: str, req: CaptainConfirmRequest) -> BoardingPermit:
        permit = self._get_permit_or_404(db, permit_id)
        if permit.status != "submitted":
            raise HTTPException(status_code=422, detail="只有已提交状态的许可才能由船长确认")

        self._check_sea_condition(db, permit)
        self._check_vessel_capacity(db, permit)

        permit.status = "captain_confirmed"
        permit.captain_id = req.captain_id
        permit.captain_confirmed_at = datetime.utcnow()
        db.commit()
        db.refresh(permit)
        return permit

    def safety_clear(self, db: Session, permit_id: str, req: SafetyClearRequest) -> BoardingPermit:
        permit = self._get_permit_or_404(db, permit_id)
        if permit.status != "captain_confirmed":
            raise HTTPException(status_code=422, detail="只有船长已确认的许可才能由安全员放行")

        self._check_certificates(db, permit)
        self._check_position_conflict(db, permit)

        permit.status = "safety_cleared"
        permit.safety_officer_id = req.safety_officer_id
        permit.safety_cleared_at = datetime.utcnow()
        db.commit()
        db.refresh(permit)
        return permit

    def reject(self, db: Session, permit_id: str, req: RejectRequest) -> BoardingPermit:
        permit = self._get_permit_or_404(db, permit_id)
        if permit.status not in ("submitted", "captain_confirmed"):
            raise HTTPException(status_code=422, detail="当前状态不允许驳回")
        permit.status = "rejected"
        permit.rejection_reason = req.rejection_reason
        db.commit()
        db.refresh(permit)
        return permit

    def _check_sea_condition(self, db: Session, permit: BoardingPermit):
        latest = (
            db.query(SeaCondition)
            .filter(SeaCondition.vessel_id == permit.vessel_id)
            .order_by(SeaCondition.record_time.desc())
            .first()
        )
        if not latest:
            raise HTTPException(status_code=422, detail="无海况记录，不能登船")

        windows = (
            db.query(OperationWindow)
            .filter(
                OperationWindow.work_position_id == permit.maintenance_plan_id,
                OperationWindow.start_time <= permit.boarding_date,
                OperationWindow.end_time >= permit.boarding_date,
            )
            .all()
        )

        if not windows:
            if not latest.is_navigable:
                raise HTTPException(status_code=422, detail="海况不满足窗口要求，不能登船")
            return

        for w in windows:
            if latest.wave_height > w.max_wave_height:
                raise HTTPException(
                    status_code=422,
                    detail=f"浪高{latest.wave_height}m超过窗口上限{w.max_wave_height}m，不能登船",
                )
            if latest.wind_speed > w.max_wind_speed:
                raise HTTPException(
                    status_code=422,
                    detail=f"风速{latest.wind_speed}m/s超过窗口上限{w.max_wind_speed}m/s，不能登船",
                )
            if latest.visibility < w.min_visibility:
                raise HTTPException(
                    status_code=422,
                    detail=f"能见度{latest.visibility}km低于窗口下限{w.min_visibility}km，不能登船",
                )

    def _check_vessel_capacity(self, db: Session, permit: BoardingPermit):
        from app.models.vessel import Vessel

        vessel = db.query(Vessel).filter(Vessel.id == permit.vessel_id).first()
        if not vessel:
            raise HTTPException(status_code=404, detail="船舶不存在")

        crew_count = (
            db.query(BoardingPersonnel)
            .filter(BoardingPersonnel.boarding_permit_id == permit.id)
            .count()
        )
        if crew_count > vessel.capacity:
            raise HTTPException(
                status_code=422,
                detail=f"登乘人数{crew_count}超过船舶载员{vessel.capacity}人",
            )

    def _check_certificates(self, db: Session, permit: BoardingPermit):
        personnel_ids = self._get_permit_personnel_ids(db, permit.id)
        if not personnel_ids:
            raise HTTPException(status_code=422, detail="登乘名单为空")

        today = datetime.utcnow().date()
        for pid in personnel_ids:
            certs = (
                db.query(PersonnelCertificate)
                .filter(PersonnelCertificate.personnel_id == pid)
                .all()
            )
            if not certs:
                raise HTTPException(
                    status_code=422,
                    detail=f"人员{pid}无任何证书，不能放行",
                )
            for c in certs:
                if c.expiry_date < today:
                    raise HTTPException(
                        status_code=422,
                        detail=f"人员{pid}的证书{c.cert_type}({c.cert_number})已于{c.expiry_date}过期，不能放行",
                    )

    def _check_position_conflict(self, db: Session, permit: BoardingPermit):
        plan = db.query(MaintenancePlan).filter(MaintenancePlan.id == permit.maintenance_plan_id).first()
        if not plan:
            return

        if plan.risk_level != "high":
            return

        conflicting = (
            db.query(BoardingPermit)
            .join(MaintenancePlan, BoardingPermit.maintenance_plan_id == MaintenancePlan.id)
            .filter(
                MaintenancePlan.work_position_id == plan.work_position_id,
                MaintenancePlan.risk_level == "high",
                BoardingPermit.status.in_(["submitted", "captain_confirmed", "safety_cleared"]),
                BoardingPermit.id != permit.id,
                BoardingPermit.boarding_date == permit.boarding_date,
            )
            .first()
        )
        if conflicting:
            raise HTTPException(
                status_code=422,
                detail=f"作业机位{plan.work_position_id}已有高风险作业在进行，不能重复派队",
            )

    def get_permit_personnel(self, db: Session, permit_id: str) -> list[BoardingPersonnelItem]:
        rows = db.query(BoardingPersonnel).filter(
            BoardingPersonnel.boarding_permit_id == permit_id
        ).all()
        return [BoardingPersonnelItem(personnel_id=r.personnel_id, role_on_board=r.role_on_board) for r in rows]


boarding_permit_service = BoardingPermitService()
