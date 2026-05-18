import os
from datetime import date
from sqlalchemy.orm import Session
import database, models, auth

def seed_db():
    print("Seeding database...")
    db = database.SessionLocal()
    try:
        # Create Thrust Areas
        areas = ["Sales & Growth", "Customer Success", "Product Innovation", "Operational Excellence"]
        for area in areas:
            if not db.query(models.ThrustArea).filter_by(name=area).first():
                db.add(models.ThrustArea(name=area))
        
        # Create Cycle
        cycle_name = "FY 2025-26"
        cycle = db.query(models.Cycle).filter_by(name=cycle_name).first()
        if not cycle:
            cycle = models.Cycle(
                name=cycle_name,
                goal_open=date(2025, 5, 1),
                q1_open=date(2025, 7, 1),
                q2_open=date(2025, 10, 1),
                q3_open=date(2026, 1, 1),
                q4_open=date(2026, 3, 1),
                q4_close=date(2026, 4, 30),
                is_active=True
            )
            db.add(cycle)
            db.commit()
            db.refresh(cycle)

        # Create Admin
        admin_email = "admin@atomquest.demo"
        admin = db.query(models.User).filter_by(email=admin_email).first()
        if not admin:
            admin = models.User(
                name="Ananya HR",
                email=admin_email,
                password_hash=auth.get_password_hash("Demo@123"),
                role="ADMIN",
                department="HR"
            )
            db.add(admin)
            db.commit()
            db.refresh(admin)

        # Create Manager
        manager_email = "manager@atomquest.demo"
        manager = db.query(models.User).filter_by(email=manager_email).first()
        if not manager:
            manager = models.User(
                name="Rahul Mehta",
                email=manager_email,
                password_hash=auth.get_password_hash("Demo@123"),
                role="MANAGER",
                department="Sales"
            )
            db.add(manager)
            db.commit()
            db.refresh(manager)

        # Create Employee
        emp_email = "employee@atomquest.demo"
        emp = db.query(models.User).filter_by(email=emp_email).first()
        if not emp:
            emp = models.User(
                name="Priya Sharma",
                email=emp_email,
                password_hash=auth.get_password_hash("Demo@123"),
                role="EMPLOYEE",
                department="Sales",
                manager_id=manager.id
            )
            db.add(emp)
            db.commit()
            db.refresh(emp)
        
        print("Seeding completed successfully!")
    except Exception as e:
        print(f"Error seeding DB: {e}")
        db.rollback()
    finally:
        db.close()

if __name__ == "__main__":
    seed_db()
