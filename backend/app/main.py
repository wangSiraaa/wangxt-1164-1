from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from app.database import Base, engine
from app.routers import (
    boarding_permit,
    maintenance_plan,
    operation_window,
    personnel,
    personnel_certificate,
    sea_condition,
    vessel,
    work_position,
)


@asynccontextmanager
async def lifespan(app: FastAPI):
    Base.metadata.create_all(bind=engine)
    yield


app = FastAPI(
    title="海上风电登乘许可系统",
    description="运维登乘许可管理 - 覆盖运维计划、船长确认和安全员放行",
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(work_position.router)
app.include_router(vessel.router)
app.include_router(personnel.router)
app.include_router(personnel_certificate.router)
app.include_router(sea_condition.router)
app.include_router(operation_window.router)
app.include_router(maintenance_plan.router)
app.include_router(boarding_permit.router)


@app.get("/health")
def health_check():
    return {"status": "ok", "service": "windfarm-boarding-permit"}
