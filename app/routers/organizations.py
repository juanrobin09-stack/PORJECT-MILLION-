from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.auth import current_org
from app.database import get_db
from app.models import BrandVoice, Organization
from app.schemas import (
    BrandVoiceOut,
    BrandVoiceUpsert,
    OrganizationCreate,
    OrganizationOut,
    UsageOut,
)
from app.services import usage as usage_service

router = APIRouter(tags=["organizations"])


@router.post("/organizations", response_model=OrganizationOut, status_code=201)
def create_organization(body: OrganizationCreate, db: Session = Depends(get_db)):
    """Sign up. Returns the org with its API key — shown once, store it safely."""
    org = Organization(name=body.name, plan=body.plan)
    db.add(org)
    db.commit()
    db.refresh(org)
    return org


@router.get("/organizations/me", response_model=OrganizationOut)
def get_me(org: Organization = Depends(current_org)):
    return org


@router.get("/organizations/me/usage", response_model=UsageOut)
def get_usage(org: Organization = Depends(current_org), db: Session = Depends(get_db)):
    return UsageOut(
        plan=org.plan,
        period="current_month",
        responses_used=usage_service.responses_used(db, org),
        responses_quota=usage_service.quota_for(db, org),
    )


@router.put("/organizations/me/brand-voice", response_model=BrandVoiceOut)
def upsert_brand_voice(
    body: BrandVoiceUpsert,
    org: Organization = Depends(current_org),
    db: Session = Depends(get_db),
):
    voice = org.brand_voice
    if voice is None:
        voice = BrandVoice(organization_id=org.id)
        db.add(voice)
    for field, value in body.model_dump().items():
        setattr(voice, field, value)
    db.commit()
    db.refresh(voice)
    return voice


@router.get("/organizations/me/brand-voice", response_model=BrandVoiceOut | None)
def get_brand_voice(org: Organization = Depends(current_org)):
    return org.brand_voice
