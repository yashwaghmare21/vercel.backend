from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List
import database, models, schemas, auth

router = APIRouter(prefix="/api/admin", tags=["Admin"])

@router.get("/users", response_model=List[schemas.UserResponse])
def get_all_users(db: Session = Depends(database.get_db), current_user: models.User = Depends(auth.require_role("ADMIN"))):
    return db.query(models.User).all()

@router.get("/cycles")
def get_all_cycles(db: Session = Depends(database.get_db), current_user: models.User = Depends(auth.require_role("ADMIN"))):
    return db.query(models.Cycle).all()

@router.post("/cycles")
def create_cycle(name: str, db: Session = Depends(database.get_db), current_user: models.User = Depends(auth.require_role("ADMIN"))):
    # Simplified cycle creation for hackathon
    new_cycle = models.Cycle(
        name=name,
        goal_open="2025-05-01",
        q1_open="2025-07-01",
        q2_open="2025-10-01",
        q3_open="2026-01-01",
        q4_open="2026-03-01",
        q4_close="2026-04-30",
        is_active=False
    )
    db.add(new_cycle)
    db.commit()
    db.refresh(new_cycle)
    return new_cycle

@router.put("/cycles/{cycle_id}/activate")
def activate_cycle(cycle_id: str, db: Session = Depends(database.get_db), current_user: models.User = Depends(auth.require_role("ADMIN"))):
    # Deactivate all others
    db.query(models.Cycle).update({models.Cycle.is_active: False})
    
    cycle = db.query(models.Cycle).filter(models.Cycle.id == cycle_id).first()
    if not cycle:
        raise HTTPException(status_code=404, detail="Cycle not found")
    
    cycle.is_active = True
    db.commit()
    return {"message": f"Cycle {cycle.name} activated"}
