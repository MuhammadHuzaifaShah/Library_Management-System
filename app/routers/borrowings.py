from fastapi import FastAPI, Response, status,HTTPException,Depends,APIRouter
from sqlalchemy.orm import Session
from ..database import get_db
from ..import models,schemas,utils,outh2

router=APIRouter(
    prefix="/borrowings",
    tags=['borrowings']
)

@router.post("/", status_code=status.HTTP_201_CREATED,response_model=schemas.BorrowingResponse)
def borrow_book(borrowing:schemas.BorrowingCreate, db:Session= Depends(get_db),current_user:models.User=Depends(outh2.get_current_user)):
    book=db.query(models.Book).filter(models.Book.id==borrowing.book_id).first()

    if not book:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND,
                                 detail=f"Book with id: {id} does not exist")

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
