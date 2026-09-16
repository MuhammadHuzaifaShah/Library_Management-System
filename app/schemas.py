from datetime import datetime
from decimal import Decimal
from typing import Annotated

from pydantic import BaseModel, ConfigDict, EmailStr, Field, StringConstraints, field_validator

Text = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=255)]


class UserCreate(BaseModel):
    model_config = ConfigDict(extra='forbid')
    name: Text
    email: EmailStr
    password: str = Field(min_length=8, max_length=72)

    @field_validator('email')
    @classmethod
    def normalize_email(cls, value):
        return value.lower()

    @field_validator('password')
    @classmethod
    def validate_password_bytes(cls, value):
        if len(value.encode('utf-8')) > 72:
            raise ValueError('Password must be at most 72 UTF-8 bytes')
        return value


class UserResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    name: str
    email: EmailStr
    isadmin: bool


class BookCreate(BaseModel):
    model_config = ConfigDict(extra='forbid')
    title: Text
    author: Text
    isbn: Text
    quantity: int = Field(ge=0)


class BookResponse(BookCreate):
    model_config = ConfigDict(from_attributes=True)
    id: int
    available: bool
    available_quantity: int


class Token(BaseModel):
    access_token: str
    token_type: str


class TokenData(BaseModel):
    id: int = Field(gt=0)


class BorrowingCreate(BaseModel):
    model_config = ConfigDict(extra='forbid')
    book_id: int = Field(gt=0)


class BorrowingResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    user_id: int
    book_id: int
    issue_date: datetime
    due_date: datetime
    return_date: datetime | None = None
    returned: bool
    fine_amount: Decimal
    overdue: bool = False
