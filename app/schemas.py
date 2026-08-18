from pydantic import BaseModel,EmailStr,ConfigDict,Field
from typing import Optional
from datetime import datetime

class UserCreate(BaseModel):
    name : str
    email: EmailStr
    password: str


class UserResponse(BaseModel):
    id:int
    name:str
    email:EmailStr
    isadmin:bool

    model_config =ConfigDict(from_attributes=True) 

class BookCreate(BaseModel):
    title:str
    author:str
    isbn: str
    quantity:int

class BookResponse(BaseModel):
    id:int
    title: str
    author:str
    isbn: str
    quantity:int
    available:bool

    model_config =ConfigDict(from_attributes=True)

class Token(BaseModel):
    access_token:str
    token_type:str

class TokenData(BaseModel):
    id:Optional[int] = None


class BorrowingCreate(BaseModel):
    book_id:int

class BorrowingResponse(BaseModel):
    id:int
    user_id:int
    book_id:int
    issue_date:datetime
    return_date: datetime | None=None
    returned:bool

    class config:
        from_attributes=True