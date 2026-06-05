import models
from fastapi import  HTTPException, status, Depends, APIRouter
from schemas import PostResponse, UserPrivate, UserPublic, UserCreate, UserUpdate, Token
from datetime import timedelta
from fastapi.security import OAuth2PasswordRequestForm
from typing import Annotated
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from database import get_db
from auth import create_access_token, hash_password, oauth2_scheme, verify_access_token, verify_password
from config import settings

router = APIRouter()


# Session: We create a session inside the db, Depends: Before we call the code, it will call the method inside Depends(fun).
# DI works like middleware, but middlware calls on all routes on all requests, with DI we can call a specific route only
# and then return this data back as the 'db' parameter 
# Annotated just combines the type hint (Session) and extra metadata (Depends) into 1 parameter
@router.post("", response_model=UserPrivate, status_code=status.HTTP_201_CREATED)
async def create_user(user: UserCreate, db: Annotated[AsyncSession, Depends(get_db)]):
    result = await db.execute(select(models.User).where(func.lower(models.User.username) == user.username.lower()))
    existing_user = result.scalars().first()
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Username already exists"
        )

    result = await db.execute(select(models.User).where(func.lower(models.User.email) == user.email.lower()))
    existing_email = result.scalars().first()
    if existing_email:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already exists"
        )

    new_user = models.User(
        username = user.username,
        email = user.email.lower(),
        password_hash = hash_password(user.password)
    )

    db.add(new_user)
    await db.commit()
    await db.refresh(new_user)

    return new_user

@router.get('/token', response_model=Token)
async def login_for_access_token(form_data:Annotated[OAuth2PasswordRequestForm, Depends()], db: Annotated[AsyncSession, Depends(get_db)]):
    # OauthPasswordRequestForm uses 'username' field, but we treat it as email. This class has a standard to take 'username + password'
    # but in our app we do 'email + password' So we treat username field as an email field
    result = await db.execute(select(models.User).where(func.lower(models.User.email) == form_data.username.lower()))
    user = result.scalars().first()

    if not user or not verify_password(form_data.password, user.paswword_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"}
        )

    #Create acces token with user id as subject
    access_token_expires = timedelta(minutes=settings.access_token_expire_minutes)
    access_token = create_access_token(
        data={'sub':str(user.id)},
        expires_delta=access_token_expires
    )
    return Token(access_token=access_token, token_type="bearer")

@router.get('/me', response_model=UserPrivate)
async def get_current_user(token: Annotated[str, Depends(oauth2_scheme)], db: Annotated[AsyncSession, Depends(get_db)]):
    """Get the currently authenticated user"""
    user_id = verify_access_token(token)
    if user_id is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
            headers={"WWW-Authenticate": "Bearer"}
        )
    
    try:
        user_id_int = int(user_id)
    except (TypeError, ValueError):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
            headers={"WWW-Authenticate": "Bearer"}
        )
    
    result = await db.execute(select(models.User).where(models.User.id == user_id_int))
    user = result.scalars().first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found",
            headers={"WWW-Authenticate": "Bearer"}
        )
    
    return user

@router.get('', response_model=list[UserPublic])
async def get_users(db:Annotated[AsyncSession, Depends(get_db)]):
    result = await db.execute(select(models.User))
    users = result.scalars().all()
    return users

@router.get('/{user_id}', response_model=UserPublic)
async def get_user(user_id:int, db: Annotated[AsyncSession, Depends(get_db)]):
    result = await db.execute(select(models.User).where(models.User.id == user_id))       
    user = result.scalars().first()

    if user:
        return user
    
    raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

@router.get("/{user_id}/posts", response_model=list[PostResponse])
async def get_user_posts(user_id: int, db: Annotated[AsyncSession, Depends(get_db)]):
    result = await db.execute(select(models.User).where(models.User.id == user_id))
    user = result.scalars().first()
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    
    result = await db.execute(select(models.Post).options(selectinload(models.Post.author)).where(models.Post.user_id == user_id).order_by(models.Post.date_posted.desc())) 
    posts = result.scalars().all()
    return posts

@router.patch("/{user_id}", response_model=UserPrivate)
async def update_user(user_id: int, user_update: UserUpdate, db: Annotated[AsyncSession, Depends(get_db)]):
    result = await db.execute(select(models.User).where(models.User.id == user_id))
    user = result.scalars().first()
    # User checks
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

    if user_update.username is not None and user_update.username.lower() != user.username.lower():
        result = await db.execute(select(models.User).where(func.lower(models.User.username) == user_update.username.lower()))
        existing_user = result.scalars().first()
        if existing_user:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Username already exists")
        
    # Email checks
    if user_update.email is not None and user_update.email.lower() != user.email.lower():
        result = await db.execute(select(models.User).where(func.lower(models.User.email) == user_update.email.lower()))
        existing_email = result.scalars().first()
        if existing_email:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Email already registered")
    
    if user_update.email:
        user_update.email = user_update.email.lower()

    new_updates = user_update.model_dump(exclude_unset=True)
    
    for field, value in new_updates.items():
        setattr(user, field, value)
   
    await db.commit()
    await db.refresh(user)
    return user


@router.delete("/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_user(user_id:int, db:Annotated[AsyncSession, Depends(get_db)]):
    result = await db.execute(select(models.User).where(models.User.id == user_id))
    user = result.scalars().first()

    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    
    await db.delete(user)
    await db.commit()
