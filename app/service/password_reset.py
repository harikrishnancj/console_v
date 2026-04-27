from fastapi import HTTPException
from sqlalchemy.orm import Session
from app.models import Tenant, User
from app.core.security import hash_password, verify_password
from app.service import otp as otp_service
from app.core.redis import redis_client

async def request_password_reset_service(db: Session, email: str):
    tenant = db.query(Tenant).filter(Tenant.email == email).first()
    user = db.query(User).filter(User.email == email).first()

    if not tenant and not user:
        raise HTTPException(status_code=404, detail="Email not registered")
    
    return await otp_service.request_otp_service(email)

async def reset_password_service(db: Session, email: str, new_password: str, old_password: str = None):

    is_verified = await redis_client.get(f"verified_email:{email}")
    
    if not is_verified or is_verified != "true":
         raise HTTPException(status_code=400, detail="Email not verified")

    tenant = db.query(Tenant).filter(Tenant.email == email).first()
    user = db.query(User).filter(User.email == email).first()

    if not tenant and not user:
         raise HTTPException(status_code=404, detail="Account not found during reset")

    # Update passwords
    if tenant:
        tenant.hashed_password = hash_password(new_password)
    if user:
        user.hashed_password = hash_password(new_password)

    db.commit()
    
    await redis_client.delete(f"verified_email:{email}")
    
    return {"message": "Password updated successfully"}
