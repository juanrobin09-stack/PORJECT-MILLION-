from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from sona.actions.engine import _FIELDS
from sona.api.schemas import ActionRunOut, AutomationCreate, AutomationOut
from sona.auth import current_org
from sona.database import get_db
from sona.models import ActionRun, Automation, Organization

router = APIRouter(tags=["automations"])

_VALID_OPS = {"eq", "ne", "gte", "lte", "in", "contains"}


def _validate_conditions(conditions: list[dict]) -> None:
    for cond in conditions:
        if cond.get("field") not in _FIELDS:
            raise HTTPException(
                status_code=422,
                detail=f"Unknown condition field {cond.get('field')!r}. "
                f"Valid: {sorted(_FIELDS)}",
            )
        if cond.get("op", "eq") not in _VALID_OPS:
            raise HTTPException(
                status_code=422,
                detail=f"Unknown op {cond.get('op')!r}. Valid: {sorted(_VALID_OPS)}",
            )


@router.post("/automations", response_model=AutomationOut, status_code=201)
def create_automation(
    body: AutomationCreate,
    org: Organization = Depends(current_org),
    db: Session = Depends(get_db),
):
    _validate_conditions(body.conditions)
    automation = Automation(
        organization_id=org.id,
        name=body.name,
        enabled=body.enabled,
        conditions=body.conditions,
        action_type=body.action_type,
        action_config=body.action_config,
    )
    db.add(automation)
    db.commit()
    db.refresh(automation)
    return automation


@router.get("/automations", response_model=list[AutomationOut])
def list_automations(org: Organization = Depends(current_org), db: Session = Depends(get_db)):
    return db.scalars(
        select(Automation).where(Automation.organization_id == org.id).order_by(Automation.id)
    ).all()


@router.delete("/automations/{automation_id}", status_code=204)
def delete_automation(
    automation_id: int,
    org: Organization = Depends(current_org),
    db: Session = Depends(get_db),
):
    automation = db.get(Automation, automation_id)
    if automation is None or automation.organization_id != org.id:
        raise HTTPException(status_code=404, detail="Automation not found")
    db.delete(automation)
    db.commit()


@router.get("/action-runs", response_model=list[ActionRunOut])
def list_action_runs(
    org: Organization = Depends(current_org),
    db: Session = Depends(get_db),
    signal_id: int | None = None,
    action_type: str | None = None,
    limit: int = 50,
):
    query = select(ActionRun).where(ActionRun.organization_id == org.id)
    if signal_id is not None:
        query = query.where(ActionRun.signal_id == signal_id)
    if action_type is not None:
        query = query.where(ActionRun.action_type == action_type)
    return db.scalars(
        query.order_by(ActionRun.created_at.desc()).limit(min(limit, 200))
    ).all()
