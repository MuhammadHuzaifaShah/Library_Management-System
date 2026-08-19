from fastapi import FastAPI, Response, status,HTTPException,Depends,APIRouter
from sqlalchemy.orm import Session
from ..database import get_db
from ..import models,schemas,utils,outh2
from datetime import datetime, timezone

router=APIRouter(
    prefix="/borrowings",
    tags=['borrowings']
)

@router.post("/", status_code=status.HTTP_201_CREATED,response_model=schemas.BorrowingResponse)
def borrow_book(borrowing:schemas.BorrowingCreate, db:Session= Depends(get_db),current_user:models.User=Depends(outh2.get_current_user)):
    book=db.query(models.Book).filter(models.Book.id==borrowing.book_id).first()

    if not book:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND,
                                 detail=f"Book with id: {borrowing.book_id} does not exist")

    if book.available_quantity<=0:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST,
                                 detail=f"Book is not available")

    new_borrowing=models.Borrowing(
         user_id=current_user.id,
         book_id=borrowing.book_id
    )

    db.add(new_borrowing)

    book.available_quantity -=1
    book.available = book.available_quantity > 0

    if book.available_quantity==0:
         book.available=False
    
    db.commit()
    db.refresh(new_borrowing)

    return new_borrowing

@router.get("/my",response_model=list[schemas.BorrowingResponse])
def get_my_borrowing(db:Session= Depends(get_db),current_user:models.User=Depends(outh2.get_current_user)):
     borrowings=db.query(models.Borrowing).filter(models.Borrowing.user_id==current_user.id).all()

     return borrowings


@router.put("/{id}/return", status_code=status.HTTP_201_CREATED,response_model=schemas.BorrowingResponse)
def return_book(id:int, db:Session= Depends(get_db),current_user:models.User=Depends(outh2.get_current_user)):
     borrowings=db.query(models.Borrowing).filter(models.Borrowing.id==id,models.Borrowing.user_id==current_user.id).first()
     if not borrowings:
                 raise HTTPException(status_code=status.HTTP_404_NOT_FOUND,
                                      detail=f"Borrowing record not found")

     if borrowings.returned:
                 raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST,
                                      detail=f"Book is alredy returned")

     book=db.query(models.Book).filter(models.Book.id==borrowings.book_id).first()

     borrowings.returned=True
     borrowings.return_date = datetime.now(timezone.utc)

     book.available_quantity +=1
     book.available=True

     db.commit()
     db.refresh(borrowings)

     return borrowings


@router.get("/",response_model=list[schemas.BorrowingResponse])
def get_my_borrowing(db:Session= Depends(get_db),current_user:models.User=Depends(outh2.get_current_admin)):
     borrowings=db.query(models.Borrowing).all()

     return borrowings