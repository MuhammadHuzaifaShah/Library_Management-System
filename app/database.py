from sqlalchemy import create_engine, event
from sqlalchemy.orm import declarative_base, sessionmaker

from .config import settings

DATABASE_URL = settings.sqlalchemy_url
engine = create_engine(
    DATABASE_URL, pool_pre_ping=True,
    connect_args={'check_same_thread': False} if str(DATABASE_URL).startswith('sqlite') else {},
)

if engine.dialect.name == 'sqlite':
    @event.listens_for(engine, 'connect')
    def enable_foreign_keys(connection, _):
        connection.execute('PRAGMA foreign_keys=ON')

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


def get_db():
    with SessionLocal() as db:
        yield db
