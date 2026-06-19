from datetime import datetime, timedelta
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
from app.models.vessel import Vessel
from app.models.work_position import WorkPosition
from app.schemas.boarding_permit import (
    BoardingPermitCreate,
    BoardingPersonnelItem,
    CaptainConfirmRequest,
    CaptainRejectRequest,
    CheckResult,
    PersonnelUpdateRequest,
    PreCheckResponse,
    RescheduleRequest,
    RejectRequest,
    SafetyClearRequest,
)


RISK_LEVEL_ORDER = {"low": 1, "medium": 2, "high": 3}


class BoardingPermitService:
    def create_permit(self, db: Session, data: BoardingPermitCreate) -> BoardingPermit:
        plan = db.query(MaintenancePlan).filter(MaintenancePlan.id == data.maintenance_plan_id).first()
        if not plan:
            raise HTTPException(status_code=404, detail="运维计划不存在")
        if plan.status not in ("approved", "submitted"):
            raise HTTPException(status_code=422, detail="运维计划状态不允许提交登乘许可")

        pre_check = self._pre_submit_check(db, data)
        if not pre_check.all_passed:
            errors = []
            if not pre_check.certificate_check.passed:
                errors.extend(pre_check.certificate_check.details)
            if not pre_check.position_risk_check.passed:
                errors.extend(pre_check.position_risk_check.details)
            if not pre_check.same_day_high_risk_check.passed:
                errors.extend(pre_check.same_day_high_risk_check.details)
            raise HTTPException(
                status_code=422,
                detail="提交前检查未通过：" + "；".join(errors),
            )

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

    def pre_check(self, db: Session, data: BoardingPermitCreate) -> PreCheckResponse:
        return self._pre_submit_check(db, data)

    def _pre_submit_check(self, db: Session, data: BoardingPermitCreate) -> PreCheckResponse:
        plan = db.query(MaintenancePlan).filter(MaintenancePlan.id == data.maintenance_plan_id).first()
        work_position = (
            db.query(WorkPosition).filter(WorkPosition.id == plan.work_position_id).first()
            if plan
            else None
        )

        cert_check = self._check_certificates_for_position(
            db, [p.personnel_id for p in data.personnel], work_position
        )
        pos_risk_check = self._check_certificate_risk_match(
            db, [p.personnel_id for p in data.personnel], work_position
        )
        same_day_check = self._check_same_day_high_risk(
            db, plan.work_position_id if plan else None, data.boarding_date, None
        )

        return PreCheckResponse(
            certificate_check=cert_check,
            position_risk_check=pos_risk_check,
            same_day_high_risk_check=same_day_check,
            all_passed=cert_check.passed and pos_risk_check.passed and same_day_check.passed,
        )

    def _check_certificates_for_position(
        self, db: Session, personnel_ids: list[str], work_position: WorkPosition | None
    ) -> CheckResult:
        if not personnel_ids:
            return CheckResult(passed=False, message="登乘名单为空", details=["登乘人员名单不能为空"])
        if not work_position:
            return CheckResult(passed=False, message="机位不存在", details=["关联的作业机位不存在"])

        today = datetime.utcnow().date()
        details: list[str] = []

        for pid in personnel_ids:
            certs = (
                db.query(PersonnelCertificate)
                .filter(
                    PersonnelCertificate.personnel_id == pid,
                    PersonnelCertificate.is_valid == True,
                )
                .all()
            )
            if not certs:
                details.append(f"人员{pid}无任何有效证书，不允许登乘{work_position.name}")
                continue

            has_valid_cert = False
            for c in certs:
                if c.expiry_date >= today:
                    has_valid_cert = True
                    break
            if not has_valid_cert:
                details.append(f"人员{pid}的所有证书均已过期，不允许登乘{work_position.name}")

        if details:
            return CheckResult(
                passed=False,
                message=f"有{len(details)}名人员证书检查未通过",
                details=details,
            )
        return CheckResult(passed=True, message="所有人员证书检查通过", details=[])

    def _check_certificate_risk_match(
        self, db: Session, personnel_ids: list[str], work_position: WorkPosition | None
    ) -> CheckResult:
        if not work_position:
            return CheckResult(passed=False, message="机位不存在", details=["关联的作业机位不存在"])

        position_risk = work_position.risk_level
        details: list[str] = []

        for pid in personnel_ids:
            certs = (
                db.query(PersonnelCertificate)
                .filter(
                    PersonnelCertificate.personnel_id == pid,
                    PersonnelCertificate.is_valid == True,
                )
                .all()
            )
            if not certs:
                continue

            max_allowed_risk = "low"
            for c in certs:
                if RISK_LEVEL_ORDER.get(c.allowed_risk_level, 1) > RISK_LEVEL_ORDER.get(max_allowed_risk, 1):
                    max_allowed_risk = c.allowed_risk_level

            if RISK_LEVEL_ORDER.get(max_allowed_risk, 1) < RISK_LEVEL_ORDER.get(position_risk, 1):
                details.append(
                    f"人员{pid}的最高作业等级为{max_allowed_risk}，"
                    f"不足以承担{work_position.name}的{position_risk}风险作业"
                )

        if details:
            return CheckResult(
                passed=False,
                message=f"有{len(details)}名人员证书等级不足以适应该机位风险",
                details=details,
            )
        return CheckResult(passed=True, message="所有人员证书等级与机位风险匹配", details=[])

    def _check_same_day_high_risk(
        self,
        db: Session,
        work_position_id: str | None,
        boarding_date: datetime,
        exclude_permit_id: str | None,
    ) -> CheckResult:
        if not work_position_id:
            return CheckResult(passed=False, message="机位不存在", details=["关联的作业机位不存在"])

        boarding_date_only = boarding_date.date()

        conflicting = (
            db.query(BoardingPermit)
            .join(MaintenancePlan, BoardingPermit.maintenance_plan_id == MaintenancePlan.id)
            .filter(
                MaintenancePlan.work_position_id == work_position_id,
                MaintenancePlan.risk_level == "high",
                BoardingPermit.status.in_(["submitted", "captain_confirmed", "safety_cleared"]),
                BoardingPermit.id != exclude_permit_id if exclude_permit_id else True,
            )
            .all()
        )

        details: list[str] = []
        for cp in conflicting:
            cp_date = cp.boarding_date.date()
            if cp_date == boarding_date_only:
                details.append(
                    f"该机位同日已有高风险作业许可{cp.permit_code}，禁止重复派队"
                )

        if details:
            return CheckResult(
                passed=False,
                message=f"该机位{boarding_date_only}已有{len(details)}个高风险作业",
                details=details,
            )
        return CheckResult(passed=True, message="同日无高风险作业冲突", details=[])

    def _get_permit_or_404(self, db: Session, permit_id: str) -> BoardingPermit:
        permit = db.query(BoardingPermit).filter(BoardingPermit.id == permit_id).first()
        if not permit:
            raise HTTPException(status_code=404, detail="登乘许可不存在")
        return permit

    def _get_permit_personnel_ids(self, db: Session, permit_id: str) -> list[str]:
        rows = (
            db.query(BoardingPersonnel.personnel_id)
            .filter(BoardingPersonnel.boarding_permit_id == permit_id)
            .all()
        )
        return [r[0] for r in rows]

    def captain_confirm(self, db: Session, permit_id: str, req: CaptainConfirmRequest) -> BoardingPermit:
        permit = self._get_permit_or_404(db, permit_id)
        if permit.status != "submitted":
            raise HTTPException(status_code=422, detail="只有已提交状态的许可才能由船长确认")

        sea_ok, violations = self._check_sea_condition_with_result(db, permit)
        permit.sea_condition_met = sea_ok

        if not sea_ok:
            permit.status = "sea_rejected"
            permit.captain_id = req.captain_id
            permit.captain_confirmed_at = datetime.utcnow()
            permit.rejection_reason = "海况不满足作业窗口要求：" + "；".join(violations)
            permit.reschedule_suggestion = req.reschedule_suggestion
            permit.suggested_boarding_date = req.suggested_boarding_date
            db.commit()
            db.refresh(permit)
            raise HTTPException(
                status_code=422,
                detail={
                    "message": "海况不满足作业窗口要求，不能登船",
                    "violations": violations,
                    "reschedule_suggestion": req.reschedule_suggestion,
                    "suggested_boarding_date": req.suggested_boarding_date.isoformat() if req.suggested_boarding_date else None,
                },
            )

        self._check_vessel_capacity(db, permit)
        permit.capacity_checked = True

        permit.status = "captain_confirmed"
        permit.captain_id = req.captain_id
        permit.captain_confirmed_at = datetime.utcnow()
        permit.reschedule_suggestion = req.reschedule_suggestion
        permit.suggested_boarding_date = req.suggested_boarding_date
        db.commit()
        db.refresh(permit)
        return permit

    def captain_reject(self, db: Session, permit_id: str, req: CaptainRejectRequest) -> BoardingPermit:
        permit = self._get_permit_or_404(db, permit_id)
        if permit.status != "submitted":
            raise HTTPException(status_code=422, detail="只有已提交状态的许可才能由船长驳回")

        permit.status = "captain_rejected"
        permit.captain_id = req.captain_id
        permit.captain_confirmed_at = datetime.utcnow()
        permit.rejection_reason = req.rejection_reason
        permit.reschedule_suggestion = req.reschedule_suggestion
        permit.suggested_boarding_date = req.suggested_boarding_date
        permit.sea_condition_met = False
        db.commit()
        db.refresh(permit)
        return permit

    def reschedule(self, db: Session, permit_id: str, req: RescheduleRequest) -> BoardingPermit:
        permit = self._get_permit_or_404(db, permit_id)
        if permit.status not in ("sea_rejected", "captain_rejected", "rejected"):
            raise HTTPException(status_code=422, detail="只有已驳回状态的许可才能改期")

        permit.boarding_date = req.boarding_date
        permit.status = "submitted"
        permit.rejection_reason = None
        permit.sea_condition_met = None
        permit.capacity_checked = None
        permit.life_equipment_checked = None
        permit.operation_license_checked = None
        permit.captain_id = None
        permit.captain_confirmed_at = None
        permit.safety_officer_id = None
        permit.safety_cleared_at = None
        permit.requires_reapproval = False
        permit.reapproval_reason = None

        db.commit()
        db.refresh(permit)
        return permit

    def safety_clear(self, db: Session, permit_id: str, req: SafetyClearRequest) -> BoardingPermit:
        permit = self._get_permit_or_404(db, permit_id)
        if permit.status != "captain_confirmed":
            raise HTTPException(status_code=422, detail="只有船长已确认的许可才能由安全员放行")

        self._check_vessel_capacity(db, permit)
        permit.capacity_checked = True

        self._check_life_equipment(db, permit, req.life_equipment_count)
        permit.life_equipment_checked = True
        permit.life_equipment_count = req.life_equipment_count

        self._check_operation_license(db, permit, req.operation_license_number)
        permit.operation_license_checked = True
        permit.operation_license_number = req.operation_license_number

        self._check_high_risk_conflict(db, permit)

        personnel_ids = self._get_permit_personnel_ids(db, permit.id)
        plan = db.query(MaintenancePlan).filter(MaintenancePlan.id == permit.maintenance_plan_id).first()
        work_position = (
            db.query(WorkPosition).filter(WorkPosition.id == plan.work_position_id).first()
            if plan
            else None
        )
        cert_check = self._check_certificates_for_position(db, personnel_ids, work_position)
        if not cert_check.passed:
            raise HTTPException(
                status_code=422,
                detail="安全员放行前证书复核未通过：" + "；".join(cert_check.details),
            )

        permit.status = "safety_cleared"
        permit.safety_officer_id = req.safety_officer_id
        permit.safety_cleared_at = datetime.utcnow()
        db.commit()
        db.refresh(permit)
        return permit

    def update_personnel(self, db: Session, permit_id: str, req: PersonnelUpdateRequest) -> BoardingPermit:
        permit = self._get_permit_or_404(db, permit_id)

        old_personnel_ids = set(self._get_permit_personnel_ids(db, permit.id))
        new_personnel_ids = set(p.personnel_id for p in req.personnel)
        personnel_changed = old_personnel_ids != new_personnel_ids

        if permit.status == "safety_cleared" and personnel_changed:
            permit.requires_reapproval = True
            permit.reapproval_reason = req.change_reason
            permit.status = "pending_reapproval"
            permit.personnel_changed = True

        db.query(BoardingPersonnel).filter(BoardingPersonnel.boarding_permit_id == permit_id).delete()

        for p in req.personnel:
            bp = BoardingPersonnel(
                boarding_permit_id=permit.id,
                personnel_id=p.personnel_id,
                role_on_board=p.role_on_board,
            )
            db.add(bp)

        if permit.status != "safety_cleared":
            permit.personnel_changed = personnel_changed

        db.commit()
        db.refresh(permit)
        return permit

    def reapprove(self, db: Session, permit_id: str, safety_officer_id: str) -> BoardingPermit:
        permit = self._get_permit_or_404(db, permit_id)
        if permit.status != "pending_reapproval":
            raise HTTPException(status_code=422, detail="只有待重新审批状态的许可才能执行重新审批")

        personnel_ids = self._get_permit_personnel_ids(db, permit.id)
        plan = db.query(MaintenancePlan).filter(MaintenancePlan.id == permit.maintenance_plan_id).first()
        work_position = (
            db.query(WorkPosition).filter(WorkPosition.id == plan.work_position_id).first()
            if plan
            else None
        )

        cert_check = self._check_certificates_for_position(db, personnel_ids, work_position)
        if not cert_check.passed:
            raise HTTPException(
                status_code=422,
                detail="重新审批时证书检查未通过：" + "；".join(cert_check.details),
            )

        risk_check = self._check_certificate_risk_match(db, personnel_ids, work_position)
        if not risk_check.passed:
            raise HTTPException(
                status_code=422,
                detail="重新审批时风险等级匹配检查未通过：" + "；".join(risk_check.details),
            )

        same_day_check = self._check_same_day_high_risk(
            db, plan.work_position_id if plan else None, permit.boarding_date, permit.id
        )
        if not same_day_check.passed:
            raise HTTPException(
                status_code=422,
                detail="重新审批时同日高风险检查未通过：" + "；".join(same_day_check.details),
            )

        permit.status = "safety_cleared"
        permit.safety_officer_id = safety_officer_id
        permit.safety_cleared_at = datetime.utcnow()
        permit.requires_reapproval = False
        db.commit()
        db.refresh(permit)
        return permit

    def reject(self, db: Session, permit_id: str, req: RejectRequest) -> BoardingPermit:
        permit = self._get_permit_or_404(db, permit_id)
        if permit.status not in ("submitted", "captain_confirmed", "pending_reapproval"):
            raise HTTPException(status_code=422, detail="当前状态不允许驳回")
        permit.status = "rejected"
        permit.rejection_reason = req.rejection_reason
        db.commit()
        db.refresh(permit)
        return permit

    def _check_sea_condition_with_result(self, db: Session, permit: BoardingPermit) -> tuple[bool, list[str]]:
        latest = (
            db.query(SeaCondition)
            .filter(SeaCondition.vessel_id == permit.vessel_id)
            .order_by(SeaCondition.record_time.desc())
            .first()
        )
        if not latest:
            return False, ["无海况记录"]

        plan = db.query(MaintenancePlan).filter(MaintenancePlan.id == permit.maintenance_plan_id).first()
        if not plan:
            return False, ["关联的运维计划不存在"]

        windows = (
            db.query(OperationWindow)
            .filter(
                OperationWindow.work_position_id == plan.work_position_id,
                OperationWindow.start_time <= permit.boarding_date,
                OperationWindow.end_time >= permit.boarding_date,
            )
            .all()
        )

        if not windows:
            if not latest.is_navigable:
                return False, ["该作业机位在登乘时间无可用作业窗口，且当前海况不适航"]
            return True, []

        violations: list[str] = []
        for w in windows:
            if latest.wave_height > w.max_wave_height:
                violations.append(f"浪高{latest.wave_height}m超过窗口上限{w.max_wave_height}m")
            if latest.wind_speed > w.max_wind_speed:
                violations.append(f"风速{latest.wind_speed}m/s超过窗口上限{w.max_wind_speed}m/s")
            if latest.visibility < w.min_visibility:
                violations.append(f"能见度{latest.visibility}km低于窗口下限{w.min_visibility}km")

        return (len(violations) == 0), violations

    def _check_sea_condition(self, db: Session, permit: BoardingPermit):
        ok, violations = self._check_sea_condition_with_result(db, permit)
        if not ok:
            raise HTTPException(
                status_code=422,
                detail="海况不满足作业窗口要求，不能登船：" + "；".join(violations),
            )

    def _check_vessel_capacity(self, db: Session, permit: BoardingPermit):
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

    def _check_life_equipment(self, db: Session, permit: BoardingPermit, equipment_count: int):
        vessel = db.query(Vessel).filter(Vessel.id == permit.vessel_id).first()
        if not vessel:
            raise HTTPException(status_code=404, detail="船舶不存在")

        crew_count = (
            db.query(BoardingPersonnel)
            .filter(BoardingPersonnel.boarding_permit_id == permit.id)
            .count()
        )

        if equipment_count < crew_count:
            raise HTTPException(
                status_code=422,
                detail=f"救生衣数量{equipment_count}件不足，至少需要{crew_count}件（每人1件）",
            )

        if vessel.life_jacket_count < crew_count:
            raise HTTPException(
                status_code=422,
                detail=f"船舶配备救生衣{vessel.life_jacket_count}件不足，至少需要{crew_count}件",
            )

        if vessel.life_raft_count < 1:
            raise HTTPException(
                status_code=422,
                detail="船舶未配备救生筏，不符合安全要求",
            )

        if vessel.first_aid_kit_count < 1:
            raise HTTPException(
                status_code=422,
                detail="船舶未配备急救箱，不符合安全要求",
            )

    def _check_operation_license(self, db: Session, permit: BoardingPermit, license_number: str):
        vessel = db.query(Vessel).filter(Vessel.id == permit.vessel_id).first()
        if not vessel:
            raise HTTPException(status_code=404, detail="船舶不存在")

        if not license_number:
            raise HTTPException(
                status_code=422,
                detail="作业许可证编号不能为空",
            )

        if not vessel.operation_license:
            raise HTTPException(
                status_code=422,
                detail="船舶未配置作业许可证，不符合运营要求",
            )

        if vessel.operation_license != license_number:
            raise HTTPException(
                status_code=422,
                detail=f"作业许可证编号{license_number}与船舶登记的{vessel.operation_license}不符",
            )

    def _check_high_risk_conflict(self, db: Session, permit: BoardingPermit):
        plan = db.query(MaintenancePlan).filter(MaintenancePlan.id == permit.maintenance_plan_id).first()
        if not plan:
            return

        if plan.risk_level != "high":
            return

        check_result = self._check_same_day_high_risk(
            db, plan.work_position_id, permit.boarding_date, permit.id
        )
        if not check_result.passed:
            raise HTTPException(
                status_code=422,
                detail="；".join(check_result.details),
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
        rows = (
            db.query(BoardingPersonnel)
            .filter(BoardingPersonnel.boarding_permit_id == permit_id)
            .all()
        )
        return [BoardingPersonnelItem(personnel_id=r.personnel_id, role_on_board=r.role_on_board) for r in rows]


boarding_permit_service = BoardingPermitService()
