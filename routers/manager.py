from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List, Optional
from datetime import datetime
from pydantic import BaseModel
import database, models, schemas, auth

router = APIRouter(prefix="/api/manager", tags=["Manager"])


# ── Response schemas for new endpoints ───────────────────────────────────────

class GoalBrief(BaseModel):
    id: str
    thrust_area: str
    title: str
    description: Optional[str] = None
    weightage: float
    uom_type: str
    target_value: Optional[float] = None
    status: str
    is_locked: bool

    class Config:
        orm_mode = True
        from_attributes = True


class PendingSubmission(BaseModel):
    employee_id: str
    employee_name: str
    employee_email: str
    submitted_at: str          # ISO timestamp of most-recent update
    goals: List[GoalBrief]


class ManagerStats(BaseModel):
    team_size: int
    pending_approvals: int
    goals_locked: int


# ── Existing endpoints ────────────────────────────────────────────────────────

@router.get("/team", response_model=List[schemas.UserResponse])
def get_team(
    db: Session = Depends(database.get_db),
    current_user: models.User = Depends(auth.require_role("MANAGER", "ADMIN")),
):
    return (
        db.query(models.User)
        .filter(models.User.manager_id == current_user.id)
        .all()
    )


@router.get("/goals/{emp_id}", response_model=List[schemas.GoalResponse])
def get_employee_goals(
    emp_id: str,
    db: Session = Depends(database.get_db),
    current_user: models.User = Depends(auth.require_role("MANAGER", "ADMIN")),
):
    # Ensure employee reports to this manager
    if current_user.role == "MANAGER":
        emp = (
            db.query(models.User)
            .filter(
                models.User.id == emp_id,
                models.User.manager_id == current_user.id,
            )
            .first()
        )
        if not emp:
            raise HTTPException(status_code=403, detail="Employee not in your team")
    return (
        db.query(models.Goal)
        .filter(models.Goal.employee_id == emp_id)
        .all()
    )


@router.post("/goals/{emp_id}/approve")
def approve_goals(
    emp_id: str,
    db: Session = Depends(database.get_db),
    current_user: models.User = Depends(auth.require_role("MANAGER")),
):
    goals = (
        db.query(models.Goal)
        .filter(
            models.Goal.employee_id == emp_id,
            models.Goal.status == "SUBMITTED",
        )
        .all()
    )
    if not goals:
        raise HTTPException(
            status_code=400, detail="No submitted goals found for this employee"
        )

    total_weightage = sum(float(g.weightage) for g in goals)
    if abs(total_weightage - 100) > 0.01:
        raise HTTPException(
            status_code=400,
            detail=f"Cannot approve: Total weightage is {total_weightage:.1f}% (must be 100%)",
        )

    for g in goals:
        g.status = "APPROVED"
        g.is_locked = True
        g.approved_by = current_user.id
        g.approved_at = datetime.utcnow()

    db.commit()
    return {"message": "Goals approved and locked", "count": len(goals)}


@router.post("/goals/{emp_id}/return")
def return_goals(
    emp_id: str,
    req: schemas.ReturnGoalRequest,
    db: Session = Depends(database.get_db),
    current_user: models.User = Depends(auth.require_role("MANAGER")),
):
    goals = (
        db.query(models.Goal)
        .filter(
            models.Goal.employee_id == emp_id,
            models.Goal.status == "SUBMITTED",
        )
        .all()
    )
    if not goals:
        raise HTTPException(
            status_code=400, detail="No submitted goals found for this employee"
        )

    for g in goals:
        g.status = "RETURNED"
        g.return_comment = req.comment

    db.commit()
    return {"message": "Goals returned for rework", "count": len(goals)}


# ── New endpoints ─────────────────────────────────────────────────────────────

@router.get("/pending-submissions", response_model=List[PendingSubmission])
def get_pending_submissions(
    db: Session = Depends(database.get_db),
    current_user: models.User = Depends(auth.require_role("MANAGER", "ADMIN")),
):
    """
    Returns all employees in the manager's team that have at least one
    SUBMITTED goal, grouped as pending approval submissions.
    """
    # Get all employees under this manager
    team = (
        db.query(models.User)
        .filter(models.User.manager_id == current_user.id)
        .all()
    )
    team_ids = [u.id for u in team]

    if not team_ids:
        return []

    # Get all SUBMITTED goals for this team (single query, no N+1)
    submitted_goals = (
        db.query(models.Goal)
        .filter(
            models.Goal.employee_id.in_(team_ids),
            models.Goal.status == "SUBMITTED",
        )
        .all()
    )

    # Group goals by employee_id
    goals_by_emp: dict[str, list[models.Goal]] = {}
    for g in submitted_goals:
        goals_by_emp.setdefault(g.employee_id, []).append(g)

    # Build a lookup for employee details
    emp_lookup = {u.id: u for u in team}

    results: List[PendingSubmission] = []
    for emp_id, emp_goals in goals_by_emp.items():
        emp = emp_lookup.get(emp_id)
        if not emp:
            continue

        # Most recent updated_at as the "submitted at" time
        latest_update = max(
            (g.updated_at for g in emp_goals if g.updated_at),
            default=None,
        )
        submitted_at = latest_update.isoformat() if latest_update else datetime.utcnow().isoformat()

        results.append(
            PendingSubmission(
                employee_id=emp_id,
                employee_name=emp.name,
                employee_email=emp.email,
                submitted_at=submitted_at,
                goals=[
                    GoalBrief(
                        id=g.id,
                        thrust_area=g.thrust_area,
                        title=g.title,
                        description=g.description,
                        weightage=float(g.weightage),
                        uom_type=g.uom_type,
                        target_value=float(g.target_value) if g.target_value is not None else None,
                        status=g.status,
                        is_locked=g.is_locked,
                    )
                    for g in emp_goals
                ],
            )
        )

    # Sort by employee name for stable ordering
    results.sort(key=lambda x: x.employee_name)
    return results


@router.get("/stats", response_model=ManagerStats)
def get_manager_stats(
    db: Session = Depends(database.get_db),
    current_user: models.User = Depends(auth.require_role("MANAGER", "ADMIN")),
):
    """Dashboard summary stats for the authenticated manager."""
    team = (
        db.query(models.User)
        .filter(models.User.manager_id == current_user.id)
        .all()
    )
    team_ids = [u.id for u in team]
    team_size = len(team)

    if not team_ids:
        return ManagerStats(team_size=0, pending_approvals=0, goals_locked=0)

    # Count employees with at least one SUBMITTED goal
    from sqlalchemy import func, distinct
    pending_approvals = (
        db.query(func.count(distinct(models.Goal.employee_id)))
        .filter(
            models.Goal.employee_id.in_(team_ids),
            models.Goal.status == "SUBMITTED",
        )
        .scalar()
        or 0
    )

    goals_locked = (
        db.query(func.count(models.Goal.id))
        .filter(
            models.Goal.employee_id.in_(team_ids),
            models.Goal.is_locked == True,
        )
        .scalar()
        or 0
    )

    return ManagerStats(
        team_size=team_size,
        pending_approvals=pending_approvals,
        goals_locked=goals_locked,
    )

