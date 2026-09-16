"""JWT authentication (module name retained for existing imports)."""
from datetime import datetime, timedelta, timezone

from fastapi import Depends, HTTPException
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt
from pydantic import ValidationError
from sqlalchemy.orm import Session

from . import database, models, schemas
from .config import settings

outh2_scheme = OAuth2PasswordBearer(tokenUrl='login')


def create_access_token(data: dict):
    payload = data.copy()
    payload['exp'] = datetime.now(timezone.utc) + timedelta(minutes=settings.access_token_expire_minutes)
    return jwt.encode(payload, settings.secret_key, algorithm=settings.algorithm)


def verify_access_token(token: str, credentials_exception):
    try:
        payload = jwt.decode(token, settings.secret_key, algorithms=[settings.algorithm], options={'require_exp': True})
        return schemas.TokenData(id=payload.get('user_id'))
    except (JWTError, ValidationError, TypeError, ValueError):
        raise credentials_exception


def get_current_user(token: str = Depends(outh2_scheme), db: Session = Depends(database.get_db)):
    error = HTTPException(status_code=401, detail='Could not validate credentials', headers={'WWW-Authenticate': 'Bearer'})
    token_data = verify_access_token(token, error)
    user = db.get(models.User, token_data.id)
    if user is None:
        raise error
    return user


def get_current_admin(current_user: models.User = Depends(get_current_user)):
    if not current_user.isadmin:
        raise HTTPException(status_code=403, detail='Administrator access required')
    return current_user
