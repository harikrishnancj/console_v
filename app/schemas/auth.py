from typing import Optional
from pydantic import BaseModel


class PasswordResetRequest(BaseModel):
    email: str

class PasswordResetConfirm(BaseModel):
    email: str
    new_password: str
    old_password: Optional[str] = None

class VerifyTokenRequest(BaseModel):
    token: str