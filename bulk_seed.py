"""
bulk_seed.py — seeds 10,000 dummy users into sql_app.db
Structure:
  - 10 Admins
  - 100 Managers (10 per admin department)
  - 9,890 Employees (split across managers, 3–5 goals each, mixed statuses)

Run: python bulk_seed.py
"""
import sys, random, uuid
from datetime import date, datetime, timedelta
from sqlalchemy.orm import Session

import database, models, auth

DEPARTMENTS = ["Engineering", "Sales", "Marketing", "HR", "Finance",
               "Operations", "Legal", "Design", "Data", "Support"]

THRUST_AREAS = ["Financial", "Customer", "Process", "Learning", "Innovation"]

GOAL_TEMPLATES = [
    ("Increase Revenue",         "Financial",  "percentage", "max", 20),
    ("Improve CSAT Score",       "Customer",   "numeric",    "max", 95),
    ("Reduce Churn Rate",        "Customer",   "percentage", "min", 5),
    ("Launch Feature X",         "Innovation", "numeric",    "min", 1),
    ("Reduce Infra Costs",       "Financial",  "percentage", "min", 15),
    ("Complete Training Hours",  "Learning",   "numeric",    "min", 20),
    ("Onboarding Time",          "Process",    "numeric",    "min", 14),
    ("New Hires Target",         "Learning",   "numeric",    "min", 10),
    ("Bug Resolution Rate",      "Process",    "percentage", "max", 95),
    ("NPS Score",                "Customer",   "numeric",    "max", 50),
    ("API Uptime",               "Process",    "percentage", "max", 99),
    ("Quarterly Revenue",        "Financial",  "numeric",    "max", 1000000),
]

STATUSES = ["DRAFT", "SUBMITTED", "SUBMITTED", "APPROVED", "APPROVED", "RETURNED"]

def generate_uuid():
    return str(uuid.uuid4())

def make_weightages(n: int):
    """Generate n weightages that sum to 100."""
    base = 100 // n
    weights = [base] * n
    weights[0] += 100 - sum(weights)  # adjust rounding
    return weights

def bulk_seed():
    db: Session = database.SessionLocal()
    print("Starting bulk seed...")

    try:
        # ── Thrust Areas ──────────────────────────────────────
        for ta in THRUST_AREAS:
            if not db.query(models.ThrustArea).filter_by(name=ta).first():
                db.add(models.ThrustArea(name=ta))
        db.commit()

        # ── Active cycle ──────────────────────────────────────
        cycle = db.query(models.Cycle).filter_by(is_active=True).first()
        if not cycle:
            cycle = models.Cycle(
                id=generate_uuid(),
                name="FY 2025-26",
                goal_open=date(2025, 5, 1),
                q1_open=date(2025, 7, 1),
                q2_open=date(2025, 10, 1),
                q3_open=date(2026, 1, 1),
                q4_open=date(2026, 3, 1),
                q4_close=date(2026, 4, 30),
                is_active=True,
            )
            db.add(cycle)
            db.commit()
            db.refresh(cycle)
        print(f"  Cycle: {cycle.name}")

        # ── Admins ────────────────────────────────────────────
        admins = []
        for i in range(10):
            email = f"admin{i+1}@gmail.com"
            u = db.query(models.User).filter_by(email=email).first()
            if not u:
                u = models.User(
                    id=generate_uuid(), name=f"Admin {i+1}", email=email,
                    password_hash=auth.get_password_hash("Demo@123"),
                    role="ADMIN", department=DEPARTMENTS[i % len(DEPARTMENTS)],
                    is_active=True,
                )
                db.add(u)
            admins.append(u)
        db.commit()
        print(f"  Admins: {len(admins)}")

        # ── Managers ──────────────────────────────────────────
        managers = []
        for i in range(100):
            email = f"manager{i+1}@gmail.com"
            u = db.query(models.User).filter_by(email=email).first()
            if not u:
                u = models.User(
                    id=generate_uuid(), name=f"Manager {i+1}", email=email,
                    password_hash=auth.get_password_hash("Demo@123"),
                    role="MANAGER", department=DEPARTMENTS[i % len(DEPARTMENTS)],
                    is_active=True,
                )
                db.add(u)
            managers.append(u)
        db.commit()
        print(f"  Managers: {len(managers)}")

        # ── Employees + Goals ─────────────────────────────────
        batch_size = 500
        total_employees = 9890
        created = 0

        for i in range(total_employees):
            email = f"employee{i+1}@gmail.com"
            if db.query(models.User).filter_by(email=email).first():
                continue

            mgr = managers[i % len(managers)]
            emp = models.User(
                id=generate_uuid(),
                name=f"Employee {i+1}",
                email=email,
                password_hash=auth.get_password_hash("Demo@123"),
                role="EMPLOYEE",
                department=mgr.department,
                manager_id=mgr.id,
                is_active=True,
            )
            db.add(emp)

            # 3–5 goals per employee
            n_goals = random.randint(3, 5)
            templates = random.sample(GOAL_TEMPLATES, n_goals)
            weightages = make_weightages(n_goals)
            status = random.choice(STATUSES)

            for j, (title, thrust, uom, eval_type, target) in enumerate(templates):
                goal = models.Goal(
                    id=generate_uuid(),
                    employee_id=emp.id,
                    cycle_id=cycle.id,
                    thrust_area=thrust,
                    title=f"{title} (E{i+1})",
                    description=f"Auto-generated goal for demo employee {i+1}.",
                    uom_type=uom.upper(),
                    target_value=target,
                    weightage=weightages[j],
                    status=status,
                    is_locked=(status == "APPROVED"),
                    approved_by=mgr.id if status == "APPROVED" else None,
                    approved_at=datetime.utcnow() if status == "APPROVED" else None,
                )
                db.add(goal)

            created += 1
            if created % batch_size == 0:
                db.commit()
                print(f"  Progress: {created}/{total_employees} employees ({created*100//total_employees}%)")

        db.commit()
        print(f"\n✓ Bulk seed complete!")
        print(f"  Total employees created: {created}")
        print(f"  Total managers: 100")
        print(f"  Total admins:   10")
        print(f"  Total users:    {created + 110}")
        print(f"\nLogin credentials:")
        print(f"  Admin:    admin1@gmail.com / Demo@123")
        print(f"  Manager:  manager1@gmail.com / Demo@123")
        print(f"  Employee: employee1@gmail.com / Demo@123")

    except Exception as e:
        print(f"Error: {e}")
        import traceback; traceback.print_exc()
        db.rollback()
    finally:
        db.close()

if __name__ == "__main__":
    bulk_seed()
