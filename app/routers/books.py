from fastapi import FastAPI, Response, status,HTTPException,Depends,APIRouter
from sqlalchemy.orm import Session
from ..database import get_db
from ..import models,schemas,utils,outh2

router=APIRouter(
    prefix="/books",
    tags=['books']
)

@router.post("/", status_code=status.HTTP_201_CREATED,response_model=schemas.BookResponse)
def create_book(book:schemas.BookCreate, db:Session= Depends(get_db),current_user:models.User=Depends(outh2.get_current_user)):
    existing_book=db.query(models.Book).filter(models.Book.isbn==book.isbn).first()

    if existing_book:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Book with this isbn already exists"
        )
    
    new_book=models.Book(**book.model_dump())
    db.add(new_book)
    db.commit()
    db.refresh(new_book)

    return new_book


@router.get("/",response_model=list[schemas.BookResponse])
def get_all_books(db:Session= Depends(get_db),current_user: models.User = Depends(outh2.get_current_user)):
    books=db.query(models.Book).all()
    return books


@router.get("/{id}", response_model=schemas.BookResponse)
def get_book(id: int,db:Session= Depends(get_db),current_user: models.User = Depends(outh2.get_current_user)):
    book=db.query(models.Book).filter(models.Book.id==id).first()
    
    if not book:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND,
                             detail=f"Book with id: {id} does not exist")
    
    return book

@router.put("/{id}",response_model=schemas.BookResponse)
def update_book(id: int, book: schemas.BookCreate,db:Session= Depends(get_db)):
    existing_book=db.query(models.Book).filter(models.Book.isbn==book.isbn,models.Book.id !=id).first()
    if existing_book:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"ISBN {book.isbn} already belong to another one"
        )

    book_query=db.query(models.Book).filter(models.Book.id==id).first()

    if book_query==None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND,
                             detail=f"Book with id: {id} does not exist")
    
    book_query.title=book.title
    book_query.author=book.author
    book_query.isbn=book.isbn
    book_query.quantity=book.quantity

    db.commit()
    db.refresh(book_query)

    return  book_query


@router.delete("/{id}",status_code=status.HTTP_204_NO_CONTENT)
def delete_book(id:int,db:Session=Depends(get_db)):
    book=db.query(models.Book).filter(models.Book.id==id).first()
    

    if book==None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND,
                             detail=f"Book with id: {id} does not exist")
    
    db.delete(book)
    db.commit()

    return Response(status_code=status.HTTP_204_NO_CONTENT)