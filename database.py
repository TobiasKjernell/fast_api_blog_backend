## database.py
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase

SQLALCHEMY_DATABASE_URL = "sqlite+aiosqlite:///./blog.db"

## our connection to database
engine = create_async_engine(
    SQLALCHEMY_DATABASE_URL,
    connect_args={"check_same_thread": False},
)

## A factory that creating a session with the databsae
AsyncSessionLocal = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

class Base(DeclarativeBase):
    pass

## a dependency injection, this one cleans up errors and other things to keep the db cleanup. It tells the db it needs a session and we give it one
## on every db call.
async def get_db():
    async with AsyncSessionLocal() as session:
        yield session

