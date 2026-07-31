from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from sona import benchmarks as benchmark_service
from sona.api.schemas import BenchmarkOut
from sona.auth import current_org
from sona.database import get_db
from sona.models import Organization

router = APIRouter(tags=["benchmarks"])


@router.get("/benchmarks", response_model=list[BenchmarkOut])
def my_industry_benchmarks(
    org: Organization = Depends(current_org),
    db: Session = Depends(get_db),
    period: str | None = None,
):
    """Anonymized topic benchmarks for the org's industry.

    Segments appear only when enough distinct organizations contribute
    (k-anonymity) — small industries return an empty list until the network
    grows, by design.
    """
    return benchmark_service.published_benchmarks(db, org.industry, period=period)
