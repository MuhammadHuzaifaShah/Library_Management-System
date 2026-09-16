import bcrypt
from fastapi import HTTPException
from sqlalchemy.exc import IntegrityError


def hash(password: str):
    return bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')


def verify(plain_password: str, hashed_password: str):
    try:
        return bcrypt.checkpw(plain_password.encode('utf-8'), hashed_password.encode('utf-8'))
    except (ValueError, TypeError):
        return False


def commit(db, detail='The change conflicts with an existing record'):
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=409, detail=detail)
