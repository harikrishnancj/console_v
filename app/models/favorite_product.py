from ..core.database import Base
from sqlalchemy import Column, Integer, ForeignKey, UniqueConstraint, Boolean
from sqlalchemy.orm import relationship

class FavoriteProduct(Base):
    __tablename__ = "favorite_products"

    id = Column(Integer, primary_key=True, index=True)
    tenant_id = Column(Integer, ForeignKey("tenants.tenant_id", ondelete="CASCADE"), nullable=False)
    user_id = Column(Integer, ForeignKey("users.user_id", ondelete="CASCADE"), nullable=True)
    product_id = Column(Integer, ForeignKey("products.product_id", ondelete="CASCADE"), nullable=False)
    favorite = Column(Boolean, default=True)

    __table_args__ = (
        UniqueConstraint("tenant_id", "user_id", "product_id", name="uq_favorite_item"),
    )

    tenant = relationship("Tenant", back_populates="favorites")
    user = relationship("User", back_populates="favorites")
    product = relationship("Product", back_populates="favorites")