from fastapi import APIRouter, Depends, HTTPException, Query, Response
from sqlalchemy import func
from sqlalchemy.orm import Session
from ..database import get_db
from .. import models, schemas, utils, outh2

router = APIRouter(prefix='/users', tags=['users'])


def require_self_or_admin(id, current_user):
    if current_user.id != id and not current_user.isadmin:
        raise HTTPException(status_code=403, detail='You can only manage your own account')


def check_email(db, email, exclude_id=None):
    query = db.query(models.User).filter(func.lower(models.User.email) == email.lower())
    if exclude_id is not None:
        query = query.filter(models.User.id != exclude_id)
    if query.first():
        raise HTTPException(status_code=409, detail='Email is already registered')


@router.post('/', status_code=201, response_model=schemas.UserResponse)
def create_user(user: schemas.UserCreate, db: Session = Depends(get_db)):
    check_email(db, user.email)
    new_user = models.User(name=user.name, email=user.email, password=utils.hash(user.password), isadmin=False)
    db.add(new_user)
    utils.commit(db, 'Email is already registered')
    db.refresh(new_user)
    return new_user


@router.get('/', response_model=list[schemas.UserResponse])
def get_all_users(db: Session = Depends(get_db), current_user=Depends(outh2.get_current_admin),
                  skip: int = Query(0, ge=0), limit: int = Query(20, ge=1, le=100)):
    return db.query(models.User).order_by(models.User.id).offset(skip).limit(limit).all()


@router.get('/me', response_model=schemas.UserResponse)
def get_current_user_info(current_user=Depends(outh2.get_current_user)):
    return current_user


@router.get('/{id}', response_model=schemas.UserResponse)
def get_user(id: int, db: Session = Depends(get_db), current_user=Depends(outh2.get_current_user)):
    require_self_or_admin(id, current_user)
    user = db.get(models.User, id)
    if user is None:
        raise HTTPException(status_code=404, detail='User not found')
    return user


@router.put('/{id}', response_model=schemas.UserResponse)
def update_user(id: int, user: schemas.UserCreate, db: Session = Depends(get_db), current_user=Depends(outh2.get_current_user)):
    require_self_or_admin(id, current_user)
    record = db.query(models.User).filter(models.User.id == id).with_for_update().first()
    if record is None:
        raise HTTPException(status_code=404, detail='User not found')
    check_email(db, user.email, id)
    record.name, record.email, record.password = user.name, user.email, utils.hash(user.password)
    utils.commit(db, 'Email is already registered')
    db.refresh(record)
    return record


@router.delete('/{id}', status_code=204)
def delete_user(id: int, db: Session = Depends(get_db), current_user=Depends(outh2.get_current_user)):
    require_self_or_admin(id, current_user)
    user = db.query(models.User).filter(models.User.id == id).with_for_update().first()
    if user is None:
        raise HTTPException(status_code=404, detail='User not found')
    if db.query(models.Borrowing).filter(models.Borrowing.user_id == id).first():
        raise HTTPException(status_code=409, detail='Users with borrowing history cannot be deleted')
    db.delete(user)
    utils.commit(db)
    return Response(status_code=204)
