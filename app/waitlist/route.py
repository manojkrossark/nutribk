from fastapi import APIRouter, HTTPException
from app.auth.schemas import WaitlistUser
from app.db.database import get_db_connection

router = APIRouter(prefix="/waitlist", tags=["Waitlist"])

@router.post("/add")
def add_to_waitlist(data: WaitlistUser):
    if not data.email and not data.mobile:
        raise HTTPException(status_code=400, detail="Either email or mobile is required")

    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("""
            INSERT INTO waitlist_users (first_name, last_name, mobile, email, objectives)
            VALUES (%s, %s, %s, %s, %s)
        """, (data.first_name, data.last_name, data.mobile, data.email, data.objectives))
        conn.commit()
        return {"message": "Added to waitlist successfully"}
    except Exception as e:
        conn.rollback()
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")
    finally:
        cursor.close()
        conn.close()
