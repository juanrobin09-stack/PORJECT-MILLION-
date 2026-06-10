from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.auth import current_org
from app.database import get_db
from app.models import Alert, InsightReport, Organization
from app.schemas import AlertOut, InsightReportOut
from app.services import insights as insight_service

router = APIRouter(tags=["insights"])


@router.get("/insights", response_model=list[InsightReportOut])
def list_reports(
    org: Organization = Depends(current_org),
    db: Session = Depends(get_db),
    limit: int = 12,
):
    return db.scalars(
        select(InsightReport)
        .where(InsightReport.organization_id == org.id)
        .order_by(InsightReport.created_at.desc())
        .limit(min(limit, 52))
    ).all()


@router.post("/insights/generate", response_model=InsightReportOut)
def generate_now(org: Organization = Depends(current_org), db: Session = Depends(get_db)):
    """Generate a report for the trailing 7 days on demand (also runs weekly)."""
    report = insight_service.generate_weekly_report(db, org)
    if report is None:
        raise HTTPException(status_code=422, detail="No analyzed reviews in the last 7 days")
    return report


@router.get("/alerts", response_model=list[AlertOut])
def list_alerts(
    org: Organization = Depends(current_org),
    db: Session = Depends(get_db),
    limit: int = 50,
):
    return db.scalars(
        select(Alert)
        .where(Alert.organization_id == org.id)
        .order_by(Alert.created_at.desc())
        .limit(min(limit, 200))
    ).all()
