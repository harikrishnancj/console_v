from fastapi import APIRouter, Depends, Request
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.utils.session_resolver import get_session_identity
from app.crud import crud4usage
from app.utils.response import wrap_response

router = APIRouter()

@router.post("/heartbeat")
async def heartbeat(request: Request, db: Session = Depends(get_db)):
    auth_header = request.headers.get("Authorization")
    token = auth_header.split(" ")[1] if (auth_header and " " in auth_header) else None
    if token:
        crud4usage.update_heartbeat(db, token)
    return {"status": "heartbeat recorded"}

@router.post("/app-logout")
async def app_logout(request: Request, db: Session = Depends(get_db)):
    auth_header = request.headers.get("Authorization")
    token = auth_header.split(" ")[1] if (auth_header and " " in auth_header) else None
    if token:
        crud4usage.record_logout(db, token)
    return {"status": "logout recorded"}


@router.get("/analytics")
async def get_analytics(product_id: int = None, auth: dict = Depends(get_session_identity), db: Session = Depends(get_db)):
    rows = crud4usage.get_usage_statistics(db, auth["tenant_id"], auth.get("user_id"), product_id)
    results = []
    for r in rows:
        results.append({
            "app_name": r.product_name,
            "last_access": r.last_used,
            "total_launches": r.total_sessions,
            "total_hours": round((r.total_days or 0) * 24, 2)
        })
    return wrap_response(data=results, message="Usage analytics retrieved")

@router.get("/recently-used")
async def get_recent(limit: int = 3, auth: dict = Depends(get_session_identity), db: Session = Depends(get_db)):
    recent = crud4usage.get_recently_used_apps(db, auth["tenant_id"], auth.get("user_id"), limit)
    results = [{"product_id": r.product_id, "app_name": r.product_name, "last_used": r.last_accessed} for r in recent]
    return wrap_response(data=results, message="Recent apps retrieved")

@router.get("/frequently-used")
async def get_frequent(limit: int = 3, auth: dict = Depends(get_session_identity), db: Session = Depends(get_db)):
    frequent = crud4usage.get_frequently_used_apps(db, auth["tenant_id"], auth.get("user_id"), limit)
    results = [{"product_id": r.product_id, "app_name": r.product_name, "usage_count": r.usage_count} for r in frequent]
    return wrap_response(data=results, message="Frequent apps retrieved")
