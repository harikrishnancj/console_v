from pydantic import BaseModel
from typing import Optional, List
from .product import ProductInDBBase

class FavoriteToggle(BaseModel):
    product_id: int

class FavoriteSetStatus(BaseModel):
    product_id: int
    is_favorite: Optional[bool] = None  # If None, toggles the current state

class FavoriteResponse(BaseModel):
    id: int
    product_id: int
    favorite: bool
    product: ProductInDBBase

    class Config:
        from_attributes = True