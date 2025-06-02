from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.db.database import create_user_table_if_not_exists 
from app.db.database import create_waitlist_table_if_not_exists 

from app.meal.routes import router as meal_router
from app.auth.signup import router as signup_router
from app.auth.login import router as login_router
from app.waitlist.route import router as waitlist_router

app = FastAPI()

# CORS Middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ✅ Call this on startup
@app.on_event("startup")
def startup_event():
    create_user_table_if_not_exists()
    create_waitlist_table_if_not_exists()

# Register routes

#Meal Planner
app.include_router(meal_router)

#Auth
app.include_router(signup_router)
app.include_router(login_router)

#Waitlist
app.include_router(waitlist_router)

# Optional root check
@app.get("/")
def health_check():
    return {"status": "Meal planner API is running"}

# Run with: uvicorn app.main:app --reload
