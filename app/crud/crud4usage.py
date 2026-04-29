from sqlalchemy.orm import Session
from sqlalchemy import func
from app.models.product_session import ProductSession
from app.models.product import Product
from datetime import datetime, timezone

def update_heartbeat(db: Session, session_token: str):
    session = db.query(ProductSession).filter(ProductSession.session_token == session_token).first()
    if session:
        session.last_heartbeat = datetime.now(timezone.utc)
        db.commit()
    return session

def record_logout(db: Session, session_token: str):
    session = db.query(ProductSession).filter(ProductSession.session_token == session_token).first()
    if session:
        session.logout_at = datetime.now(timezone.utc)
        session.is_active = False
        db.commit()
    return session



def get_usage_statistics(db: Session, tenant_id: int, user_id: int = None, product_id: int = None):
    # Logic: Use logout_at if it exists, otherwise use last_heartbeat
    stats = db.query(
        Product.product_id,
        Product.product_name,
        func.max(ProductSession.created_at).label("last_used"),
        func.count(ProductSession.id).label("total_sessions"),
        func.sum(
            func.julianday(func.coalesce(ProductSession.logout_at, ProductSession.last_heartbeat)) - 
            func.julianday(ProductSession.created_at)
        ).label("total_days")
    ).join(ProductSession, Product.product_id == ProductSession.product_id)\
     .filter(ProductSession.tenant_id == tenant_id)
    
    if user_id:
        stats = stats.filter(ProductSession.user_id == user_id)
    
    if product_id:
        stats = stats.filter(Product.product_id == product_id)
        
    return stats.group_by(Product.product_id)\
                .order_by(func.max(ProductSession.created_at).desc())\
                .all()

def get_recently_used_apps(db: Session, tenant_id: int, user_id: int = None, limit: int = 5):
    query = db.query(
        Product.product_id,
        Product.product_name,
        func.max(ProductSession.created_at).label("last_accessed")
    ).join(ProductSession).filter(ProductSession.tenant_id == tenant_id)
    
    if user_id:
        query = query.filter(ProductSession.user_id == user_id)
        
    return query.group_by(Product.product_id)\
                .order_by(func.max(ProductSession.created_at).desc())\
                .limit(limit).all()

def get_frequently_used_apps(db: Session, tenant_id: int, user_id: int = None, limit: int = 3):
    query = db.query(
        Product.product_id,
        Product.product_name,
        func.count(ProductSession.id).label("usage_count")
    ).join(ProductSession).filter(ProductSession.tenant_id == tenant_id)
    
    if user_id:
        query = query.filter(ProductSession.user_id == user_id)
        
    return query.group_by(Product.product_id)\
                .order_by(func.count(ProductSession.id).desc())\
                .limit(limit).all()
