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
    PersonnelCertificate,
    SeaCondition,
    Vessel,
    WorkPosition,
)
from app.schemas.boarding_permit import (
    CaptainConfirmRequest,
    PersonnelUpdateRequest,
    RescheduleRequest,
    SafetyClearRequest,
)
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
        seed_safety_clear_request: SafetyClearRequest,
    ):
        seed_permit_submitted.status = "captain_confirmed"
        seed_permit_submitted.captain_id = "captain-uuid"
        db.flush()

        with pytest.raises(HTTPException) as exc_info:
            boarding_permit_service.safety_clear(db, seed_permit_submitted.id, seed_safety_clear_request)
        assert exc_info.value.status_code == 422
        assert "过期" in exc_info.value.detail

    def test_valid_certificate_passed(
        self,
        db: Session,
        seed_permit_submitted: BoardingPermit,
        seed_certificate_valid,
        seed_safety_officer: Personnel,
        seed_work_position: WorkPosition,
        seed_safety_clear_request: SafetyClearRequest,
    ):
        seed_permit_submitted.status = "captain_confirmed"
        seed_permit_submitted.captain_id = "captain-uuid"
        db.flush()

        result = boarding_permit_service.safety_clear(db, seed_permit_submitted.id, seed_safety_clear_request)
        assert result.status == "safety_cleared"
        assert result.life_equipment_checked == True
        assert result.operation_license_checked == True
        assert result.capacity_checked == True


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
        seed_safety_clear_request: SafetyClearRequest,
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

        with pytest.raises(HTTPException) as exc_info:
            boarding_permit_service.safety_clear(db, seed_permit_submitted.id, seed_safety_clear_request)
        assert exc_info.value.status_code == 422
        assert "高风险作业" in exc_info.value.detail

    def test_different_position_no_conflict(
        self,
        db: Session,
        seed_permit_submitted: BoardingPermit,
        seed_maintenance_plan: MaintenancePlan,
        seed_certificate_valid,
        seed_safety_officer: Personnel,
        seed_crew: Personnel,
        seed_vessel: Vessel,
        seed_safety_clear_request: SafetyClearRequest,
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

        result = boarding_permit_service.safety_clear(db, seed_permit_submitted.id, seed_safety_clear_request)
        assert result.status == "safety_cleared"


class TestPreSubmitCheck:
    def test_pre_check_certificate_valid_passed(
        self,
        db: Session,
        seed_maintenance_plan: MaintenancePlan,
        seed_vessel: Vessel,
        seed_crew: Personnel,
        seed_certificate_valid,
    ):
        from app.schemas.boarding_permit import BoardingPermitCreate, BoardingPersonnelItem

        data = BoardingPermitCreate(
            permit_code="BP-PRECHECK-001",
            maintenance_plan_id=seed_maintenance_plan.id,
            vessel_id=seed_vessel.id,
            boarding_date=datetime(2025, 1, 15, 8, 0, 0),
            submitted_by="运维负责人",
            personnel=[BoardingPersonnelItem(personnel_id=seed_crew.id, role_on_board="船员")],
        )
        result = boarding_permit_service.pre_check(db, data)
        assert result.all_passed == True
        assert result.certificate_check.passed == True
        assert result.position_risk_check.passed == True
        assert result.same_day_high_risk_check.passed == True

    def test_pre_check_certificate_risk_mismatch_blocked(
        self,
        db: Session,
        seed_maintenance_plan: MaintenancePlan,
        seed_vessel: Vessel,
        seed_crew: Personnel,
        seed_certificate_low_risk,
        seed_work_position: WorkPosition,
    ):
        from app.schemas.boarding_permit import BoardingPermitCreate, BoardingPersonnelItem

        seed_work_position.risk_level = "high"
        db.flush()

        data = BoardingPermitCreate(
            permit_code="BP-PRECHECK-002",
            maintenance_plan_id=seed_maintenance_plan.id,
            vessel_id=seed_vessel.id,
            boarding_date=datetime(2025, 1, 15, 8, 0, 0),
            submitted_by="运维负责人",
            personnel=[BoardingPersonnelItem(personnel_id=seed_crew.id, role_on_board="船员")],
        )
        result = boarding_permit_service.pre_check(db, data)
        assert result.all_passed == False
        assert result.position_risk_check.passed == False
        assert "不足以承担" in result.position_risk_check.details[0]

    def test_pre_check_same_day_high_risk_blocked(
        self,
        db: Session,
        seed_maintenance_plan: MaintenancePlan,
        seed_vessel: Vessel,
        seed_crew: Personnel,
        seed_certificate_valid,
        seed_work_position: WorkPosition,
    ):
        from app.schemas.boarding_permit import BoardingPermitCreate, BoardingPersonnelItem

        existing_plan = MaintenancePlan(
            plan_code="MP-EXISTING",
            title="已有高风险计划",
            work_position_id=seed_work_position.id,
            plan_date=datetime(2025, 1, 15).date(),
            risk_level="high",
            status="approved",
            created_by="其他",
        )
        db.add(existing_plan)
        db.flush()

        existing_permit = BoardingPermit(
            permit_code="BP-EXISTING",
            maintenance_plan_id=existing_plan.id,
            vessel_id=seed_vessel.id,
            boarding_date=datetime(2025, 1, 15, 8, 0, 0),
            status="safety_cleared",
            submitted_by="其他",
        )
        db.add(existing_permit)
        db.flush()

        data = BoardingPermitCreate(
            permit_code="BP-PRECHECK-003",
            maintenance_plan_id=seed_maintenance_plan.id,
            vessel_id=seed_vessel.id,
            boarding_date=datetime(2025, 1, 15, 8, 0, 0),
            submitted_by="运维负责人",
            personnel=[BoardingPersonnelItem(personnel_id=seed_crew.id, role_on_board="船员")],
        )
        result = boarding_permit_service.pre_check(db, data)
        assert result.all_passed == False
        assert result.same_day_high_risk_check.passed == False
        assert "禁止重复派队" in result.same_day_high_risk_check.details[0]


class TestCaptainSeaConditionReject:
    def test_sea_condition_rejected_with_reschedule_suggestion(
        self,
        db: Session,
        seed_permit_submitted: BoardingPermit,
        seed_operation_window: OperationWindow,
        seed_sea_condition_wave_high: SeaCondition,
        captain_confirm_request: CaptainConfirmRequest,
    ):
        from datetime import timedelta

        captain_confirm_request.reschedule_suggestion = "建议3天后（1月18日）再安排登乘"
        captain_confirm_request.suggested_boarding_date = (datetime(2025, 1, 15) + timedelta(days=3)).date()

        with pytest.raises(HTTPException) as exc_info:
            boarding_permit_service.captain_confirm(db, seed_permit_submitted.id, captain_confirm_request)
        assert exc_info.value.status_code == 422

        db.refresh(seed_permit_submitted)
        assert seed_permit_submitted.status == "sea_rejected"
        assert seed_permit_submitted.sea_condition_met == False
        assert seed_permit_submitted.reschedule_suggestion == "建议3天后（1月18日）再安排登乘"
        assert seed_permit_submitted.suggested_boarding_date is not None


class TestSafetyClearTripleCheck:
    def test_life_equipment_insufficient_blocked(
        self,
        db: Session,
        seed_permit_submitted: BoardingPermit,
        seed_certificate_valid,
        seed_safety_officer: Personnel,
    ):
        seed_permit_submitted.status = "captain_confirmed"
        seed_permit_submitted.captain_id = "captain-uuid"
        db.flush()

        req = SafetyClearRequest(
            safety_officer_id=seed_safety_officer.id,
            life_equipment_count=0,
            operation_license_number="OP-LICENSE-001",
        )
        with pytest.raises(HTTPException) as exc_info:
            boarding_permit_service.safety_clear(db, seed_permit_submitted.id, req)
        assert exc_info.value.status_code == 422
        assert "救生衣数量" in exc_info.value.detail

    def test_operation_license_mismatch_blocked(
        self,
        db: Session,
        seed_permit_submitted: BoardingPermit,
        seed_certificate_valid,
        seed_safety_officer: Personnel,
    ):
        seed_permit_submitted.status = "captain_confirmed"
        seed_permit_submitted.captain_id = "captain-uuid"
        db.flush()

        req = SafetyClearRequest(
            safety_officer_id=seed_safety_officer.id,
            life_equipment_count=20,
            operation_license_number="WRONG-LICENSE",
        )
        with pytest.raises(HTTPException) as exc_info:
            boarding_permit_service.safety_clear(db, seed_permit_submitted.id, req)
        assert exc_info.value.status_code == 422
        assert "作业许可证编号" in exc_info.value.detail


class TestPersonnelChangeReapproval:
    def test_personnel_change_after_clear_requires_reapproval(
        self,
        db: Session,
        seed_permit_submitted: BoardingPermit,
        seed_certificate_valid,
        seed_safety_clear_request: SafetyClearRequest,
        seed_safety_officer: Personnel,
        seed_crew: Personnel,
    ):
        seed_permit_submitted.status = "captain_confirmed"
        seed_permit_submitted.captain_id = "captain-uuid"
        db.flush()

        permit = boarding_permit_service.safety_clear(db, seed_permit_submitted.id, seed_safety_clear_request)
        assert permit.status == "safety_cleared"

        new_person = Personnel(name="新船员", employee_id="NEW001", role="crew", phone="13800000004")
        db.add(new_person)
        db.flush()

        new_cert = PersonnelCertificate(
            personnel_id=new_person.id,
            cert_type="海上作业证",
            cert_number="CERT-NEW",
            issue_date=datetime(2024, 1, 1).date(),
            expiry_date=(datetime.utcnow() + timedelta(days=365)).date(),
            allowed_risk_level="high",
            is_valid=True,
        )
        db.add(new_cert)
        db.flush()

        update_req = PersonnelUpdateRequest(
            personnel=[
                {"personnel_id": seed_crew.id, "role_on_board": "船员"},
                {"personnel_id": new_person.id, "role_on_board": "船员"},
            ],
            change_reason="人员调整，增加一名船员",
            updated_by="运维负责人",
        )
        updated = boarding_permit_service.update_personnel(db, permit.id, update_req)

        assert updated.status == "pending_reapproval"
        assert updated.requires_reapproval == True
        assert updated.personnel_changed == True
        assert updated.reapproval_reason == "人员调整，增加一名船员"

    def test_reapprove_after_personnel_change(
        self,
        db: Session,
        seed_permit_submitted: BoardingPermit,
        seed_certificate_valid,
        seed_safety_clear_request: SafetyClearRequest,
        seed_safety_officer: Personnel,
        seed_crew: Personnel,
    ):
        seed_permit_submitted.status = "captain_confirmed"
        seed_permit_submitted.captain_id = "captain-uuid"
        db.flush()

        permit = boarding_permit_service.safety_clear(db, seed_permit_submitted.id, seed_safety_clear_request)

        new_person = Personnel(name="新船员", employee_id="NEW002", role="crew", phone="13800000005")
        db.add(new_person)
        db.flush()

        new_cert = PersonnelCertificate(
            personnel_id=new_person.id,
            cert_type="海上作业证",
            cert_number="CERT-NEW2",
            issue_date=datetime(2024, 1, 1).date(),
            expiry_date=(datetime.utcnow() + timedelta(days=365)).date(),
            allowed_risk_level="high",
            is_valid=True,
        )
        db.add(new_cert)
        db.flush()

        update_req = PersonnelUpdateRequest(
            personnel=[
                {"personnel_id": new_person.id, "role_on_board": "船员"},
            ],
            change_reason="更换船员",
            updated_by="运维负责人",
        )
        updated = boarding_permit_service.update_personnel(db, permit.id, update_req)
        assert updated.status == "pending_reapproval"

        reapproved = boarding_permit_service.reapprove(db, updated.id, seed_safety_officer.id)
        assert reapproved.status == "safety_cleared"
        assert reapproved.requires_reapproval == False


class TestReschedule:
    def test_reschedule_after_sea_rejected(
        self,
        db: Session,
        seed_permit_submitted: BoardingPermit,
        seed_operation_window: OperationWindow,
        seed_sea_condition_wave_high: SeaCondition,
        captain_confirm_request: CaptainConfirmRequest,
    ):
        with pytest.raises(HTTPException):
            boarding_permit_service.captain_confirm(db, seed_permit_submitted.id, captain_confirm_request)

        db.refresh(seed_permit_submitted)
        assert seed_permit_submitted.status == "sea_rejected"

        new_date = datetime(2025, 1, 20, 8, 0, 0)
        reschedule_req = RescheduleRequest(
            boarding_date=new_date,
            reschedule_reason="海况不佳，改期执行",
            updated_by="运维负责人",
        )
        rescheduled = boarding_permit_service.reschedule(db, seed_permit_submitted.id, reschedule_req)

        assert rescheduled.status == "submitted"
        assert rescheduled.boarding_date == new_date
        assert rescheduled.rejection_reason is None
        assert rescheduled.sea_condition_met is None
