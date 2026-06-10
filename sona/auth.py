from fastapi import Depends, HTTPException, Security, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy import select
from sqlalchemy.orm import Session

from sona.database import get_db
from sona.models import Organization, hash_api_key

bearer = HTTPBearer(auto_error=False)


def current_org(
    credentials: HTTPAuthorizationCredentials | None = Security(bearer),
    db: Session = Depends(get_db),
) -> Organization:
    if credentials is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing API key. Send 'Authorization: Bearer sk_sona_...'",
        )
    org = db.scalars(
        select(Organization).where(
            Organization.api_key_hash == hash_api_key(credentials.credentials)
        )
    ).first()
    if org is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid API key")
    return org
