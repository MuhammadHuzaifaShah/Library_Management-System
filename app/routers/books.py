from fastapi import APIRouter, Depends, HTTPException, Query, Response
from sqlalchemy import or_
from sqlalchemy.orm import Session
from ..database import get_db
from .. import models, schemas, utils, outh2

router = APIRouter(prefix='/books', tags=['books'])


@router.post('/', status_code=201, response_model=schemas.BookResponse)
def create_book(book: schemas.BookCreate, db: Session = Depends(get_db), current_user=Depends(outh2.get_current_admin)):
    record = models.Book(**book.model_dump(), available_quantity=book.quantity, available=book.quantity > 0)
    db.add(record)
    utils.commit(db, 'ISBN is already registered')
    db.refresh(record)
    return record


@router.get('/', response_model=list[schemas.BookResponse])
def get_all_books(db: Session = Depends(get_db), current_user=Depends(outh2.get_current_user),
                  search: str | None = Query(None, max_length=255), author: str | None = Query(None, max_length=255),
                  available: bool | None = None, skip: int = Query(0, ge=0), limit: int = Query(20, ge=1, le=100)):
    query = db.query(models.Book)
    if search:
        query = query.filter(or_(models.Book.title.icontains(search, autoescape=True),
                                 models.Book.author.icontains(search, autoescape=True),
                                 models.Book.isbn.icontains(search, autoescape=True)))
    if author:
        query = query.filter(models.Book.author.icontains(author, autoescape=True))
    if available is not None:
        query = query.filter(models.Book.available == available)
    return query.order_by(models.Book.id).offset(skip).limit(limit).all()


@router.get('/{id}', response_model=schemas.BookResponse)
def get_book(id: int, db: Session = Depends(get_db), current_user=Depends(outh2.get_current_admin)):
    book = db.get(models.Book, id)
    if book is None:
        raise HTTPException(status_code=404, detail='Book not found')
    return book


@router.put('/{id}', response_model=schemas.BookResponse)
def update_book(id: int, book: schemas.BookCreate, db: Session = Depends(get_db), current_user=Depends(outh2.get_current_admin)):
    record = db.query(models.Book).filter(models.Book.id == id).with_for_update().first()
    if record is None:
        raise HTTPException(status_code=404, detail='Book not found')
    borrowed = record.quantity - record.available_quantity
    if book.quantity < borrowed:
        raise HTTPException(status_code=409, detail='Quantity cannot be lower than the number of borrowed copies')
    for key, value in book.model_dump().items():
        setattr(record, key, value)
    record.available_quantity = book.quantity - borrowed
    record.available = record.available_quantity > 0
    utils.commit(db, 'ISBN is already registered')
    db.refresh(record)
    return record


@router.delete('/{id}', status_code=204)
def delete_book(id: int, db: Session = Depends(get_db), current_user=Depends(outh2.get_current_admin)):
    book = db.query(models.Book).filter(models.Book.id == id).with_for_update().first()
    if book is None:
        raise HTTPException(status_code=404, detail='Book not found')
    if db.query(models.Borrowing).filter(models.Borrowing.book_id == id).first():
        raise HTTPException(status_code=409, detail='Books with borrowing history cannot be deleted')
    db.delete(book)
    utils.commit(db)
    return Response(status_code=204)
