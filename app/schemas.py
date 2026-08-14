from pydantic import BaseModel,EmailStr,ConfigDict,Field
from typing import Optional

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
    available:str

    model_config =ConfigDict(from_attributes=True)

class Token(BaseModel):
    access_token:str
    token_type:str

class TokenData(BaseModel):
    id:Optional[int] = None