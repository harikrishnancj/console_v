from sqlalchemy.orm import Session
from app.models import RoleUserMapping, AppRoleMapping, Product, TenantProductMapping
from typing import List, Optional


def get_user_products(db: Session, user_id: int, tenant_id: int) -> List[Product]:
    """Return distinct products the user can ACCESS, based on their role assignments and tenant subscription status."""
    return (
        db.query(Product)
        .join(TenantProductMapping, TenantProductMapping.product_id == Product.product_id)
        .join(AppRoleMapping, AppRoleMapping.product_id == Product.product_id)
        .join(RoleUserMapping, RoleUserMapping.role_id == AppRoleMapping.role_id)
        .filter(
            RoleUserMapping.user_id == user_id,
            RoleUserMapping.tenant_id == tenant_id,
            AppRoleMapping.tenant_id == tenant_id,
            TenantProductMapping.tenant_id == tenant_id,
            TenantProductMapping.status == "APPROVED"
        )
        .distinct()
        .all()
    )


def get_user_discovery_products(db: Session, user_id: int, tenant_id: int) -> List[Product]:
    """
    Return products for discovery:
    1. Products the tenant HAS NOT purchased (not APPROVED).
    2. Products the tenant HAS purchased (APPROVED) but the user DOES NOT have access to.
    """
    # Subquery for product IDs user has access to
    user_product_ids = (
        db.query(Product.product_id)
        .join(TenantProductMapping, TenantProductMapping.product_id == Product.product_id)
        .join(AppRoleMapping, AppRoleMapping.product_id == Product.product_id)
        .join(RoleUserMapping, RoleUserMapping.role_id == AppRoleMapping.role_id)
        .filter(
            RoleUserMapping.user_id == user_id,
            RoleUserMapping.tenant_id == tenant_id,
            AppRoleMapping.tenant_id == tenant_id,
            TenantProductMapping.tenant_id == tenant_id,
            TenantProductMapping.status == "APPROVED"
        )
        .distinct()
    )
    
    # Return all products NOT in that list
    return db.query(Product).filter(~Product.product_id.in_(user_product_ids)).all()


def get_tenant_products_for_user(db: Session, tenant_id: int) -> List[Product]:
    """Return all products the tenant has subscribed to (user can VIEW but not necessarily launch all)."""
    return (
        db.query(Product)
        .join(TenantProductMapping, TenantProductMapping.product_id == Product.product_id)
        .filter(
            TenantProductMapping.tenant_id == tenant_id,
            TenantProductMapping.status == "APPROVED"
        )
        .all()
    )


def get_user_product_by_id(db: Session, user_id: int, tenant_id: int, product_id: int) -> Optional[Product]:
    """Return a specific product only if the user has role-based access to it and the tenant subscription is approved."""
    return (
        db.query(Product)
        .join(TenantProductMapping, TenantProductMapping.product_id == Product.product_id)
        .join(AppRoleMapping, AppRoleMapping.product_id == Product.product_id)
        .join(RoleUserMapping, RoleUserMapping.role_id == AppRoleMapping.role_id)
        .filter(
            RoleUserMapping.user_id == user_id,
            RoleUserMapping.tenant_id == tenant_id,
            AppRoleMapping.tenant_id == tenant_id,
            TenantProductMapping.tenant_id == tenant_id,
            TenantProductMapping.status == "APPROVED",
            Product.product_id == product_id
        )
        .first()
    )


def check_user_product_access(db: Session, user_id: int, tenant_id: int, product_id: int) -> bool:
    """Check if user has role-based access to a specific product and the tenant subscription is approved (used for launch auth)."""
    count = (
        db.query(Product.product_id)
        .join(TenantProductMapping, TenantProductMapping.product_id == Product.product_id)
        .join(AppRoleMapping, AppRoleMapping.product_id == Product.product_id)
        .join(RoleUserMapping, RoleUserMapping.role_id == AppRoleMapping.role_id)
        .filter(
            RoleUserMapping.user_id == user_id,
            RoleUserMapping.tenant_id == tenant_id,
            AppRoleMapping.tenant_id == tenant_id,
            TenantProductMapping.tenant_id == tenant_id,
            TenantProductMapping.status == "APPROVED",
            Product.product_id == product_id
        )
        .count()
    )
    return count > 0