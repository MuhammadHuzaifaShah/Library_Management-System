from sqlalchemy import Boolean, CheckConstraint, Column, DateTime, ForeignKey, Index, Integer, Numeric, String, func, text
from .database import Base


class User(Base):
    __tablename__ = 'users'
    id = Column(Integer, primary_key=True)
    name = Column(String, nullable=False)
    email = Column(String, nullable=False, unique=True)
    password = Column(String, nullable=False)
    isadmin = Column(Boolean, nullable=False, default=False, server_default=text('false'))
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())


class Book(Base):
    __tablename__ = 'books'
    __table_args__ = (
        CheckConstraint('quantity >= 0', name='books_quantity_nonnegative'),
        CheckConstraint('available_quantity >= 0 AND available_quantity <= quantity', name='books_stock_bounds'),
        CheckConstraint('available = (available_quantity > 0)', name='books_available_matches_stock'),
    )
    id = Column(Integer, primary_key=True)
    title = Column(String, nullable=False)
    isbn = Column(String, nullable=False, unique=True)
    author = Column(String, nullable=False)
    quantity = Column(Integer, nullable=False, default=1)
    available = Column(Boolean, nullable=False, default=True)
    available_quantity = Column(Integer, nullable=False, default=1)
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())


class Borrowing(Base):
    __tablename__ = 'borrowings'
    __table_args__ = (
        Index('uq_active_user_book', 'user_id', 'book_id', unique=True,
              postgresql_where=text('returned = false'), sqlite_where=text('returned = 0')),
        CheckConstraint('fine_amount >= 0', name='borrowings_fine_nonnegative'),
    )
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey('users.id'), nullable=False, index=True)
    book_id = Column(Integer, ForeignKey('books.id'), nullable=False, index=True)
    issue_date = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
    due_date = Column(DateTime(timezone=True), nullable=False)
    return_date = Column(DateTime(timezone=True))
    returned = Column(Boolean, nullable=False, default=False, server_default=text('false'))
    fine_amount = Column(Numeric(12, 2), nullable=False, default=0, server_default='0')
