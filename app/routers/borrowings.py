from datetime import datetime, timedelta, timezone
from decimal import Decimal
from math import ceil

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from ..database import get_db
from ..config import settings
from .. import models, schemas, utils, outh2

router = APIRouter(prefix='/borrowings', tags=['borrowings'])


def as_utc(value):
    return value.replace(tzinfo=timezone.utc) if value.tzinfo is None else value.astimezone(timezone.utc)


def fine_at(record, now):
    late_seconds = (as_utc(now) - as_utc(record.due_date)).total_seconds()
    days = max(0, ceil(late_seconds / 86400))
    return (settings.daily_fine * days).quantize(Decimal('0.01'))


def borrowing_response(record):
    response = schemas.BorrowingResponse.model_validate(record)
    now = datetime.now(timezone.utc)
    response.overdue = not record.returned and as_utc(record.due_date) < now
    if not record.returned:
        response.fine_amount = fine_at(record, now)
    return response


@router.post('/', status_code=201, response_model=schemas.BorrowingResponse)
def borrow_book(borrowing: schemas.BorrowingCreate, db: Session = Depends(get_db), current_user=Depends(outh2.get_current_user)):
    # Serialize loans for this member, then lock inventory. All loan paths use this lock order.
    db.query(models.User).filter(models.User.id == current_user.id).with_for_update().one()
    book = db.query(models.Book).filter(models.Book.id == borrowing.book_id).with_for_update().first()
    if book is None:
        raise HTTPException(status_code=404, detail='Book not found')
    active = db.query(models.Borrowing).filter(models.Borrowing.user_id == current_user.id, models.Borrowing.returned.is_(False))
    if active.filter(models.Borrowing.book_id == book.id).first():
        raise HTTPException(status_code=409, detail='You already have an active borrowing for this book')
    if active.count() >= settings.max_active_borrowings:
        raise HTTPException(status_code=409, detail='Active borrowing limit reached')
    if book.available_quantity <= 0:
        raise HTTPException(status_code=409, detail='Book is not available')
    now = datetime.now(timezone.utc)
    record = models.Borrowing(user_id=current_user.id, book_id=book.id, issue_date=now,
                              due_date=now + timedelta(days=settings.loan_days), fine_amount=0)
    db.add(record)
    book.available_quantity -= 1
    book.available = book.available_quantity > 0
    utils.commit(db)
    db.refresh(record)
    return borrowing_response(record)


def list_borrowings(query, returned, overdue, skip, limit):
    if returned is not None:
        query = query.filter(models.Borrowing.returned == returned)
    if overdue is not None:
        condition = (models.Borrowing.returned.is_(False)) & (models.Borrowing.due_date < datetime.now(timezone.utc))
        query = query.filter(condition if overdue else ~condition)
    return [borrowing_response(row) for row in query.order_by(models.Borrowing.id).offset(skip).limit(limit).all()]


@router.get('/my', response_model=list[schemas.BorrowingResponse])
def get_my_borrowings(db: Session = Depends(get_db), current_user=Depends(outh2.get_current_user),
                      returned: bool | None = None, overdue: bool | None = None,
                      skip: int = Query(0, ge=0), limit: int = Query(20, ge=1, le=100)):
    return list_borrowings(db.query(models.Borrowing).filter(models.Borrowing.user_id == current_user.id), returned, overdue, skip, limit)


@router.put('/{id}/return', response_model=schemas.BorrowingResponse)
def return_book(id: int, db: Session = Depends(get_db), current_user=Depends(outh2.get_current_user)):
    db.query(models.User).filter(models.User.id == current_user.id).with_for_update().one()
    record = db.query(models.Borrowing).filter(models.Borrowing.id == id, models.Borrowing.user_id == current_user.id).with_for_update().first()
    if record is None:
        raise HTTPException(status_code=404, detail='Borrowing record not found')
    if record.returned:
        raise HTTPException(status_code=409, detail='Book is already returned')
    book = db.query(models.Book).filter(models.Book.id == record.book_id).with_for_update().one()
    now = datetime.now(timezone.utc)
    record.fine_amount = fine_at(record, now)
    record.returned, record.return_date = True, now
    book.available_quantity += 1
    book.available = book.available_quantity > 0
    utils.commit(db)
    db.refresh(record)
    return borrowing_response(record)


@router.get('/', response_model=list[schemas.BorrowingResponse])
def get_all_borrowings(db: Session = Depends(get_db), current_user=Depends(outh2.get_current_admin),
                       user_id: int | None = Query(None, gt=0), returned: bool | None = None, overdue: bool | None = None,
                       skip: int = Query(0, ge=0), limit: int = Query(20, ge=1, le=100)):
    query = db.query(models.Borrowing)
    if user_id is not None:
        query = query.filter(models.Borrowing.user_id == user_id)
    return list_borrowings(query, returned, overdue, skip, limit)
