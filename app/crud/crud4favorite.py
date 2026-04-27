from sqlalchemy.orm import Session
from app.models.favorite_product import FavoriteProduct
from app.crud import product as product_crud
from app.models.tenant_product_mapping import TenantProductMapping
from app.models.app_role_mapping import AppRoleMapping
from app.models.role_user_mapping import RoleUserMapping
from app.models import Product
from sqlalchemy.orm import joinedload
from fastapi import HTTPException
from typing import Optional

def get_favorites(db: Session, tenant_id: int, user_id: Optional[int] = None, only_active: bool = True):
    """
    Get favorites with product details:
    - If user_id is None: Return tenant-level favorites (where user_id is NULL)
    - If user_id is provided: Return user-level favorites for products the tenant is subscribed to
    - If only_active is True: Return only favorites marked as True
    """
 
    
    if user_id is None:
        # Tenant-level favorites - return all favorites where user_id is NULL
        query = db.query(FavoriteProduct).options(
            joinedload(FavoriteProduct.product)
        ).filter(
            FavoriteProduct.tenant_id == tenant_id,
            FavoriteProduct.user_id == None
        )
        
        if only_active:
            query = query.filter(FavoriteProduct.favorite == True)
        
        return query.all()
    
    else:
        # User-level favorites - only show products the tenant is subscribed to
        # (not filtering by roles - users can favorite any subscribed product)
        tenant_subscribed_products = (
            db.query(Product.product_id)
            .join(TenantProductMapping, TenantProductMapping.product_id == Product.product_id)
            .filter(
                TenantProductMapping.tenant_id == tenant_id,
                TenantProductMapping.status == "APPROVED"
            )
            .distinct()
        )
        
        query = db.query(FavoriteProduct).options(
            joinedload(FavoriteProduct.product)
        ).filter(
            FavoriteProduct.tenant_id == tenant_id,
            FavoriteProduct.user_id == user_id,
            FavoriteProduct.product_id.in_(tenant_subscribed_products)
        )
        
        if only_active:
            query = query.filter(FavoriteProduct.favorite == True)
        
        return query.all()

def set_favorite_status(db: Session, product_id: int, tenant_id: int, is_favorite: Optional[bool] = None, user_id: Optional[int] = None):
    """
    Set or toggle the favorite status for a product.
    - If is_favorite is None: toggles the current state (True→False, False→True; defaults to True for new records)
    - If is_favorite is True/False: explicitly sets that value
    - If user_id is None: Tenant-level favorite
    - If user_id is provided: User-level favorite
    """
    # 1. Access Check
    has_subscription = product_crud.get_tenant_product_by_id(db, tenant_id, product_id) is not None
    
    if not has_subscription:
        raise HTTPException(
            status_code=403, 
            detail="Access denied: Tenant has not subscribed to this product."
        )
    
    # 2. If user-level favorite, check if user has role
    if user_id is not None:
        has_role = (
            db.query(RoleUserMapping).join(
                AppRoleMapping, AppRoleMapping.role_id == RoleUserMapping.role_id
            ).filter(
                RoleUserMapping.user_id == user_id,
                RoleUserMapping.tenant_id == tenant_id,
                AppRoleMapping.product_id == product_id,
                AppRoleMapping.tenant_id == tenant_id
            ).first() is not None
        )
        
        if not has_role:
            raise HTTPException(
                status_code=403,
                detail="Access denied: You do not have a role assigned to this product."
            )
    
    # 3. Update or Create
    existing = db.query(FavoriteProduct).filter(
        FavoriteProduct.tenant_id == tenant_id,
        FavoriteProduct.user_id == user_id,
        FavoriteProduct.product_id == product_id
    ).first()

    if existing:
        # Toggle if is_favorite not supplied, otherwise set explicitly
        new_value = (not existing.favorite) if is_favorite is None else is_favorite
        existing.favorite = new_value
        db.commit()
        db.refresh(existing)
        return {"status": "updated", "product_id": product_id, "favorite": existing.favorite}
    else:
        new_fav = FavoriteProduct(
            tenant_id=tenant_id,
            user_id=user_id,
            product_id=product_id,
            favorite=True if is_favorite is None else is_favorite  # default True for new records
        )
        db.add(new_fav)
        db.commit()
        db.refresh(new_fav)
        return {"status": "created", "product_id": product_id, "favorite": new_fav.favorite}