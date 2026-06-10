from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.auth import current_org
from app.database import get_db
from app.models import Location, Organization
from app.schemas import LocationCreate, LocationOut

router = APIRouter(tags=["locations"])


@router.post("/locations", response_model=LocationOut, status_code=201)
def create_location(
    body: LocationCreate,
    org: Organization = Depends(current_org),
    db: Session = Depends(get_db),
):
    location = Location(
        organization_id=org.id,
        name=body.name,
        platform_ids=body.platform_ids,
        response_mode=body.response_mode,
    )
    db.add(location)
    db.commit()
    db.refresh(location)
    return location


@router.get("/locations", response_model=list[LocationOut])
def list_locations(org: Organization = Depends(current_org), db: Session = Depends(get_db)):
    return db.scalars(select(Location).where(Location.organization_id == org.id)).all()


def get_owned_location(location_id: int, org: Organization, db: Session) -> Location:
    location = db.get(Location, location_id)
    if location is None or location.organization_id != org.id:
        raise HTTPException(status_code=404, detail="Location not found")
    return location
