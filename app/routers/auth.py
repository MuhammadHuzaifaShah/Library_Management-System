from fastapi import APIRouter, Depends, HTTPException
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy import func
from sqlalchemy.orm import Session
from .. import database, schemas, models, utils, outh2

router = APIRouter(tags=['Authentication'])


@router.post('/login', response_model=schemas.Token)
def login(user_credentials: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(database.get_db)):
    user = db.query(models.User).filter(func.lower(models.User.email) == user_credentials.username.strip().lower()).first()
    if not user or not utils.verify(user_credentials.password, user.password):
        raise HTTPException(status_code=401, detail='Invalid credentials', headers={'WWW-Authenticate': 'Bearer'})
    return {'access_token': outh2.create_access_token({'user_id': user.id}), 'token_type': 'bearer'}
