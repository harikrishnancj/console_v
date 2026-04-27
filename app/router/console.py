from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import RedirectResponse

from sqlalchemy.orm import Session
from app.core.database import get_db
from app.utils.session_resolver import get_session_identity, SESSION_COOKIE_NAME
from app.utils.response import wrap_response
from app.service import console_auth
from app.schemas.auth import VerifyTokenRequest
from app.models.product import Product
from app.crud.crud4user_products import check_user_product_access
from app.crud import product as product_crud
from app.core.config import console_login_url

router = APIRouter()

@router.get("/check-auth")
async def check_console_auth(
    request: Request,
    product_id: int = None,
    db: Session = Depends(get_db)
):
    # 1. Resolve Product ID from query or headers first
    if product_id is None:
        product_id_str = request.headers.get("Product-ID")
        if product_id_str:
            try:
                product_id = int(product_id_str)
            except ValueError:
                pass

    # 2. Check if user has a valid console session!
    try:
        auth_ctx = await get_session_identity(request)
        if auth_ctx["user_type"] not in ["tenant", "user"]:
             raise HTTPException(status_code=401, detail="Invalid session type for console auth")
    except HTTPException as e:
        # Build dynamic redirect URL
        login_url = f"{console_login_url}?next_product_id={product_id}" if product_id else console_login_url
        
        return wrap_response(
            data={"authenticated": False, "redirect_to": login_url},
            message="No valid console session. Please login."
        )
    
    # 3. Session is valid -> Double check Product ID
    if product_id is None:
        return wrap_response(data={"authenticated": False}, message="Missing Product-ID")

    # 3. Third: Session is valid AND Product ID is valid -> Generate temp token
    try:
        temp_token = await console_auth.check_auth_and_generate_temp_token(
            db=db,
            tenant_id=auth_ctx["tenant_id"],
            user_id=auth_ctx.get("user_id"),
            user_type=auth_ctx["user_type"],
            product_id=product_id,
            session_id=auth_ctx.get("session_id")
        )
        return wrap_response(
            data={"authenticated": True, "temp_token": temp_token}, 
            message="Session valid, temp token issued"
        )
    except HTTPException as e:
        detail = e.detail
        reason = "access_denied"
        
        if "not subscribed" in detail.lower():
            reason = "no_subscription"
        elif "permission" in detail.lower():
            reason = "no_permission"
            
        return wrap_response(
            data={"authenticated": False, "reason": reason, "detail": detail}, 
            message=detail
        )

@router.post("/verify")
async def verify_temp_token(data: VerifyTokenRequest, db: Session = Depends(get_db)):
    session_token = await console_auth.verify_temp_token_and_generate_jwt(db, data.token)
    
    return wrap_response(
        data={"session_token": session_token},
        message="Token verified successfully"
    )

@router.get("/login-redirect")
async def login_redirect(
    product_id: int,
    request: Request,
    db: Session = Depends(get_db)
):
    """
    Final step of login: Redirects the browser back to the child app.
    Includes security checks to ensure the user has access to the product.
    """
    # 1. Get current session identity
    try:
        auth_ctx = await get_session_identity(request)
    except HTTPException:
        # Not logged in, return redirect to login page with next_product_id
        return {"redirect_url": f"{console_login_url}?next_product_id={product_id}"}
    
    tenant_id = auth_ctx["tenant_id"]
    user_id = auth_ctx.get("user_id")
    user_type = auth_ctx["user_type"]

    # 2. Check if the product exists
    product = db.query(Product).filter(Product.product_id == product_id).first()
    if not product or not product.launch_url:
        print(f"[DEBUG] Product not found or no launch URL for product_id: {product_id}")
        # Fallback to dashboard if product not found or no URL
        dashboard_url = console_login_url.replace("/login", "/dashboard")
        return {"redirect_url": dashboard_url}

    # 3. Security Check: Verify user/tenant has access to this product
    # This ensures integer IDs are safe by preventing unauthorized access
    has_access = False
    if user_type == "user":
        # Check if user has role-based access
        has_access = check_user_product_access(db, user_id, tenant_id, product_id)
    elif user_type == "tenant":
        # Check if the tenant is subscribed to the product
        has_access = product_crud.get_tenant_product_by_id(db, tenant_id, product_id) is not None
    
    if not has_access:
        print(f"[DEBUG] Access denied for user {user_id or tenant_id} to product {product_id}")
        # Fallback to dashboard if access is denied
        dashboard_url = console_login_url.replace("/login", "/dashboard")
        return {"redirect_url": dashboard_url}

    # 4. Success: Redirect the browser back to the App!
    print(f"[DEBUG] Redirecting to: {product.launch_url}")
    return {"redirect_url": product.launch_url}


@router.get("/product/{product_id}/launch-url")
async def get_product_launch_url(
    product_id: int,
    db: Session = Depends(get_db),
    auth_ctx: dict = Depends(get_session_identity)
):
    tenant_id = auth_ctx["tenant_id"]
    user_id = auth_ctx.get("user_id")

    # 2. Use user_type to decide which check to perform
    if auth_ctx["user_type"] == "user":
        if not check_user_product_access(db, user_id, tenant_id, product_id):
            raise HTTPException(status_code=403, detail="Access denied: You do not have permission to launch this product")
    elif auth_ctx["user_type"] == "tenant":
        # It's a tenant, check if they are subscribed to the product
        if not product_crud.get_tenant_product_by_id(db, tenant_id, product_id):
            raise HTTPException(status_code=403, detail="Access denied: Tenant is not subscribed to this product")
    else:
        # Prevent access for unauthorized user types
        raise HTTPException(status_code=403, detail="Invalid session type for product launch")
    
    product = db.query(Product).filter(Product.product_id == product_id).first()
    
    if not product:
        return wrap_response(data={"authenticated": True}, message="Product not found")
        
    return wrap_response(
        data={"launch_url": product.launch_url},
        message="Product URL retrieved successfully"
    )
