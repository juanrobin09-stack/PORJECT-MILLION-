from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from sona import usage as usage_service
from sona.api.schemas import (
    OrganizationCreate,
    OrganizationCreated,
    OrganizationOut,
    SourceCreate,
    SourceOut,
    UsageOut,
)
from sona.auth import current_org
from sona.database import get_db
from sona.models import Organization, Source, generate_api_key, hash_api_key

router = APIRouter(tags=["organizations"])


@router.post("/organizations", response_model=OrganizationCreated, status_code=201)
def create_organization(body: OrganizationCreate, db: Session = Depends(get_db)):
    """Sign up. The API key is returned exactly once; only its hash is stored."""
    key = generate_api_key()
    org = Organization(
        name=body.name,
        industry=body.industry.strip().lower(),
        plan=body.plan,
        api_key_hash=hash_api_key(key),
    )
    db.add(org)
    db.commit()
    db.refresh(org)
    return OrganizationCreated(
        id=org.id,
        name=org.name,
        industry=org.industry,
        plan=org.plan,
        created_at=org.created_at,
        api_key=key,
    )


@router.get("/organizations/me", response_model=OrganizationOut)
def get_me(org: Organization = Depends(current_org)):
    return org


@router.get("/organizations/me/usage", response_model=UsageOut)
def get_usage(org: Organization = Depends(current_org), db: Session = Depends(get_db)):
    return UsageOut(
        plan=org.plan,
        period="current_month",
        signals_enriched=usage_service.signals_used(db, org),
        signal_quota=usage_service.quota_for(org),
    )


@router.post("/sources", response_model=SourceOut, status_code=201)
def create_source(
    body: SourceCreate,
    org: Organization = Depends(current_org),
    db: Session = Depends(get_db),
):
    source = Source(
        organization_id=org.id, name=body.name, kind=body.kind, config=body.config
    )
    db.add(source)
    db.commit()
    db.refresh(source)
    return source


@router.get("/sources", response_model=list[SourceOut])
def list_sources(org: Organization = Depends(current_org), db: Session = Depends(get_db)):
    return (
        db.query(Source).filter(Source.organization_id == org.id).order_by(Source.id).all()
    )
