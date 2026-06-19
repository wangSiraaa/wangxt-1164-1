from datetime import datetime

import pytest
from fastapi import HTTPException
from sqlalchemy.orm import Session

from app.models import (
    BoardingPermit,
    BoardingPersonnel,
    MaintenancePlan,
    OperationWindow,
    Personnel,
    SeaCondition,
    Vessel,
    WorkPosition,
)
from app.schemas.boarding_permit import CaptainConfirmRequest, SafetyClearRequest
from app.services.boarding_permit import boarding_permit_service


class TestSeaConditionWindowCheck:
    def test_sea_condition_ok_captain_confirm_success(
        self,
        db: Session,
        seed_permit_submitted: BoardingPermit,
        seed_operation_window: OperationWindow,
        seed_sea_condition_ok: SeaCondition,
        captain_confirm_request: CaptainConfirmRequest,
    ):
        result = boarding_permit_service.captain_confirm(db, seed_permit_submitted.id, captain_confirm_request)
        assert result.status == "captain_confirmed"
        assert result.captain_id == captain_confirm_request.captain_id

    def test_wave_height_exceeded_blocked_and_message(
        self,
        db: Session,
        seed_permit_submitted: BoardingPermit,
        seed_operation_window: OperationWindow,
        seed_sea_condition_wave_high: SeaCondition,
        captain_confirm_request: CaptainConfirmRequest,
    ):
        with pytest.raises(HTTPException) as exc_info:
            boarding_permit_service.captain_confirm(db, seed_permit_submitted.id, captain_confirm_request)
        assert exc_info.value.status_code == 422
        assert "浪高" in exc_info.value.detail
        assert "2.5m超过窗口上限1.5m" in exc_info.value.detail

    def test_all_three_violations_aggregated_in_one_message(
        self,
        db: Session,
        seed_permit_submitted: BoardingPermit,
        seed_operation_window: OperationWindow,
        seed_sea_condition_all_violations: SeaCondition,
        captain_confirm_request: CaptainConfirmRequest,
    ):
        with pytest.raises(HTTPException) as exc_info:
            boarding_permit_service.captain_confirm(db, seed_permit_submitted.id, captain_confirm_request)
        assert exc_info.value.status_code == 422
        detail = exc_info.value.detail
        assert "浪高" in detail
        assert "风速" in detail
        assert "能见度" in detail
        assert "；" in detail
        assert detail.count("超过") + detail.count("低于") >= 3

    def test_no_sea_condition_record_blocked(
        self,
        db: Session,
        seed_permit_submitted: BoardingPermit,
        seed_operation_window: OperationWindow,
        captain_confirm_request: CaptainConfirmRequest,
    ):
        with pytest.raises(HTTPException) as exc_info:
            boarding_permit_service.captain_confirm(db, seed_permit_submitted.id, captain_confirm_request)
        assert exc_info.value.status_code == 422
        assert "无海况记录" in exc_info.value.detail

    def test_maintenance_plan_not_found_blocked(
        self,
        db: Session,
        seed_permit_submitted: BoardingPermit,
        seed_sea_condition_ok: SeaCondition,
        seed_operation_window: OperationWindow,
        captain_confirm_request: CaptainConfirmRequest,
    ):
        db.query(MaintenancePlan).filter(MaintenancePlan.id == seed_permit_submitted.maintenance_plan_id).delete()
        db.flush()
        with pytest.raises(HTTPException) as exc_info:
            boarding_permit_service.captain_confirm(db, seed_permit_submitted.id, captain_confirm_request)
        assert exc_info.value.status_code == 422
        assert "运维计划不存在" in exc_info.value.detail

    def test_window_queried_by_plan_work_position_id_not_plan_id(
        self,
        db: Session,
        seed_permit_submitted: BoardingPermit,
        seed_maintenance_plan: MaintenancePlan,
        seed_work_position: WorkPosition,
        seed_sea_condition_ok: SeaCondition,
        captain_confirm_request: CaptainConfirmRequest,
    ):
        other_wp = WorkPosition(code="WP-999", name="错误机位B99", risk_level="low", is_active=True)
        db.add(other_wp)
        db.flush()

        wrong_window = OperationWindow(
            work_position_id=other_wp.id,
            start_time=datetime(2025, 1, 15, 6, 0, 0),
            end_time=datetime(2025, 1, 15, 18, 0, 0),
            max_wave_height=99.0,
            max_wind_speed=999.0,
            min_visibility=0.0,
        )
        db.add(wrong_window)
        db.flush()

        strict_window = OperationWindow(
            work_position_id=seed_maintenance_plan.work_position_id,
            start_time=datetime(2025, 1, 15, 6, 0, 0),
            end_time=datetime(2025, 1, 15, 18, 0, 0),
            max_wave_height=0.5,
            max_wind_speed=1.0,
            min_visibility=10.0,
        )
        db.add(strict_window)
        db.flush()

        with pytest.raises(HTTPException) as exc_info:
            boarding_permit_service.captain_confirm(db, seed_permit_submitted.id, captain_confirm_request)
        assert exc_info.value.status_code == 422
        assert "海况不满足作业窗口要求" in exc_info.value.detail
        assert seed_maintenance_plan.work_position_id == seed_work_position.id

    def test_no_window_and_not_navigable_blocked(
        self,
        db: Session,
        seed_permit_submitted: BoardingPermit,
        captain_confirm_request: CaptainConfirmRequest,
    ):
        sc = SeaCondition(
            vessel_id=seed_permit_submitted.vessel_id,
            record_time=datetime(2025, 1, 15, 7, 0, 0),
            wave_height=1.0,
            wind_speed=5.0,
            visibility=5.0,
            sea_state="calm",
            is_navigable=False,
            recorder_name="测试员",
        )
        db.add(sc)
        db.flush()

        with pytest.raises(HTTPException) as exc_info:
            boarding_permit_service.captain_confirm(db, seed_permit_submitted.id, captain_confirm_request)
        assert exc_info.value.status_code == 422
        assert "无可用作业窗口" in exc_info.value.detail


class TestCertificateCheck:
    def test_certificate_expired_blocked(
        self,
        db: Session,
        seed_permit_submitted: BoardingPermit,
        seed_certificate_expired,
        seed_safety_officer: Personnel,
    ):
        seed_permit_submitted.status = "captain_confirmed"
        seed_permit_submitted.captain_id = "captain-uuid"
        db.flush()

        req = SafetyClearRequest(safety_officer_id=seed_safety_officer.id)
        with pytest.raises(HTTPException) as exc_info:
            boarding_permit_service.safety_clear(db, seed_permit_submitted.id, req)
        assert exc_info.value.status_code == 422
        assert "过期" in exc_info.value.detail

    def test_valid_certificate_passed(
        self,
        db: Session,
        seed_permit_submitted: BoardingPermit,
        seed_certificate_valid,
        seed_safety_officer: Personnel,
        seed_work_position: WorkPosition,
    ):
        seed_permit_submitted.status = "captain_confirmed"
        seed_permit_submitted.captain_id = "captain-uuid"
        db.flush()

        req = SafetyClearRequest(safety_officer_id=seed_safety_officer.id)
        result = boarding_permit_service.safety_clear(db, seed_permit_submitted.id, req)
        assert result.status == "safety_cleared"


class TestHighRiskPositionConflict:
    def test_same_position_high_risk_conflict_blocked(
        self,
        db: Session,
        seed_permit_submitted: BoardingPermit,
        seed_maintenance_plan: MaintenancePlan,
        seed_certificate_valid,
        seed_safety_officer: Personnel,
        seed_crew: Personnel,
        seed_vessel: Vessel,
        seed_work_position: WorkPosition,
    ):
        existing_plan = MaintenancePlan(
            plan_code="MP-2025-CONFLICT",
            title="冲突计划",
            work_position_id=seed_work_position.id,
            plan_date=datetime(2025, 1, 15).date(),
            risk_level="high",
            status="approved",
            created_by="其他",
        )
        db.add(existing_plan)
        db.flush()

        existing_permit = BoardingPermit(
            permit_code="BP-CONFLICT",
            maintenance_plan_id=existing_plan.id,
            vessel_id=seed_vessel.id,
            boarding_date=seed_permit_submitted.boarding_date,
            status="captain_confirmed",
            submitted_by="其他",
        )
        db.add(existing_permit)
        db.flush()
        bp = BoardingPersonnel(boarding_permit_id=existing_permit.id, personnel_id=seed_crew.id, role_on_board="船员")
        db.add(bp)
        db.flush()

        seed_permit_submitted.status = "captain_confirmed"
        seed_permit_submitted.captain_id = "captain-uuid"
        db.flush()

        req = SafetyClearRequest(safety_officer_id=seed_safety_officer.id)
        with pytest.raises(HTTPException) as exc_info:
            boarding_permit_service.safety_clear(db, seed_permit_submitted.id, req)
        assert exc_info.value.status_code == 422
        assert "高风险作业在进行" in exc_info.value.detail

    def test_different_position_no_conflict(
        self,
        db: Session,
        seed_permit_submitted: BoardingPermit,
        seed_maintenance_plan: MaintenancePlan,
        seed_certificate_valid,
        seed_safety_officer: Personnel,
        seed_crew: Personnel,
        seed_vessel: Vessel,
    ):
        other_wp = WorkPosition(code="WP-OTHER", name="其他机位", risk_level="high", is_active=True)
        db.add(other_wp)
        db.flush()

        other_plan = MaintenancePlan(
            plan_code="MP-OTHER",
            title="其他机位计划",
            work_position_id=other_wp.id,
            plan_date=datetime(2025, 1, 15).date(),
            risk_level="high",
            status="approved",
            created_by="其他",
        )
        db.add(other_plan)
        db.flush()

        other_permit = BoardingPermit(
            permit_code="BP-OTHER",
            maintenance_plan_id=other_plan.id,
            vessel_id=seed_vessel.id,
            boarding_date=seed_permit_submitted.boarding_date,
            status="captain_confirmed",
            submitted_by="其他",
        )
        db.add(other_permit)
        db.flush()

        seed_permit_submitted.status = "captain_confirmed"
        seed_permit_submitted.captain_id = "captain-uuid"
        db.flush()

        req = SafetyClearRequest(safety_officer_id=seed_safety_officer.id)
        result = boarding_permit_service.safety_clear(db, seed_permit_submitted.id, req)
        assert result.status == "safety_cleared"
