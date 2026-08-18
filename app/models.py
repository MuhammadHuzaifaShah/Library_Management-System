from sqlalchemy import Column,Integer,String,Boolean,ForeignKey
from sqlalchemy.sql.sqltypes import TIMESTAMP
from sqlalchemy.orm import relationship
from sqlalchemy.sql.expression import text
from .database import Base

class User(Base):
    __tablename__="users"

    id=Column(Integer,primary_key=True,nullable=False)
    name=Column(String,nullable=False)
    email=Column(String,nullable=False,unique=True)
    password=Column(String,nullable=False)
    isadmin=Column(Boolean,default=False)
    created_at=Column(TIMESTAMP(timezone=True),
                      nullable=False,server_default=text('now()'))


class Book(Base):
    __tablename__="books"

    id=Column(Integer,primary_key=True,nullable=False)
    title=Column(String,nullable=False)
    isbn = Column(String, nullable=False, unique=True)
    author=Column(String,nullable=False)
    quantity=Column(Integer,default=1)
    available=Column(Boolean,default=True)
    available_quantity=Column(Integer,default=1)
    created_at=Column(TIMESTAMP(timezone=True),
                      nullable=False,server_default=text('now()'))


class Borrowing(Base):
    __tablename__="borrowings"

    id=Column(Integer,primary_key=True,nullable=False)
    user_id=Column(Integer,ForeignKey("users.id"),nullable=False)
    book_id=Column(Integer,ForeignKey("books.id"),nullable=False)
    issue_date=Column(TIMESTAMP(timezone=True),
                      nullable=False,server_default=text('now()'))
    return_date=Column(TIMESTAMP(timezone=True),
                          nullable=True)
    returned=Column(Boolean,default=False)
