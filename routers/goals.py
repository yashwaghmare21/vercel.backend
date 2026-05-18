from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List
import database, models, schemas, auth

router = APIRouter(prefix="/api/goals", tags=["Goals"])

@router.get("/", response_model=List[schemas.GoalResponse])
def get_my_goals(db: Session = Depends(database.get_db), current_user: models.User = Depends(auth.require_role("EMPLOYEE"))):
    return db.query(models.Goal).filter(models.Goal.employee_id == current_user.id).all()

@router.post("/", response_model=schemas.GoalResponse)
def create_goal(goal: schemas.GoalCreate, db: Session = Depends(database.get_db), current_user: models.User = Depends(auth.require_role("EMPLOYEE"))):
    # Need to get active cycle
    cycle = db.query(models.Cycle).filter(models.Cycle.is_active == True).first()
    if not cycle:
        raise HTTPException(status_code=400, detail="No active cycle found")
    
    # Check max goals
    current_goals_count = db.query(models.Goal).filter(
        models.Goal.employee_id == current_user.id,
        models.Goal.cycle_id == cycle.id
    ).count()
    if current_goals_count >= 8:
        raise HTTPException(status_code=400, detail="Maximum 8 goals allowed")

    db_goal = models.Goal(
        **goal.dict(),
        employee_id=current_user.id,
        cycle_id=cycle.id,
        status="DRAFT"
    )
    db.add(db_goal)
    db.commit()
    db.refresh(db_goal)
    return db_goal

@router.put("/{goal_id}", response_model=schemas.GoalResponse)
def update_goal(goal_id: str, goal_update: schemas.GoalUpdate, db: Session = Depends(database.get_db), current_user: models.User = Depends(auth.require_role("EMPLOYEE", "MANAGER"))):
    db_goal = db.query(models.Goal).filter(models.Goal.id == goal_id).first()
    if not db_goal:
        raise HTTPException(status_code=404, detail="Goal not found")
    
    # Check if locked
    if db_goal.is_locked:
        raise HTTPException(status_code=403, detail="Goal is locked and cannot be edited")

    if current_user.role == "EMPLOYEE" and db_goal.employee_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not your goal")

    # Only managers can edit goals in SUBMITTED state
    if current_user.role == "EMPLOYEE" and db_goal.status not in ["DRAFT", "RETURNED"]:
        raise HTTPException(status_code=403, detail="Cannot edit goal in current state")

    update_data = goal_update.dict(exclude_unset=True)
    for key, value in update_data.items():
        setattr(db_goal, key, value)
    
    db.commit()
    db.refresh(db_goal)
    return db_goal

@router.post("/submit", status_code=status.HTTP_200_OK)
def submit_goals(submission: schemas.GoalSubmission, db: Session = Depends(database.get_db), current_user: models.User = Depends(auth.require_role("EMPLOYEE"))):
    goals = db.query(models.Goal).filter(models.Goal.id.in_(submission.goal_ids), models.Goal.employee_id == current_user.id).all()
    if not goals:
        raise HTTPException(status_code=404, detail="No goals found")
    
    if len(goals) > 8:
        raise HTTPException(status_code=400, detail="Maximum 8 goals allowed")
    
    total_weightage = sum([g.weightage for g in goals])
    if abs(total_weightage - 100) > 0.01:
        raise HTTPException(status_code=400, detail=f"Total weightage must equal 100%. Current: {total_weightage}%")
    
    for g in goals:
        if g.weightage < 10:
            raise HTTPException(status_code=400, detail=f"Goal '{g.title}': minimum weightage is 10%")
        g.status = "SUBMITTED"
    
    db.commit()
    return {"message": "Goals submitted successfully"}
