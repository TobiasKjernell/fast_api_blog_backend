## database.py
from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, sessionmaker

SQLALCHEMY_DATABASE_URL = "sqlite:///./blog.db"

## our connection to database
engine = create_engine(
    SQLALCHEMY_DATABASE_URL,
    connect_args={"check_same_thread": False},
)

## A factory that creating a session with the databsae
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

class Base(DeclarativeBase):
    pass

## a dependency injection, this one cleans up errors and other things to keep the db cleanup. It tells the db it needs a session and we give it one
## on every db call.
def get_db():
    with SessionLocal() as db:
        yield db

