from fastapi import APIRouter, Depends, HTTPException, status, Response, Request
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session
from typing import List
import database, models, schemas, auth

router = APIRouter(prefix="/api/auth", tags=["Authentication"])

COOKIE_NAME = "atomquest_token"
COOKIE_MAX_AGE = 60 * 60 * 8  # 8 hours


@router.post("/login", response_model=schemas.Token)
def login(
    response: Response,
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: Session = Depends(database.get_db),
):
    """Authenticate with email + password. Returns JWT + sets httpOnly cookie."""
    user = db.query(models.User).filter(models.User.email == form_data.username).first()

    if not user or not auth.verify_password(form_data.password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    if not user.is_active:
        raise HTTPException(status_code=400, detail="Inactive user account")

    from datetime import timedelta
    token = auth.create_access_token(
        data={"sub": user.id, "role": user.role, "name": user.name},
        expires_delta=timedelta(minutes=auth.ACCESS_TOKEN_EXPIRE_MINUTES),
    )

    # Set httpOnly cookie so JavaScript cannot read it (XSS protection)
    response.set_cookie(
        key=COOKIE_NAME,
        value=token,
        httponly=True,
        secure=False,        # Set True in production (HTTPS only)
        samesite="lax",
        max_age=COOKIE_MAX_AGE,
        path="/",
    )

    return {"access_token": token, "token_type": "bearer"}


@router.post("/logout")
def logout(response: Response):
    """Clear the auth cookie."""
    response.delete_cookie(key=COOKIE_NAME, path="/")
    return {"message": "Logged out successfully"}


@router.get("/me", response_model=schemas.UserResponse)
def read_me(current_user: models.User = Depends(auth.get_current_user)):
    """Returns the currently authenticated user's profile."""
    response_data = schemas.UserResponse.from_orm(current_user)
    if current_user.manager:
        response_data.manager_name = current_user.manager.name
    return response_data


@router.post("/register", response_model=schemas.UserResponse, status_code=status.HTTP_201_CREATED)
def register(
    user_in: schemas.UserCreate,
    db: Session = Depends(database.get_db),
):
    """Register a new user (employee, manager, admin) and hash their password."""
    # Enforce @gmail.com email constraint
    if not user_in.email.endswith("@gmail.com"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email address must end with @gmail.com.",
        )

    # Check if email is already in use
    existing = db.query(models.User).filter(models.User.email == user_in.email).first()
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email address is already registered.",
        )

    # Hash the plain password
    hashed_pw = auth.get_password_hash(user_in.password)

    db_user = models.User(
        name=user_in.name,
        email=user_in.email,
        password_hash=hashed_pw,
        role=user_in.role,
        department=user_in.department,
        manager_id=user_in.manager_id,
        is_active=True,
    )
    db.add(db_user)
    db.commit()
    db.refresh(db_user)
    return db_user


@router.get("/managers", response_model=List[schemas.UserResponse])
def get_managers(db: Session = Depends(database.get_db)):
    """Public list of active managers (used during new employee registration to assign a manager)."""
    return db.query(models.User).filter(models.User.role == "MANAGER", models.User.is_active == True).all()

