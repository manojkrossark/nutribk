from fastapi import APIRouter, HTTPException
from app.db.database import get_db_connection
from app.auth.schemas import LoginRequest
from datetime import datetime, timedelta
import bcrypt
import jwt  # PyJWT
from app.config.settings import settings

# JWT config
SECRET_KEY = settings.JWT_SECRET_KEY
ALGORITHM = settings.JWT_ALGORITHM
ACCESS_TOKEN_EXPIRE_MINUTES = 60

router = APIRouter(prefix="/auth", tags=["auth"])

def create_access_token(data: dict, expires_delta: timedelta = None):
    to_encode = data.copy()
    expire = datetime.utcnow() + (expires_delta or timedelta(minutes=15))
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)

@router.post("/login")
def login_user(data: LoginRequest):
    identifier = data.identifier
    password = data.password

    conn = get_db_connection()
    cursor = conn.cursor()

    try:
        # Try to match by email or phone
        cursor.execute("""
            SELECT id, name, email, phone, password FROM nutri_users 
            WHERE email = %s OR phone = %s
            LIMIT 1;
        """, (identifier, identifier))
        user = cursor.fetchone()

        if not user:
            raise HTTPException(status_code=404, detail="User not found.")

        user_id, name, email, phone, hashed_pw = user

        if not bcrypt.checkpw(password.encode('utf-8'), hashed_pw.encode('utf-8')):
            raise HTTPException(status_code=401, detail="Incorrect password.")

        token_data = {
            "sub": str(user_id),
            "name": name,
            "email": email or "",
            "phone": phone or ""
        }

        access_token = create_access_token(data=token_data, expires_delta=timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES))

        return {
            "access_token": access_token,
            "token_type": "bearer",
            "user": {
                "id": user_id,
                "name": name,
                "email": email,
                "phone": phone
            }
        }

    finally:
        cursor.close()
        conn.close()
