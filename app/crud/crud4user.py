from sqlalchemy.orm import Session
from app.models import User
from app.schemas.user import UserUpdate, UserInDBBase
from app.core.security import hash_password, verify_password
from fastapi import HTTPException
from sqlalchemy.orm import selectinload

def get_user_by_email(db: Session, email: str):
    return db.query(User).filter(User.email == email).first()


def update_user(db: Session, user_id: int, user_update: UserUpdate, tenant_id: int):
    db_user = db.query(User).filter(User.user_id == user_id, User.tenant_id == tenant_id).first()
    if not db_user:
        return None
    
    update_data = user_update.model_dump(exclude_unset=True)
    
    if "password" in update_data and update_data["password"]:
        if "old_password" not in update_data or not update_data["old_password"]:
            raise HTTPException(status_code=400, detail="Current password is required to set a new password")
        
        if not verify_password(update_data.pop("old_password"), db_user.hashed_password):
            raise HTTPException(status_code=400, detail="Invalid current password")
            
        update_data["hashed_password"] = hash_password(update_data.pop("password"))
    elif "old_password" in update_data:
        update_data.pop("old_password")
    
    for key, value in update_data.items():
        setattr(db_user, key, value)
    
    db.commit()
    db.refresh(db_user)
    return db_user

def get_user(db: Session, user_id: int, tenant_id: int):
    return db.query(User).filter(User.user_id == user_id, User.tenant_id == tenant_id).first()

def update_user_email_name(db: Session, user_id: int, user_update, tenant_id: int):
    """Update user email and/or name for a tenant user."""
    db_user = db.query(User).filter(User.user_id == user_id, User.tenant_id == tenant_id).first()
    if not db_user:
        return None
    
    update_data = user_update.model_dump(exclude_unset=True)
    
    # Only allow updating email and username
    allowed_fields = {"email", "username"}
    update_data = {k: v for k, v in update_data.items() if k in allowed_fields}
    
    for key, value in update_data.items():
        setattr(db_user, key, value)
    
    db.commit()
    db.refresh(db_user)
    return db_user



def sorting_user_based_on_username(
    db: Session,
    tenant_id: int,
    sort_order: str = "asc"   # default ascending
):
    query = db.query(User).options(selectinload(User.user_roles)).filter(User.tenant_id == tenant_id)

    if sort_order.lower() == "desc":
        query = query.order_by(User.username.desc())
    else:
        query = query.order_by(User.username.asc())

    users = query.all()
    
    return [
        {
            "user_id": user.user_id,
            "username": user.username,
            "email": user.email,
            "is_active": user.is_active,
            "tenant_id": user.tenant_id,
            "roles": [mapping.role.role_name for mapping in user.user_roles if mapping.role]
        } for user in users
    ]

    