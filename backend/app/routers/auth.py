from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import User
from app.schemas import LoginRequest, TokenResponse, UserCreate, UserResponse
from app.security import create_access_token, hash_password, verify_password, get_current_user

router = APIRouter(prefix="/api/v1/auth", tags=["Authentication"])


@router.post("/register", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
def register_user(user_data: UserCreate, db: Session = Depends(get_db)):
    email = user_data.email.strip().lower()
    existing = db.scalar(select(User).where(User.email == email))
    if existing is not None:
        raise HTTPException(status_code=409, detail="An account with this email already exists.")

    user = User(
        email=email,
        full_name=user_data.full_name.strip(),
        password_hash=hash_password(user_data.password),
        role="customer",
    )
    db.add(user)
    try:
        db.commit()
        db.refresh(user)
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=409, detail="An account with this email already exists.")
    return user


@router.post("/login", response_model=TokenResponse)
def login(login_data: LoginRequest, db: Session = Depends(get_db)):
    email = login_data.email.strip().lower()
    user = db.scalar(select(User).where(User.email == email))
    if user is None or not user.is_active or not verify_password(
        login_data.password, user.password_hash
    ):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    return TokenResponse(access_token=create_access_token(user))


@router.get("/me", response_model=UserResponse)
def read_current_user(current_user: User = Depends(get_current_user)):
    return current_user
