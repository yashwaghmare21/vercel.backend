"""
bulk_seed_fast.py — seeds 10,000 dummy users using raw SQL bulk inserts.
SQLite-safe: uses executemany + one big transaction = ~10x faster than ORM loop.

Run: .\\venv\\Scripts\\python.exe bulk_seed_fast.py
"""
import uuid, random, hashlib, time
from datetime import date, datetime

# Use raw sqlite3 for maximum speed (no ORM overhead)
import sqlite3

DB_PATH = "./sql_app.db"

DEPARTMENTS  = ["Engineering","Sales","Marketing","HR","Finance",
                "Operations","Legal","Design","Data","Support"]
THRUST_AREAS = ["Financial","Customer","Process","Learning","Innovation"]
GOAL_TEMPLATES = [
    ("Increase Revenue",        "Financial",  "PERCENTAGE", "max", 20),
    ("Improve CSAT Score",      "Customer",   "NUMERIC",    "max", 95),
    ("Reduce Churn Rate",       "Customer",   "PERCENTAGE", "min", 5),
    ("Launch New Feature",      "Innovation", "NUMERIC",    "min", 1),
    ("Reduce Infra Costs",      "Financial",  "PERCENTAGE", "min", 15),
    ("Training Hours",          "Learning",   "NUMERIC",    "min", 20),
    ("Onboarding Time",         "Process",    "NUMERIC",    "min", 14),
    ("New Hires Target",        "Learning",   "NUMERIC",    "min", 10),
    ("Bug Resolution Rate",     "Process",    "PERCENTAGE", "max", 95),
    ("NPS Score",               "Customer",   "NUMERIC",    "max", 50),
    ("API Uptime",              "Process",    "PERCENTAGE", "max", 99),
    ("Quarterly Revenue",       "Financial",  "NUMERIC",    "max", 500000),
]
STATUSES = ["DRAFT","SUBMITTED","SUBMITTED","APPROVED","APPROVED","RETURNED"]

def fake_pw_hash(pw: str) -> str:
    """Lightweight bcrypt-compatible looking hash (not real bcrypt — fast for seeding)."""
    return "$2b$12$" + hashlib.sha256(pw.encode()).hexdigest()[:53]

def make_weightages(n: int):
    base = 100 // n
    w = [base] * n
    w[0] += 100 - sum(w)
    return w

def gen_id():
    return str(uuid.uuid4())

def main():
    t0 = time.time()
    con = sqlite3.connect(DB_PATH)
    con.execute("PRAGMA journal_mode=WAL")    # write-ahead logging = faster writes
    con.execute("PRAGMA synchronous=NORMAL")  # don't fsync after every write
    cur = con.cursor()

    print("Step 1/5 — Thrust areas...")
    for ta in THRUST_AREAS:
        cur.execute("INSERT OR IGNORE INTO thrust_areas (id,name,is_active) VALUES (?,?,1)",
                    (gen_id(), ta))

    print("Step 2/5 — Active cycle...")
    cur.execute("SELECT id FROM cycles WHERE is_active=1 LIMIT 1")
    row = cur.fetchone()
    if row:
        cycle_id = row[0]
    else:
        cycle_id = gen_id()
        cur.execute("""INSERT OR IGNORE INTO cycles
            (id,name,goal_open,q1_open,q2_open,q3_open,q4_open,q4_close,is_active)
            VALUES (?,?,?,?,?,?,?,?,1)""",
            (cycle_id,"FY 2025-26","2025-05-01","2025-07-01",
             "2025-10-01","2026-01-01","2026-03-01","2026-04-30"))

    print("Step 3/5 — 10 Admins + 100 Managers...")
    admin_ids = []
    for i in range(10):
        uid = gen_id()
        cur.execute("INSERT OR IGNORE INTO users (id,name,email,password_hash,role,department,is_active) VALUES (?,?,?,?,?,?,1)",
            (uid, f"Admin {i+1}", f"admin{i+1}@gmail.com",
             fake_pw_hash("Demo@123"), "ADMIN", DEPARTMENTS[i % 10]))
        cur.execute("SELECT id FROM users WHERE email=?", (f"admin{i+1}@gmail.com",))
        admin_ids.append(cur.fetchone()[0])

    manager_ids = []
    for i in range(100):
        uid = gen_id()
        cur.execute("INSERT OR IGNORE INTO users (id,name,email,password_hash,role,department,is_active) VALUES (?,?,?,?,?,?,1)",
            (uid, f"Manager {i+1}", f"manager{i+1}@gmail.com",
             fake_pw_hash("Demo@123"), "MANAGER", DEPARTMENTS[i % 10]))
        cur.execute("SELECT id FROM users WHERE email=?", (f"manager{i+1}@gmail.com",))
        manager_ids.append(cur.fetchone()[0])

    con.commit()

    print("Step 4/5 — 9,890 Employees + goals (bulk inserts)...")
    user_rows = []
    goal_rows = []
    now_str   = datetime.now().isoformat()
    TOTAL_EMP = 9890
    BATCH     = 1000

    for i in range(TOTAL_EMP):
        emp_id  = gen_id()
        mgr_id  = manager_ids[i % 100]
        dept    = DEPARTMENTS[i % 10]
        status  = random.choice(STATUSES)
        is_locked = 1 if status == "APPROVED" else 0
        approved_by = mgr_id if status == "APPROVED" else None
        approved_at = now_str if status == "APPROVED" else None

        user_rows.append((
            emp_id, f"Employee {i+1}", f"employee{i+1}@gmail.com",
            fake_pw_hash("Demo@123"), "EMPLOYEE", dept, mgr_id, 1
        ))

        n_goals   = random.randint(3, 5)
        templates = random.sample(GOAL_TEMPLATES, n_goals)
        weights   = make_weightages(n_goals)

        for j, (title, thrust, uom, eval_t, target) in enumerate(templates):
            goal_rows.append((
                gen_id(), emp_id, cycle_id,
                thrust, f"{title}", f"Goal for employee {i+1}.",
                uom, target, None, weights[j],
                status, is_locked, 0, None, approved_by, approved_at, None,
                now_str, now_str
            ))

        if (i + 1) % BATCH == 0 or (i + 1) == TOTAL_EMP:
            cur.executemany("""INSERT OR IGNORE INTO users
                (id,name,email,password_hash,role,department,manager_id,is_active)
                VALUES (?,?,?,?,?,?,?,?)""", user_rows)
            cur.executemany("""INSERT OR IGNORE INTO goals
                (id,employee_id,cycle_id,thrust_area,title,description,
                 uom_type,target_value,target_date,weightage,
                 status,is_locked,is_shared,shared_parent_id,
                 approved_by,approved_at,return_comment,created_at,updated_at)
                VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""", goal_rows)
            con.commit()
            pct = (i+1)*100//TOTAL_EMP
            bar = "#"*(pct//5) + "."*(20-pct//5)
            print(f"  [{bar}] {i+1}/{TOTAL_EMP} ({pct}%)", end="\r")
            user_rows.clear()
            goal_rows.clear()

    print()
    print("Step 5/5 — Verifying counts...")
    cur.execute("SELECT COUNT(*) FROM users WHERE role='EMPLOYEE'")
    emp_count = cur.fetchone()[0]
    cur.execute("SELECT COUNT(*) FROM users WHERE role='MANAGER'")
    mgr_count = cur.fetchone()[0]
    cur.execute("SELECT COUNT(*) FROM users WHERE role='ADMIN'")
    adm_count = cur.fetchone()[0]
    cur.execute("SELECT COUNT(*) FROM goals")
    goal_count = cur.fetchone()[0]
    cur.execute("SELECT COUNT(*) FROM goals WHERE status='SUBMITTED'")
    sub_count = cur.fetchone()[0]

    con.close()

    elapsed = time.time() - t0
    print(f"""
Bulk Seed Complete!
  Admins      : {adm_count}
  Managers    : {mgr_count}
  Employees   : {emp_count}
  Total Users : {adm_count+mgr_count+emp_count}
  Goals       : {goal_count}
  SUBMITTED   : {sub_count}
  Time taken  : {elapsed:.1f}s

Login credentials (password: Demo@123):
  admin1@gmail.com
  manager1@gmail.com
  employee1@gmail.com
""")

if __name__ == "__main__":
    main()
