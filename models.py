## models.py
from __future__ import annotations

## timestamps from py
from datetime import UTC, datetime

## DB types
from sqlalchemy import DateTime, ForeignKey, Integer, String, Text
## row and structure helpers
from sqlalchemy.orm import Mapped, mapped_column, relationship

from database import Base

class User(Base):
    ## which table
    __tablename__ = "users"

    ## ID name of the column, primary key = increase automatic if True, unique = can only be one of the value, nullable(true/false) = is required or not
    #  
    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    username: Mapped[str] = mapped_column(String(50), unique=True, nullable=False)
    email: Mapped[str] = mapped_column(String(120), unique=True, nullable=False)
    image_file: Mapped[str | None] = mapped_column(String(200), nullable=True, default=None)
    paswword_hash: Mapped[str] = mapped_column(String(200), nullable=False)
    #relationships takes the value and goes into whatever it has for posts. 'user.posts' etc later
    posts: Mapped[list[Post]] = relationship(back_populates="author", cascade="all, delete-orphan")

    @property #instead of "user.image_path() we can write user.image_path and it return auto, the callers doesnt need to call the method"
    def image_path(self) -> str:
        if self.image_file:
            return f"/media/profile_pics/{self.image_file}"
        return ""
    
    
class Post(Base):
    __tablename__ = "posts"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    title: Mapped[str] = mapped_column(String(100), nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False, index=True)
    date_posted: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(UTC))
    author: Mapped[User] = relationship(back_populates="posts")