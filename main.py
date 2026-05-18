from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import database, models
from routers import auth, goals, manager, admin, achievements

# Create all tables on startup (Hackathon mode)
models.Base.metadata.create_all(bind=database.engine)

app = FastAPI(title="AtomQuest API", version="1.0.0")

# CORS — must list explicit origins when allow_credentials=True
# (browser spec rejects wildcard "*" with credentials)
ALLOWED_ORIGINS = [
    "http://localhost:3000",
    "http://127.0.0.1:3000",
    "http://localhost:3001",
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router)
app.include_router(goals.router)
app.include_router(manager.router)
app.include_router(admin.router)
app.include_router(achievements.router)

@app.get("/")
def read_root():
    return {"message": "Welcome to AtomQuest API!", "version": "1.0.0"}

@app.get("/health")
def health_check():
    from datetime import datetime
    return {"status": "ok", "timestamp": datetime.utcnow().isoformat()}

