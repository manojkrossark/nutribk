from pydantic import BaseModel, EmailStr
from typing import Optional

class RegisterRequest(BaseModel):
    name: str
    email: Optional[EmailStr] = None
    phone: Optional[str] = None
    password: str
    
class LoginRequest(BaseModel):
    identifier: str  # email or phone
    password: str

class WaitlistUser(BaseModel):
    first_name: str
    last_name: Optional[str] = None
    mobile: Optional[str] = None
    email: Optional[EmailStr] = None
    objectives: Optional[str] = None