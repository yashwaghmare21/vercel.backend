from pydantic import BaseModel, EmailStr, Field
from typing import Optional, List
from datetime import date, datetime

class Token(BaseModel):
    access_token: str
    token_type: str

class TokenData(BaseModel):
    user_id: Optional[str] = None
    role: Optional[str] = None

class UserBase(BaseModel):
    name: str
    email: EmailStr
    role: str
    department: Optional[str] = None
    manager_id: Optional[str] = None

class UserCreate(UserBase):
    password: str

class UserResponse(UserBase):
    id: str
    is_active: bool

    class Config:
        orm_mode = True
        from_attributes = True

class GoalBase(BaseModel):
    thrust_area: str
    title: str
    description: Optional[str] = None
    uom_type: str
    target_value: Optional[float] = None
    target_date: Optional[date] = None
    weightage: float = Field(..., ge=10, le=100)

class GoalCreate(GoalBase):
    pass

class GoalUpdate(BaseModel):
    target_value: Optional[float] = None
    weightage: Optional[float] = Field(None, ge=10, le=100)

class GoalResponse(GoalBase):
    id: str
    employee_id: str
    cycle_id: str
    status: str
    is_locked: bool
    is_shared: bool
    return_comment: Optional[str] = None

    class Config:
        orm_mode = True
        from_attributes = True

class GoalSubmission(BaseModel):
    goal_ids: List[str]

class ReturnGoalRequest(BaseModel):
    comment: str = Field(..., min_length=1)

class AchievementUpdate(BaseModel):
    actual_value: Optional[float] = None
    actual_date: Optional[date] = None
    status: str

class CheckinCreate(BaseModel):
    employee_id: str
    quarter: str
    comment: str = Field(..., min_length=20)
