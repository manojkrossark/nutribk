from fastapi import APIRouter, HTTPException
import bcrypt
from app.db.database import get_db_connection
from app.auth.schemas import RegisterRequest

router = APIRouter(prefix="/auth", tags=["auth"])

@router.post("/signup")
def register_user(data: RegisterRequest):
    if not data.email and not data.phone:
        raise HTTPException(status_code=400, detail="Either email or phone must be provided.")

    hashed_pw = bcrypt.hashpw(data.password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')

    conn = get_db_connection()
    cursor = conn.cursor()

    try:
        cursor.execute("""
            INSERT INTO nutri_users (name, email, phone, password)
            VALUES (%s, %s, %s, %s)
            RETURNING id;
        """, (data.name, data.email, data.phone, hashed_pw))
        user_id = cursor.fetchone()[0]
        conn.commit()
        return {"message": "User registered successfully", "user_id": user_id}
    except Exception as e:
        conn.rollback()
        raise HTTPException(status_code=400, detail=str(e))
    finally:
        cursor.close()
        conn.close()
