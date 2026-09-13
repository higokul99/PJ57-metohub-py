import json
import math
import random
import re
from decimal import Decimal
from datetime import datetime, timedelta

from fastapi import APIRouter, Depends, File, Form, Request, UploadFile
from fastapi.responses import HTMLResponse
from sqlalchemy import func, or_
from sqlalchemy.orm import Session, joinedload

from app.config import BASE_DIR
from app.database import get_db
from app.deps import current_tenant, current_user, redirect, template_globals
from app.images import process_upload
from app.models import Category, Order, Product, ProductImage, Tenant, TenantBanner
from app.security import clean_string, slugify, verify_csrf
from app.templating import render
from app.theme import THEME_PRESETS, get_store_theme
router = APIRouter(prefix="/admin")
ALLOWED_PER_PAGE = [15, 25, 50, 100]


def admin_guard(request: Request, db: Session):
    user = current_user(request, db)
    tenant = current_tenant(request, db)
    if not user:
        return None, None, redirect("/login")
    if not tenant:
        return None, None, redirect("/register")
    return user, tenant, None


def plan_meta(db: Session, tenant: Tenant) -> dict:
    product_count = db.query(func.count(Product.id)).filter(Product.tenant_id == tenant.id).scalar() or 0
    limit = tenant.plan.product_limit if tenant.plan else 100
    unlimited = limit is None or limit <= 0
    remaining = "Unlimited" if unlimited else max(0, limit - product_count)
    return {
        "product_count": product_count,
        "is_plan_unlimited": unlimited,
        "can_add_product": unlimited or product_count < limit,
        "remaining_products": remaining,
        "product_limit": limit,
        "plan_name": tenant.plan.name if tenant.plan else "Base",
        "price_weekly": tenant.plan.price_weekly if tenant.plan else 0,
        "banner_limit": tenant.plan.banner_limit if tenant.plan else 0,
    }


def admin_ctx(request: Request, tenant: Tenant, user, meta: dict, extra: dict | None = None) -> dict:
    ctx = template_globals(request)
    ctx.update({
        "current_tenant": tenant,
        "user": user,
        "page": request.url.path.split("/")[-1] or "dashboard",
        "currency": tenant.currency or "₹",
        **meta,
    })
    if extra:
        ctx.update(extra)
    return ctx


def pagination_items(current: int, total: int, delta: int = 2) -> list:
    rng = []
    out = []
    last = None
    for i in range(1, total + 1):
        if i == 1 or i == total or (current - delta <= i <= current + delta):
            rng.append(i)
    for i in rng:
        if last is not None:
            if i - last == 2:
                out.append(last + 1)
            elif i - last != 1:
                out.append("...")
        out.append(i)
        last = i
    return out


@router.get("", include_in_schema=False)
@router.get("/")
def admin_root():
    return redirect("/admin/dashboard")


@router.get("/dashboard", response_class=HTMLResponse)
def dashboard(request: Request, db: Session = Depends(get_db)):
    user, tenant, bounced = admin_guard(request, db)
    if bounced:
        return bounced
    meta = plan_meta(db, tenant)
    revenue, total_orders = db.query(
        func.coalesce(func.sum(Order.total_amount), 0),
        func.count(Order.id),
    ).filter(Order.tenant_id == tenant.id).first()
    active_products, total_views = db.query(
        func.count(Product.id),
        func.coalesce(func.sum(Product.views_count), 0),
    ).filter(Product.tenant_id == tenant.id, Product.status == "active").first()
    recent_orders = (
        db.query(Order)
        .options(joinedload(Order.items))
        .filter(Order.tenant_id == tenant.id)
        .order_by(Order.created_at.desc())
        .limit(5)
        .all()
    )
    
    # Calculate subscription and trial dates
    now = datetime.now()
    
    # Use explicit dates from DB, fallback to logic if NULL (for older tenants)
    sub_start = tenant.subscription_start if tenant.subscription_start else tenant.created_at + timedelta(days=90)
    sub_end = tenant.subscription_end if tenant.subscription_end else sub_start + timedelta(days=364)
    trial_start = tenant.trial_start if tenant.trial_start else tenant.created_at
    trial_end = tenant.trial_end if tenant.trial_end else trial_start + timedelta(days=90)
    
    # If currently in trial, focus on trial period logic
    in_trial = now <= trial_end
    
    if in_trial:
        days_left = (trial_end - now).days
    else:
        days_left = (sub_end - now).days
    
    return render(
        "admin/dashboard.html",
        admin_ctx(request, tenant, user, meta, {
            "page_title": "Merchant Overview",
            "page": "dashboard",
            "total_revenue": revenue or 0,
            "total_orders": total_orders or 0,
            "active_products": active_products or 0,
            "total_views": total_views or 0,
            "recent_orders": recent_orders,
            "new_store": request.query_params.get("new_store"),
            "sub_start": sub_start.strftime('%b %d, %Y'),
            "sub_end": sub_end.strftime('%b %d, %Y'),
            "trial_start": trial_start.strftime('%b %d, %Y'),
            "trial_end": trial_end.strftime('%b %d, %Y'),
            "days_left": max(0, days_left),
            "in_trial": in_trial,
        }),
    )


@router.get("/products", response_class=HTMLResponse)
def products_list(
    request: Request,
    db: Session = Depends(get_db),
    q: str = "",
    type: str = "",
    category: int = 0,
    per_page: int = 15,
    page: int = 1,
):
    user, tenant, bounced = admin_guard(request, db)
    if bounced:
        return bounced
    meta = plan_meta(db, tenant)
    per_page = per_page if per_page in ALLOWED_PER_PAGE else 15
    query = db.query(Product).outerjoin(Category, Product.category_id == Category.id).filter(Product.tenant_id == tenant.id)
    if q:
        like = f"%{q}%"
        query = query.filter(or_(Product.name.like(like), Product.sku.like(like), Product.description.like(like)))
    if type == "rental":
        query = query.filter(Product.is_rental == True)  # noqa: E712
    elif type == "retail":
        query = query.filter(Product.is_rental == False)  # noqa: E712
    if category > 0:
        query = query.filter(Product.category_id == category)
    total_filtered = query.with_entities(func.count(Product.id)).scalar() or 0
    total_pages = max(1, math.ceil(total_filtered / per_page))
    page = min(max(1, page), total_pages)
    offset = (page - 1) * per_page
    products = (
        query.options(joinedload(Product.images), joinedload(Product.category))
        .order_by(Product.created_at.desc())
        .offset(offset)
        .limit(per_page)
        .all()
    )
    categories = db.query(Category).filter(Category.tenant_id == tenant.id).order_by(Category.name.asc()).all()
    return render(
        "admin/products.html",
        admin_ctx(request, tenant, user, meta, {
            "page_title": "Product Inventory",
            "page": "products",
            "products": products,
            "categories": categories,
            "search": q,
            "filter_type": type,
            "filter_category": category,
            "per_page": per_page,
            "page_num": page,
            "total_pages": total_pages,
            "total_filtered": total_filtered,
            "from_item": offset + 1 if total_filtered else 0,
            "to_item": min(offset + per_page, total_filtered),
            "page_items": pagination_items(page, total_pages),
            "allowed_per_page": ALLOWED_PER_PAGE,
            "created": request.query_params.get("created"),
            "updated": request.query_params.get("updated"),
            "deleted": request.query_params.get("deleted"),
            "error": request.query_params.get("error"),
        }),
    )


@router.get("/products/add", response_class=HTMLResponse)
def add_product_get(request: Request, db: Session = Depends(get_db)):
    user, tenant, bounced = admin_guard(request, db)
    if bounced:
        return bounced
    meta = plan_meta(db, tenant)
    if not meta["can_add_product"]:
        return redirect(f"/admin/products?error=You have reached the maximum product limit ({meta['product_limit']}) for the {meta['plan_name']} plan. Please upgrade to the Pro plan.")
    categories = db.query(Category).filter(Category.tenant_id == tenant.id).order_by(Category.name.asc()).all()
    return render(
        "admin/product_form.html",
        admin_ctx(request, tenant, user, meta, {
            "page_title": "Add New Product",
            "page": "add_product",
            "product": None,
            "categories": categories,
            "error": "",
            "mode": "add",
        }),
    )


def _ensure_category(db: Session, tenant_id: int, category_id: int, new_name: str) -> int | None:
    new_name = clean_string(new_name)
    if new_name:
        cat_slug = slugify(new_name)
        existing = (
            db.query(Category)
            .filter(Category.tenant_id == tenant_id)
            .filter(or_(Category.name == new_name, Category.slug == cat_slug))
            .first()
        )
        if existing:
            return existing.id
        cat = Category(tenant_id=tenant_id, name=new_name, slug=cat_slug)
        db.add(cat)
        db.flush()
        return cat.id
    return category_id or None


@router.post("/products/add", response_class=HTMLResponse)
async def add_product_post(
    request: Request,
    db: Session = Depends(get_db),
    csrf_token: str = Form(""),
    name: str = Form(""),
    sku: str = Form(""),
    category_id: int = Form(0),
    new_category_name: str = Form(""),
    is_rental: str | None = Form(None),
    price: float = Form(0),
    rental_price_daily: float = Form(0),
    rental_price_weekend: float = Form(0),
    rental_deposit: float = Form(0),
    stock_quantity: int = Form(10),
    status: str = Form("active"),
    description: str = Form(""),
    product_image: UploadFile | None = File(None),
):
    user, tenant, bounced = admin_guard(request, db)
    if bounced:
        return bounced
    meta = plan_meta(db, tenant)
    if not meta["can_add_product"]:
        return redirect(f"/admin/products?error=You have reached the maximum product limit ({meta['product_limit']}) for the {meta['plan_name']} plan. Please upgrade to the Pro plan.")
    categories = db.query(Category).filter(Category.tenant_id == tenant.id).order_by(Category.name.asc()).all()
    error = ""
    if not verify_csrf(request, csrf_token):
        error = "Security session expired. Please reload and try again."
    else:
        name = clean_string(name)
        if not name:
            error = "Product title is required."
        else:
            sku = clean_string(sku) or (re.sub(r"[^a-zA-Z0-9]", "", name)[:4].upper() + f"-{random.randint(1000, 9999)}")
            try:
                cid = _ensure_category(db, tenant.id, category_id, new_category_name)
                product = Product(
                    tenant_id=tenant.id,
                    category_id=cid,
                    name=name,
                    slug=slugify(name),
                    sku=sku,
                    description=description.strip(),
                    price=Decimal(str(price)),
                    is_rental=bool(is_rental),
                    rental_price_daily=Decimal(str(rental_price_daily)),
                    rental_price_weekend=Decimal(str(rental_price_weekend)),
                    rental_deposit=Decimal(str(rental_deposit)),
                    stock_quantity=max(0, stock_quantity),
                    status="active" if status == "active" else "inactive",
                )
                db.add(product)
                db.flush()
                if product_image and product_image.filename:
                    up = process_upload(product_image, tenant.slug, "products")
                    if up.get("success"):
                        db.add(ProductImage(product_id=product.id, tenant_id=tenant.id, image_path=up["path"], is_primary=True))
                    else:
                        error = "Product saved, but image upload warning: " + up.get("error", "")
                db.commit()
                return redirect("/admin/products?created=1")
            except Exception as exc:
                db.rollback()
                error = f"Failed to create product: {exc}"
    return render(
        "admin/product_form.html",
        admin_ctx(request, tenant, user, meta, {
            "page_title": "Add New Product",
            "page": "add_product",
            "product": None,
            "categories": categories,
            "error": error,
            "mode": "add",
        }),
    )


@router.get("/products/{product_id}/edit", response_class=HTMLResponse)
def edit_product_get(product_id: int, request: Request, db: Session = Depends(get_db)):
    user, tenant, bounced = admin_guard(request, db)
    if bounced:
        return bounced
    product = (
        db.query(Product)
        .options(joinedload(Product.images))
        .filter(Product.id == product_id, Product.tenant_id == tenant.id)
        .first()
    )
    if not product:
        return redirect("/admin/products?error=Product not found or unauthorized.")
    categories = db.query(Category).filter(Category.tenant_id == tenant.id).order_by(Category.name.asc()).all()
    return render(
        "admin/product_form.html",
        admin_ctx(request, tenant, user, plan_meta(db, tenant), {
            "page_title": f"Edit Product: {product.name}",
            "page": "products",
            "product": product,
            "categories": categories,
            "error": "",
            "mode": "edit",
        }),
    )


@router.post("/products/{product_id}/edit", response_class=HTMLResponse)
async def edit_product_post(
    product_id: int,
    request: Request,
    db: Session = Depends(get_db),
    csrf_token: str = Form(""),
    name: str = Form(""),
    sku: str = Form(""),
    category_id: int = Form(0),
    is_rental: str | None = Form(None),
    price: float = Form(0),
    rental_price_daily: float = Form(0),
    rental_price_weekend: float = Form(0),
    rental_deposit: float = Form(0),
    stock_quantity: int = Form(0),
    status: str = Form("active"),
    description: str = Form(""),
    product_image: UploadFile | None = File(None),
):
    user, tenant, bounced = admin_guard(request, db)
    if bounced:
        return bounced
    product = (
        db.query(Product)
        .options(joinedload(Product.images))
        .filter(Product.id == product_id, Product.tenant_id == tenant.id)
        .first()
    )
    if not product:
        return redirect("/admin/products?error=Product not found or unauthorized.")
    error = ""
    if not verify_csrf(request, csrf_token):
        error = "Security session expired. Please reload and try again."
    else:
        name = clean_string(name)
        if not name:
            error = "Product title is required."
        else:
            try:
                product.name = name
                product.sku = clean_string(sku)
                product.category_id = category_id or None
                product.description = description.strip()
                product.price = Decimal(str(price))
                product.is_rental = bool(is_rental)
                product.rental_price_daily = Decimal(str(rental_price_daily))
                product.rental_price_weekend = Decimal(str(rental_price_weekend))
                product.rental_deposit = Decimal(str(rental_deposit))
                product.stock_quantity = max(0, stock_quantity)
                product.status = "active" if status == "active" else "inactive"
                if product_image and product_image.filename:
                    up = process_upload(product_image, tenant.slug, "products")
                    if up.get("success"):
                        for img in product.images:
                            img.is_primary = False
                        db.add(ProductImage(product_id=product.id, tenant_id=tenant.id, image_path=up["path"], is_primary=True))
                    else:
                        error = "Product updated, but image conversion warning: " + up.get("error", "")
                db.commit()
                return redirect("/admin/products?updated=1")
            except Exception as exc:
                db.rollback()
                error = f"Failed to update product: {exc}"
    categories = db.query(Category).filter(Category.tenant_id == tenant.id).order_by(Category.name.asc()).all()
    return render(
        "admin/product_form.html",
        admin_ctx(request, tenant, user, plan_meta(db, tenant), {
            "page_title": f"Edit Product: {product.name}",
            "page": "products",
            "product": product,
            "categories": categories,
            "error": error,
            "mode": "edit",
        }),
    )


@router.post("/products/{product_id}/delete")
async def delete_product(product_id: int, request: Request, db: Session = Depends(get_db), csrf_token: str = Form("")):
    user, tenant, bounced = admin_guard(request, db)
    if bounced:
        return bounced
    if not verify_csrf(request, csrf_token):
        return redirect("/admin/products?error=Security session expired.")
    product = db.query(Product).options(joinedload(Product.images)).filter(Product.id == product_id, Product.tenant_id == tenant.id).first()
    if not product:
        return redirect("/admin/products?error=Unauthorized or product does not exist.")
    try:
        for img in product.images:
            if img.image_path and "sample" not in img.image_path:
                path = BASE_DIR / img.image_path
                if path.exists():
                    path.unlink()
        db.delete(product)
        db.commit()
        return redirect("/admin/products?deleted=1")
    except Exception as exc:
        db.rollback()
        return redirect(f"/admin/products?error=Failed to delete product: {exc}")


@router.get("/categories", response_class=HTMLResponse)
def categories_page(request: Request, db: Session = Depends(get_db)):
    user, tenant, bounced = admin_guard(request, db)
    if bounced:
        return bounced
    cats = (
        db.query(Category, func.count(Product.id).label("product_count"))
        .outerjoin(Product, (Product.category_id == Category.id) & (Product.tenant_id == Category.tenant_id))
        .filter(Category.tenant_id == tenant.id)
        .group_by(Category.id)
        .order_by(Category.name.asc())
        .all()
    )
    rows = [{"cat": c, "product_count": n} for c, n in cats]
    return render(
        "admin/categories.html",
        admin_ctx(request, tenant, user, plan_meta(db, tenant), {
            "page_title": "Manage Categories",
            "page": "categories",
            "categories": rows,
            "error": request.query_params.get("error") or "",
            "success": request.query_params.get("success") or "",
        }),
    )


@router.post("/categories")
async def categories_post(
    request: Request,
    db: Session = Depends(get_db),
    csrf_token: str = Form(""),
    add_category: str | None = Form(None),
    delete_category: str | None = Form(None),
    name: str = Form(""),
    category_id: int = Form(0),
):
    user, tenant, bounced = admin_guard(request, db)
    if bounced:
        return bounced
    if not verify_csrf(request, csrf_token):
        return redirect("/admin/categories?error=Security session expired.")
    if add_category:
        name = clean_string(name)
        if not name:
            return redirect("/admin/categories?error=Category name is required.")
        cat_slug = slugify(name)
        exists = (
            db.query(Category)
            .filter(Category.tenant_id == tenant.id)
            .filter(or_(Category.name == name, Category.slug == cat_slug))
            .first()
        )
        if exists:
            return redirect("/admin/categories?error=A category with this name already exists in your store.")
        db.add(Category(tenant_id=tenant.id, name=name, slug=cat_slug))
        db.commit()
        return redirect("/admin/categories?success=Category added successfully!")
    if delete_category:
        cat = db.query(Category).filter(Category.id == category_id, Category.tenant_id == tenant.id).first()
        if not cat:
            return redirect("/admin/categories?error=Unauthorized category deletion.")
        db.query(Product).filter(Product.category_id == cat.id, Product.tenant_id == tenant.id).update({Product.category_id: None})
        db.delete(cat)
        db.commit()
        return redirect("/admin/categories?success=Category removed successfully.")
    return redirect("/admin/categories")


@router.get("/orders", response_class=HTMLResponse)
def orders_list(request: Request, db: Session = Depends(get_db), status: str = "", q: str = ""):
    user, tenant, bounced = admin_guard(request, db)
    if bounced:
        return bounced
    query = db.query(Order).options(joinedload(Order.items)).filter(Order.tenant_id == tenant.id)
    if status in ("pending", "processing", "completed", "cancelled"):
        query = query.filter(Order.status == status)
    if q:
        like = f"%{q}%"
        query = query.filter(or_(
            Order.order_number.like(like),
            Order.customer_name.like(like),
            Order.customer_email.like(like),
            Order.customer_phone.like(like),
        ))
    orders = query.order_by(Order.created_at.desc()).all()
    return render(
        "admin/orders.html",
        admin_ctx(request, tenant, user, plan_meta(db, tenant), {
            "page_title": "Customer Orders",
            "page": "orders",
            "orders": orders,
            "status_filter": status,
            "search": q,
            "updated": request.query_params.get("updated"),
        }),
    )


@router.get("/orders/{order_id}", response_class=HTMLResponse)
def order_detail(order_id: int, request: Request, db: Session = Depends(get_db)):
    user, tenant, bounced = admin_guard(request, db)
    if bounced:
        return bounced
    order = db.query(Order).options(joinedload(Order.items)).filter(Order.id == order_id, Order.tenant_id == tenant.id).first()
    if not order:
        return redirect("/admin/orders?error=Order not found or unauthorized.")
    return render(
        "admin/order_detail.html",
        admin_ctx(request, tenant, user, plan_meta(db, tenant), {
            "page_title": "Order Details",
            "page": "orders",
            "order": order,
            "error": "",
            "updated": request.query_params.get("updated"),
        }),
    )


@router.post("/orders/{order_id}")
async def order_update(
    order_id: int,
    request: Request,
    db: Session = Depends(get_db),
    csrf_token: str = Form(""),
    status: str = Form("pending"),
    payment_status: str = Form("pending"),
):
    user, tenant, bounced = admin_guard(request, db)
    if bounced:
        return bounced
    if not verify_csrf(request, csrf_token):
        return redirect(f"/admin/orders/{order_id}")
    order = db.query(Order).filter(Order.id == order_id, Order.tenant_id == tenant.id).first()
    if not order:
        return redirect("/admin/orders")
    if status in ("pending", "processing", "completed", "cancelled") and payment_status in ("pending", "paid", "refunded"):
        order.status = status
        order.payment_status = payment_status
        db.commit()
        return redirect(f"/admin/orders/{order_id}?updated=1")
    return redirect(f"/admin/orders/{order_id}")


@router.get("/settings", response_class=HTMLResponse)
def settings_get(request: Request, db: Session = Depends(get_db)):
    user, tenant, bounced = admin_guard(request, db)
    if bounced:
        return bounced
    return render(
        "admin/settings.html",
        admin_ctx(request, tenant, user, plan_meta(db, tenant), {
            "page_title": "Store Settings & Branding",
            "page": "settings",
            "theme": get_store_theme(tenant),
            "presets": THEME_PRESETS,
            "banners": tenant.banners,
            "error": "",
            "success": "",
        }),
    )


@router.post("/settings", response_class=HTMLResponse)
async def settings_post(
    request: Request,
    db: Session = Depends(get_db),
    csrf_token: str = Form(""),
    name: str = Form(""),
    tagline: str = Form(""),
    currency: str = Form("₹"),
    contact_email: str = Form(""),
    contact_phone: str = Form(""),
    description: str = Form(""),
    address: str = Form(""),
    national_id_number: str = Form(""),
    store_logo: UploadFile | None = File(None),
):
    user, tenant, bounced = admin_guard(request, db)
    if bounced:
        return bounced
    form = await request.form()
    error = ""
    success = ""
    if not verify_csrf(request, csrf_token):
        error = "Security session expired. Please reload and try again."
    else:
        name = clean_string(name)
        if not name:
            error = "Store name is required."
        else:
            theme_settings = {
                "bg_color": clean_string(form.get("theme_bg_color") or "#f8fafc"),
                "card_bg": clean_string(form.get("theme_card_bg") or "#ffffff"),
                "card_border": clean_string(form.get("theme_card_border") or "#e2e8f0"),
                "header_bg": clean_string(form.get("theme_header_bg") or "#ffffff"),
                "header_text": clean_string(form.get("theme_header_text") or "#0f172a"),
                "text_color": clean_string(form.get("theme_text_color") or "#0f172a"),
                "text_muted": clean_string(form.get("theme_text_muted") or "#64748b"),
                "primary_color": clean_string(form.get("theme_primary_color") or "#0f172a"),
                "primary_hover": clean_string(form.get("theme_primary_hover") or "#334155"),
                "primary_text": clean_string(form.get("theme_primary_text") or "#ffffff"),
                "accent_color": clean_string(form.get("theme_accent_color") or "#2563eb"),
                "border_color": clean_string(form.get("theme_border_color") or "#e2e8f0"),
                "footer_bg": clean_string(form.get("theme_footer_bg") or "#ffffff"),
                "footer_text": clean_string(form.get("theme_footer_text") or "#64748b"),
                "input_bg": clean_string(form.get("theme_input_bg") or "#ffffff"),
                "input_border": clean_string(form.get("theme_input_border") or "#cbd5e1"),
            }
            logo_path = tenant.logo
            banner_path = tenant.banner
            if store_logo and store_logo.filename:
                up = process_upload(store_logo, tenant.slug, "branding")
                if up.get("success"):
                    logo_path = up["path"]
                else:
                    error = "Logo warning: " + up.get("error", "")
            
            # Handle banner deletions
            delete_ids = form.getlist("delete_banner")
            if delete_ids:
                for banner in tenant.banners:
                    if str(banner.id) in delete_ids:
                        db.delete(banner)
                db.flush()

            # Handle multiple banner uploads
            meta = plan_meta(db, tenant)
            banner_limit = meta["plan"].banner_limit
            
            store_banners = form.getlist("store_banners")
            current_count = db.query(func.count(TenantBanner.id)).filter(TenantBanner.tenant_id == tenant.id).scalar()
            
            for file in store_banners:
                if hasattr(file, "filename") and file.filename:
                    if current_count >= banner_limit:
                        error = f"Banner limit ({banner_limit}) reached for your plan."
                        break
                    up = process_upload(file, tenant.slug, "branding")
                    if up.get("success"):
                        new_banner = TenantBanner(tenant_id=tenant.id, image_path=up["path"])
                        db.add(new_banner)
                        current_count += 1
                    else:
                        error = "Banner warning: " + up.get("error", "")
            
            if banner_limit > 0:
                tenant.hide_default_banner = form.get("hide_default_banner") == "on"
            else:
                tenant.hide_default_banner = False
                
            tenant.name = name
            tenant.tagline = clean_string(tagline)
            tenant.currency = "₹"
            tenant.theme_color = theme_settings["primary_color"]
            tenant.theme_settings = json.dumps(theme_settings)
            tenant.contact_email = clean_string(contact_email)
            tenant.contact_phone = clean_string(contact_phone)
            tenant.description = description.strip()
            tenant.logo = logo_path
            tenant.banner = banner_path
            
            user.address = clean_string(address)
            user.national_id_number = clean_string(national_id_number)
            
            db.commit()
            request.session["tenant_name"] = name
            success = "Store branding and theme color customizations updated successfully!"
    return render(
        "admin/settings.html",
        admin_ctx(request, tenant, user, plan_meta(db, tenant), {
            "page_title": "Store Settings & Branding",
            "page": "settings",
            "theme": get_store_theme(tenant),
            "presets": THEME_PRESETS,
            "error": error,
            "success": success,
        }),
    )


@router.get("/payments", response_class=HTMLResponse)
def payments_get(request: Request, db: Session = Depends(get_db)):
    user, tenant, bounced = admin_guard(request, db)
    if bounced:
        return bounced
    return render(
        "admin/payments.html",
        admin_ctx(request, tenant, user, plan_meta(db, tenant), {
            "page_title": "Payment Methods & Gateways",
            "page": "payments",
            "error": "",
            "success": "",
        }),
    )


@router.post("/payments", response_class=HTMLResponse)
async def payments_post(
    request: Request,
    db: Session = Depends(get_db),
    csrf_token: str = Form(""),
    enable_upi: str | None = Form(None),
    enable_bank: str | None = Form(None),
    enable_card: str | None = Form(None),
    upi_id: str = Form(""),
    bank_details: str = Form(""),
    upi_qr_image: UploadFile | None = File(None),
):
    user, tenant, bounced = admin_guard(request, db)
    if bounced:
        return bounced
    error = ""
    success = ""
    if not verify_csrf(request, csrf_token):
        error = "Security session expired. Please reload and try again."
    else:
        qr = tenant.upi_qr_image
        if upi_qr_image and upi_qr_image.filename:
            up = process_upload(upi_qr_image, tenant.slug, "branding")
            if up.get("success"):
                qr = up["path"]
            else:
                error = "QR Code upload warning: " + up.get("error", "")
        if not error:
            tenant.enable_upi = bool(enable_upi)
            tenant.enable_cod = False
            tenant.enable_bank = bool(enable_bank)
            tenant.enable_card = bool(enable_card)
            tenant.upi_id = clean_string(upi_id)
            tenant.upi_qr_image = qr
            tenant.bank_details = bank_details.strip()
            db.commit()
            success = "Payment methods updated successfully!"
    return render(
        "admin/payments.html",
        admin_ctx(request, tenant, user, plan_meta(db, tenant), {
            "page_title": "Payment Methods & Gateways",
            "page": "payments",
            "error": error,
            "success": success,
        }),
    )
