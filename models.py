import uuid
from sqlalchemy import Column, String, Integer, Numeric, Boolean, Date, ForeignKey, DateTime
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
# We can't easily use gen_random_uuid() natively on SQLite for local testing without plugins,
# but for Supabase it works well. We will use Python's uuid4 as the default to be safe for both.
import uuid

from database import Base

def generate_uuid():
    return str(uuid.uuid4())

class User(Base):
    __tablename__ = "users"
    
    id = Column(String, primary_key=True, default=generate_uuid)
    name = Column(String(200), nullable=False)
    email = Column(String(200), unique=True, nullable=False, index=True)
    password_hash = Column(String(255), nullable=False)
    role = Column(String(20), nullable=False) # 'EMPLOYEE', 'MANAGER', 'ADMIN'
    manager_id = Column(String, ForeignKey("users.id"), nullable=True)
    department = Column(String(100))
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    manager = relationship("User", remote_side=[id], backref="direct_reports")

class Cycle(Base):
    __tablename__ = "cycles"
    
    id = Column(String, primary_key=True, default=generate_uuid)
    name = Column(String(100), nullable=False) # e.g., "FY 2025-26"
    goal_open = Column(Date, nullable=False)
    q1_open = Column(Date, nullable=False)
    q2_open = Column(Date, nullable=False)
    q3_open = Column(Date, nullable=False)
    q4_open = Column(Date, nullable=False)
    q4_close = Column(Date, nullable=False)
    is_active = Column(Boolean, default=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

class Goal(Base):
    __tablename__ = "goals"
    
    id = Column(String, primary_key=True, default=generate_uuid)
    employee_id = Column(String, ForeignKey("users.id"), nullable=False)
    cycle_id = Column(String, ForeignKey("cycles.id"), nullable=False)
    thrust_area = Column(String(100), nullable=False)
    title = Column(String(200), nullable=False)
    description = Column(String)
    uom_type = Column(String(20), nullable=False) # 'MIN','MAX','TIMELINE','ZERO'
    target_value = Column(Numeric, nullable=True)
    target_date = Column(Date, nullable=True)
    weightage = Column(Numeric, nullable=False)
    status = Column(String(20), default="DRAFT") # 'DRAFT','SUBMITTED','APPROVED','RETURNED'
    is_locked = Column(Boolean, default=False)
    is_shared = Column(Boolean, default=False)
    shared_parent_id = Column(String, ForeignKey("goals.id"), nullable=True)
    approved_by = Column(String, ForeignKey("users.id"), nullable=True)
    approved_at = Column(DateTime(timezone=True), nullable=True)
    return_comment = Column(String, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    employee = relationship("User", foreign_keys=[employee_id])
    cycle = relationship("Cycle")
    approver = relationship("User", foreign_keys=[approved_by])
    achievements = relationship("Achievement", back_populates="goal")

class Achievement(Base):
    __tablename__ = "achievements"
    
    id = Column(String, primary_key=True, default=generate_uuid)
    goal_id = Column(String, ForeignKey("goals.id"), nullable=False)
    quarter = Column(String(10), nullable=False) # 'Q1','Q2','Q3','Q4'
    actual_value = Column(Numeric, nullable=True)
    actual_date = Column(Date, nullable=True)
    status = Column(String(20), default="NOT_STARTED") # 'NOT_STARTED','ON_TRACK','COMPLETED'
    progress_score = Column(Numeric, nullable=True)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    goal = relationship("Goal", back_populates="achievements")

class Checkin(Base):
    __tablename__ = "checkins"
    
    id = Column(String, primary_key=True, default=generate_uuid)
    manager_id = Column(String, ForeignKey("users.id"), nullable=False)
    employee_id = Column(String, ForeignKey("users.id"), nullable=False)
    cycle_id = Column(String, ForeignKey("cycles.id"), nullable=False)
    quarter = Column(String(10), nullable=False)
    comment = Column(String, nullable=False)
    completed_at = Column(DateTime(timezone=True), server_default=func.now())

class AuditLog(Base):
    __tablename__ = "audit_logs"
    
    id = Column(String, primary_key=True, default=generate_uuid)
    goal_id = Column(String, ForeignKey("goals.id"), nullable=False)
    changed_by = Column(String, ForeignKey("users.id"), nullable=False)
    field_name = Column(String(100), nullable=False)
    old_value = Column(String, nullable=True)
    new_value = Column(String, nullable=True)
    action = Column(String(50), nullable=False) # 'EDIT', 'UNLOCK', 'APPROVE', 'RETURN'
    timestamp = Column(DateTime(timezone=True), server_default=func.now())

class ThrustArea(Base):
    __tablename__ = "thrust_areas"
    
    id = Column(String, primary_key=True, default=generate_uuid)
    name = Column(String(100), unique=True, nullable=False)
    is_active = Column(Boolean, default=True)
