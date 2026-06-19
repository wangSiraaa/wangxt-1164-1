from datetime import datetime, timedelta

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from app.database import Base
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
from app.schemas.boarding_permit import CaptainConfirmRequest


@pytest.fixture(scope="function")
def db():
    engine = create_engine("sqlite:///:memory:", echo=False)
    Base.metadata.create_all(bind=engine)
    TestingSessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)
    session = TestingSessionLocal()
    try:
        yield session
    finally:
        session.close()
        Base.metadata.drop_all(bind=engine)


@pytest.fixture
def seed_work_position(db: Session):
    wp = WorkPosition(code="WP-001", name="机位A01", description="测试机位", risk_level="high", is_active=True)
    db.add(wp)
    db.flush()
    return wp


@pytest.fixture
def seed_vessel(db: Session):
    v = Vessel(name="测试船01", code="V-001", capacity=10, vessel_type="运维船", status="active")
    db.add(v)
    db.flush()
    return v


@pytest.fixture
def seed_captain(db: Session):
    p = Personnel(name="张船长", employee_id="CAP001", role="captain", phone="13800000001")
    db.add(p)
    db.flush()
    return p


@pytest.fixture
def seed_safety_officer(db: Session):
    p = Personnel(name="李安全员", employee_id="SAF001", role="safety_officer", phone="13800000002")
    db.add(p)
    db.flush()
    return p


@pytest.fixture
def seed_crew(db: Session):
    p = Personnel(name="王船员", employee_id="CRW001", role="crew", phone="13800000003")
    db.add(p)
    db.flush()
    return p


@pytest.fixture
def seed_maintenance_plan(db: Session, seed_work_position: WorkPosition):
    plan = MaintenancePlan(
        plan_code="MP-2025-001",
        title="风机A01例行维护",
        work_position_id=seed_work_position.id,
        plan_date=datetime(2025, 1, 15).date(),
        description="年度检修",
        risk_level="high",
        status="approved",
        created_by="运维负责人",
    )
    db.add(plan)
    db.flush()
    return plan


@pytest.fixture
def seed_operation_window(db: Session, seed_work_position: WorkPosition):
    w = OperationWindow(
        work_position_id=seed_work_position.id,
        start_time=datetime(2025, 1, 15, 6, 0, 0),
        end_time=datetime(2025, 1, 15, 18, 0, 0),
        max_wave_height=1.5,
        max_wind_speed=10.0,
        min_visibility=2.0,
    )
    db.add(w)
    db.flush()
    return w


@pytest.fixture
def seed_sea_condition_ok(db: Session, seed_vessel: Vessel):
    sc = SeaCondition(
        vessel_id=seed_vessel.id,
        record_time=datetime(2025, 1, 15, 7, 0, 0),
        wave_height=1.0,
        wind_speed=8.0,
        visibility=5.0,
        sea_state="calm",
        is_navigable=True,
        recorder_name="测试员",
    )
    db.add(sc)
    db.flush()
    return sc


@pytest.fixture
def seed_sea_condition_wave_high(db: Session, seed_vessel: Vessel):
    sc = SeaCondition(
        vessel_id=seed_vessel.id,
        record_time=datetime(2025, 1, 15, 7, 0, 0),
        wave_height=2.5,
        wind_speed=8.0,
        visibility=5.0,
        sea_state="rough",
        is_navigable=False,
        recorder_name="测试员",
    )
    db.add(sc)
    db.flush()
    return sc


@pytest.fixture
def seed_sea_condition_all_violations(db: Session, seed_vessel: Vessel):
    sc = SeaCondition(
        vessel_id=seed_vessel.id,
        record_time=datetime(2025, 1, 15, 7, 0, 0),
        wave_height=2.5,
        wind_speed=15.0,
        visibility=0.5,
        sea_state="storm",
        is_navigable=False,
        recorder_name="测试员",
    )
    db.add(sc)
    db.flush()
    return sc


@pytest.fixture
def seed_permit_submitted(
    db: Session,
    seed_maintenance_plan: MaintenancePlan,
    seed_vessel: Vessel,
    seed_crew: Personnel,
):
    permit = BoardingPermit(
        permit_code="BP-2025-001",
        maintenance_plan_id=seed_maintenance_plan.id,
        vessel_id=seed_vessel.id,
        boarding_date=datetime(2025, 1, 15, 8, 0, 0),
        status="submitted",
        submitted_by="运维负责人",
    )
    db.add(permit)
    db.flush()
    bp = BoardingPersonnel(boarding_permit_id=permit.id, personnel_id=seed_crew.id, role_on_board="船员")
    db.add(bp)
    db.flush()
    return permit


@pytest.fixture
def seed_certificate_valid(db: Session, seed_crew: Personnel):
    cert = PersonnelCertificate(
        personnel_id=seed_crew.id,
        cert_type="海上作业证",
        cert_number="CERT-001",
        issue_date=datetime(2024, 1, 1).date(),
        expiry_date=(datetime.utcnow() + timedelta(days=365)).date(),
        is_valid=True,
    )
    db.add(cert)
    db.flush()
    return cert


@pytest.fixture
def seed_certificate_expired(db: Session, seed_crew: Personnel):
    cert = PersonnelCertificate(
        personnel_id=seed_crew.id,
        cert_type="海上作业证",
        cert_number="CERT-002",
        issue_date=datetime(2020, 1, 1).date(),
        expiry_date=datetime(2023, 1, 1).date(),
        is_valid=False,
    )
    db.add(cert)
    db.flush()
    return cert


@pytest.fixture
def captain_confirm_request(seed_captain: Personnel):
    return CaptainConfirmRequest(captain_id=seed_captain.id)
