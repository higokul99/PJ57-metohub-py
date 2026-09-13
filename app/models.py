from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import (
    Boolean,
    Date,
    DateTime,
    ForeignKey,
    Integer,
    Numeric,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class Plan(Base):
    __tablename__ = "plans"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(50), unique=True)
    slug: Mapped[str] = mapped_column(String(50), unique=True)
    price_weekly: Mapped[Decimal] = mapped_column(Numeric(10, 2), default=0)
    week_count: Mapped[int] = mapped_column(Integer, default=52)
    trial_days: Mapped[int] = mapped_column(Integer, default=90)
    banner_limit: Mapped[int] = mapped_column(Integer, default=0)
    price_monthly: Mapped[Decimal] = mapped_column(Numeric(10, 2), default=0)
    product_limit: Mapped[int] = mapped_column(Integer, default=50)
    description: Mapped[str | None] = mapped_column(String(255), nullable=True)
    features_json: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(100))
    email: Mapped[str] = mapped_column(String(150), unique=True)
    phone: Mapped[str | None] = mapped_column(String(50), nullable=True)
    whatsapp: Mapped[str | None] = mapped_column(String(50), nullable=True)
    country: Mapped[str | None] = mapped_column(String(100), nullable=True)
    address: Mapped[str | None] = mapped_column(Text, nullable=True)
    national_id_number: Mapped[str | None] = mapped_column(String(100), nullable=True)
    password_hash: Mapped[str] = mapped_column(String(255))
    role: Mapped[str] = mapped_column(String(20), default="seller")
    status: Mapped[str] = mapped_column(String(20), default="active")
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), onupdate=func.now())

    tenant: Mapped["Tenant | None"] = relationship(back_populates="user", uselist=False)


class Tenant(Base):
    __tablename__ = "tenants"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"))
    plan_id: Mapped[int] = mapped_column(ForeignKey("plans.id"))
    name: Mapped[str] = mapped_column(String(120))
    slug: Mapped[str] = mapped_column(String(100), unique=True)
    business_type: Mapped[str] = mapped_column(String(80))
    tagline: Mapped[str | None] = mapped_column(String(255), nullable=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    logo: Mapped[str | None] = mapped_column(String(255), nullable=True)
    logo_webp: Mapped[str | None] = mapped_column(String(255), nullable=True)
    banner: Mapped[str | None] = mapped_column(String(255), nullable=True)
    banner_webp: Mapped[str | None] = mapped_column(String(255), nullable=True)
    currency: Mapped[str] = mapped_column(String(10), default="₹")
    currency_symbol: Mapped[str] = mapped_column(String(5), default="₹")
    theme_color: Mapped[str] = mapped_column(String(20), default="#6366f1")
    theme_settings: Mapped[str | None] = mapped_column(Text, nullable=True)
    contact_email: Mapped[str | None] = mapped_column(String(150), nullable=True)
    contact_phone: Mapped[str | None] = mapped_column(String(50), nullable=True)
    address: Mapped[str | None] = mapped_column(Text, nullable=True)
    hide_default_banner: Mapped[bool] = mapped_column(Boolean, default=False)
    enable_upi: Mapped[bool] = mapped_column(Boolean, default=True)
    enable_cod: Mapped[bool] = mapped_column(Boolean, default=False)
    enable_bank: Mapped[bool] = mapped_column(Boolean, default=False)
    enable_card: Mapped[bool] = mapped_column(Boolean, default=False)
    upi_id: Mapped[str | None] = mapped_column(String(150), nullable=True)
    upi_qr_image: Mapped[str | None] = mapped_column(String(255), nullable=True)
    bank_details: Mapped[str | None] = mapped_column(Text, nullable=True)
    status: Mapped[str] = mapped_column(String(20), default="active")
    subscription_proof: Mapped[str | None] = mapped_column(String(255), nullable=True)
    subscription_transaction_id: Mapped[str | None] = mapped_column(String(120), nullable=True)
    trial_start: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    trial_end: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    subscription_start: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    subscription_end: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), onupdate=func.now())

    user: Mapped[User] = relationship(back_populates="tenant")
    plan: Mapped[Plan] = relationship()
    categories: Mapped[list["Category"]] = relationship(back_populates="tenant")
    products: Mapped[list["Product"]] = relationship(back_populates="tenant")
    orders: Mapped[list["Order"]] = relationship(back_populates="tenant")
    banners: Mapped[list["TenantBanner"]] = relationship(back_populates="tenant", cascade="all, delete-orphan")


class TenantBanner(Base):
    __tablename__ = "tenant_banners"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    tenant_id: Mapped[int] = mapped_column(ForeignKey("tenants.id", ondelete="CASCADE"))
    image_path: Mapped[str] = mapped_column(String(255))
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    tenant: Mapped[Tenant] = relationship(back_populates="banners")


class Category(Base):
    __tablename__ = "categories"
    __table_args__ = (UniqueConstraint("tenant_id", "slug", name="unique_tenant_category"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    tenant_id: Mapped[int] = mapped_column(ForeignKey("tenants.id", ondelete="CASCADE"))
    name: Mapped[str] = mapped_column(String(100))
    slug: Mapped[str] = mapped_column(String(100))
    description: Mapped[str | None] = mapped_column(String(255), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    tenant: Mapped[Tenant] = relationship(back_populates="categories")
    products: Mapped[list["Product"]] = relationship(back_populates="category")


class Product(Base):
    __tablename__ = "products"
    __table_args__ = (UniqueConstraint("tenant_id", "slug", name="unique_tenant_product"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    tenant_id: Mapped[int] = mapped_column(ForeignKey("tenants.id", ondelete="CASCADE"))
    category_id: Mapped[int | None] = mapped_column(ForeignKey("categories.id", ondelete="SET NULL"), nullable=True)
    name: Mapped[str] = mapped_column(String(150))
    slug: Mapped[str] = mapped_column(String(150))
    sku: Mapped[str | None] = mapped_column(String(50), nullable=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    price: Mapped[Decimal] = mapped_column(Numeric(10, 2), default=0)
    is_rental: Mapped[bool] = mapped_column(Boolean, default=False)
    rental_period: Mapped[str] = mapped_column(String(20), default="none")
    rental_price_daily: Mapped[Decimal] = mapped_column(Numeric(10, 2), default=0)
    rental_price_weekend: Mapped[Decimal] = mapped_column(Numeric(10, 2), default=0)
    rental_deposit: Mapped[Decimal] = mapped_column(Numeric(10, 2), default=0)
    stock_quantity: Mapped[int] = mapped_column(Integer, default=10)
    featured_image_webp: Mapped[str | None] = mapped_column(String(255), nullable=True)
    views_count: Mapped[int] = mapped_column(Integer, default=0)
    status: Mapped[str] = mapped_column(String(20), default="active")
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), onupdate=func.now())

    tenant: Mapped[Tenant] = relationship(back_populates="products")
    category: Mapped[Category | None] = relationship(back_populates="products")
    images: Mapped[list["ProductImage"]] = relationship(back_populates="product", cascade="all, delete-orphan")

    @property
    def primary_image(self) -> str | None:
        if not self.images:
            return None
        ordered = sorted(self.images, key=lambda i: (not i.is_primary, i.id or 0))
        return ordered[0].image_path if ordered else None


class ProductImage(Base):
    __tablename__ = "product_images"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    product_id: Mapped[int] = mapped_column(ForeignKey("products.id", ondelete="CASCADE"))
    tenant_id: Mapped[int | None] = mapped_column(ForeignKey("tenants.id", ondelete="CASCADE"), nullable=True)
    image_path: Mapped[str | None] = mapped_column(String(255), nullable=True)
    image_path_webp: Mapped[str | None] = mapped_column(String(255), nullable=True)
    is_primary: Mapped[bool] = mapped_column(Boolean, default=True)
    display_order: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    product: Mapped[Product] = relationship(back_populates="images")


class Order(Base):
    __tablename__ = "orders"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    tenant_id: Mapped[int] = mapped_column(ForeignKey("tenants.id", ondelete="CASCADE"))
    order_number: Mapped[str] = mapped_column(String(30), unique=True)
    customer_name: Mapped[str] = mapped_column(String(100))
    customer_email: Mapped[str] = mapped_column(String(150))
    customer_phone: Mapped[str] = mapped_column(String(50))
    shipping_address: Mapped[str] = mapped_column(Text)
    city: Mapped[str | None] = mapped_column(String(100), nullable=True)
    postal_code: Mapped[str | None] = mapped_column(String(20), nullable=True)
    total_amount: Mapped[Decimal] = mapped_column(Numeric(10, 2), default=0)
    payment_method: Mapped[str] = mapped_column(String(50), default="cod")
    payment_status: Mapped[str] = mapped_column(String(20), default="pending")
    payment_proof: Mapped[str | None] = mapped_column(String(255), nullable=True)
    transaction_ref: Mapped[str | None] = mapped_column(String(120), nullable=True)
    is_rental_order: Mapped[bool] = mapped_column(Boolean, default=False)
    rental_duration_days: Mapped[int] = mapped_column(Integer, default=1)
    rental_start_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    status: Mapped[str] = mapped_column(String(20), default="pending")
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), onupdate=func.now())

    tenant: Mapped[Tenant] = relationship(back_populates="orders")
    items: Mapped[list["OrderItem"]] = relationship(back_populates="order", cascade="all, delete-orphan")


class OrderItem(Base):
    __tablename__ = "order_items"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    order_id: Mapped[int] = mapped_column(ForeignKey("orders.id", ondelete="CASCADE"))
    tenant_id: Mapped[int] = mapped_column(ForeignKey("tenants.id", ondelete="CASCADE"))
    product_id: Mapped[int | None] = mapped_column(ForeignKey("products.id", ondelete="SET NULL"), nullable=True)
    product_name: Mapped[str] = mapped_column(String(150))
    quantity: Mapped[int] = mapped_column(Integer, default=1)
    unit_price: Mapped[Decimal] = mapped_column(Numeric(10, 2), default=0)
    is_rental: Mapped[bool] = mapped_column(Boolean, default=False)
    rental_type: Mapped[str | None] = mapped_column(String(30), nullable=True)
    rental_start_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    rental_days: Mapped[int | None] = mapped_column(Integer, nullable=True)
    line_total: Mapped[Decimal] = mapped_column(Numeric(10, 2), default=0)
    total_price: Mapped[Decimal] = mapped_column(Numeric(10, 2), default=0)

    order: Mapped[Order] = relationship(back_populates="items")

class Page(Base):
    __tablename__ = "pages"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    slug: Mapped[str] = mapped_column(String(50), unique=True)
    title: Mapped[str] = mapped_column(String(100))
    content: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
