import math
import secrets
from datetime import date, datetime, timedelta
from decimal import Decimal

from fastapi import APIRouter, Depends, File, Form, Request, UploadFile
from fastapi.responses import HTMLResponse
from sqlalchemy import func, or_
from sqlalchemy.orm import Session, joinedload

from app.database import get_db
from app.deps import redirect, template_globals
from app.images import process_upload
from app.mailer import send_order_confirmation
from app.models import Category, Order, OrderItem, Product, Tenant
from app.security import clean_string, verify_csrf
from app.templating import render
from app.theme import render_store_theme_css
router = APIRouter()

ALLOWED_LIMITS = [12, 16, 24, 48, 100]


def get_active_tenant(db: Session, slug: str) -> Tenant | None:
    return (
        db.query(Tenant)
        .options(joinedload(Tenant.plan))
        .filter(Tenant.slug == slug, Tenant.status == "active")
        .first()
    )


def cart_items(request: Request, slug: str) -> dict:
    carts = request.session.get("carts") or {}
    return carts.get(slug) or {}


def save_cart(request: Request, slug: str, items: dict) -> None:
    carts = request.session.get("carts") or {}
    carts[slug] = items
    request.session["carts"] = carts


def cart_count(request: Request, slug: str) -> int:
    return sum(int(item.get("qty") or 1) for item in cart_items(request, slug).values())


def store_ctx(request: Request, tenant: Tenant, extra: dict | None = None) -> dict:
    ctx = template_globals(request)
    ctx.update({
        "tenant": tenant,
        "store_slug": tenant.slug,
        "currency": tenant.currency or "₹",
        "cart_count": cart_count(request, tenant.slug),
        "theme_css": render_store_theme_css(tenant),
        "year": datetime.now().year,
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


@router.get("/store/{slug}", response_class=HTMLResponse)
def storefront(
    slug: str,
    request: Request,
    db: Session = Depends(get_db),
    q: str = "",
    category: str = "",
    type: str = "",
    sort: str = "newest",
    limit: int = 16,
    page: int = 1,
):
    tenant = get_active_tenant(db, slug)
    if not tenant:
        ctx = template_globals(request)
        ctx.update({"slug": slug, "year": datetime.now().year})
        return render("platform/store_not_found.html", ctx, status_code=404)

    categories = db.query(Category).filter(Category.tenant_id == tenant.id).order_by(Category.name.asc()).all()
    per_page = limit if limit in ALLOWED_LIMITS else 16
    current_page = max(1, page)

    query = db.query(Product).outerjoin(Category, Product.category_id == Category.id).filter(
        Product.tenant_id == tenant.id, Product.status == "active"
    )
    if q:
        like = f"%{q}%"
        query = query.filter(or_(Product.name.like(like), Product.description.like(like), Product.sku.like(like)))
    if category:
        query = query.filter(Category.slug == category)
    if type == "rental":
        query = query.filter(Product.is_rental == True)  # noqa: E712
    elif type == "retail":
        query = query.filter(Product.is_rental == False)  # noqa: E712

    total_products = query.with_entities(func.count(Product.id)).scalar() or 0
    total_pages = max(1, math.ceil(total_products / per_page))
    current_page = min(current_page, total_pages)
    offset = (current_page - 1) * per_page

    if sort == "price_asc":
        query = query.order_by(Product.price.asc())
    elif sort == "price_desc":
        query = query.order_by(Product.price.desc())
    elif sort == "popular":
        query = query.order_by(Product.views_count.desc())
    else:
        query = query.order_by(Product.created_at.desc())

    products = query.options(joinedload(Product.images), joinedload(Product.category)).offset(offset).limit(per_page).all()
    from_item = offset + 1 if total_products else 0
    to_item = min(offset + per_page, total_products)

    return render(
        "store/store.html",
        store_ctx(request, tenant, {
            "categories": categories,
            "products": products,
            "search_query": q,
            "category_filter": category,
            "rental_filter": type,
            "sort_by": sort,
            "per_page": per_page,
            "current_page": current_page,
            "total_pages": total_pages,
            "total_products": total_products,
            "from_item": from_item,
            "to_item": to_item,
            "page_items": pagination_items(current_page, total_pages),
            "allowed_limits": ALLOWED_LIMITS,
        }),
    )


@router.get("/store/{slug}/product/{product_id}", response_class=HTMLResponse)
def product_detail(slug: str, product_id: int, request: Request, db: Session = Depends(get_db)):
    tenant = get_active_tenant(db, slug)
    if not tenant:
        return redirect("/")
    product = (
        db.query(Product)
        .options(joinedload(Product.images), joinedload(Product.category))
        .filter(Product.id == product_id, Product.tenant_id == tenant.id, Product.status == "active")
        .first()
    )
    if not product:
        ctx = store_ctx(request, tenant)
        return render("store/product_not_found.html", ctx, status_code=404)
    product.views_count = (product.views_count or 0) + 1
    db.commit()

    related = (
        db.query(Product)
        .options(joinedload(Product.images))
        .filter(Product.tenant_id == tenant.id, Product.id != product.id, Product.status == "active")
        .order_by(Product.created_at.desc())
        .limit(4)
        .all()
    )
    tomorrow = (date.today() + timedelta(days=1)).isoformat()
    today = date.today().isoformat()
    return render(
        "store/product.html",
        store_ctx(request, tenant, {
            "product": product,
            "images": sorted(product.images, key=lambda i: (not i.is_primary, i.id or 0)),
            "related_products": related,
            "tomorrow": tomorrow,
            "today": today,
        }),
    )


@router.get("/store/{slug}/cart", response_class=HTMLResponse)
def cart_get(slug: str, request: Request, db: Session = Depends(get_db), action: str = "", key: str = "", added: str = ""):
    tenant = get_active_tenant(db, slug)
    if not tenant:
        return redirect("/")
    items = cart_items(request, slug)
    if action == "remove" and key in items:
        items.pop(key, None)
        save_cart(request, slug, items)
        return redirect(f"/store/{slug}/cart")
    if action == "clear":
        save_cart(request, slug, {})
        return redirect(f"/store/{slug}/cart")
    subtotal = sum(float(i.get("line_total") or 0) for i in items.values())
    return render(
        "store/cart.html",
        store_ctx(request, tenant, {
            "items": items,
            "subtotal": subtotal,
            "added": added,
            "error": "",
        }),
    )


@router.post("/store/{slug}/cart", response_class=HTMLResponse)
async def cart_add(
    slug: str,
    request: Request,
    db: Session = Depends(get_db),
    csrf_token: str = Form(""),
    product_id: int = Form(0),
    quantity: int = Form(1),
    rental_type: str = Form("daily"),
    rental_days: int = Form(1),
    rental_start_date: str = Form(""),
):
    tenant = get_active_tenant(db, slug)
    if not tenant:
        return redirect("/")
    if not verify_csrf(request, csrf_token):
        items = cart_items(request, slug)
        subtotal = sum(float(i.get("line_total") or 0) for i in items.values())
        return render(
            "store/cart.html",
            store_ctx(request, tenant, {"items": items, "subtotal": subtotal, "added": "", "error": "Session expired. Please try again."}),
        )
    product = (
        db.query(Product)
        .options(joinedload(Product.images))
        .filter(Product.id == product_id, Product.tenant_id == tenant.id, Product.status == "active")
        .first()
    )
    if not product:
        return redirect(f"/store/{slug}/cart")
    items = cart_items(request, slug)
    image = product.primary_image
    if product.is_rental:
        rental_type = "weekend" if rental_type == "weekend" else "daily"
        rental_days = max(1, rental_days)
        rental_start = clean_string(rental_start_date) or (date.today() + timedelta(days=1)).isoformat()
        if rental_type == "weekend":
            unit_price = float(product.rental_price_weekend or 0)
            calc_total = unit_price
            item_key = f"p_{product.id}_weekend"
            spec_text = f"Weekend Rental (Start: {rental_start})"
        else:
            unit_price = float(product.rental_price_daily or 0)
            calc_total = unit_price * rental_days
            item_key = f"p_{product.id}_daily_{rental_days}d"
            spec_text = f"{rental_days} Day(s) Rental (Start: {rental_start})"
        items[item_key] = {
            "product_id": product.id,
            "name": product.name,
            "sku": product.sku,
            "image": image,
            "is_rental": True,
            "rental_type": rental_type,
            "rental_days": rental_days,
            "rental_start": rental_start,
            "spec_text": spec_text,
            "unit_price": unit_price,
            "line_total": calc_total,
            "qty": 1,
        }
    else:
        qty = max(1, quantity)
        item_key = f"p_{product.id}_retail"
        unit_price = float(product.price or 0)
        if item_key in items:
            new_qty = int(items[item_key].get("qty") or 1) + qty
            items[item_key]["qty"] = new_qty
            items[item_key]["line_total"] = new_qty * unit_price
        else:
            items[item_key] = {
                "product_id": product.id,
                "name": product.name,
                "sku": product.sku,
                "image": image,
                "is_rental": False,
                "unit_price": unit_price,
                "qty": qty,
                "line_total": qty * unit_price,
                "spec_text": "Standard Purchase",
            }
    save_cart(request, slug, items)
    return redirect(f"/store/{slug}/cart?added=1")


@router.get("/store/{slug}/checkout", response_class=HTMLResponse)
def checkout_get(slug: str, request: Request, db: Session = Depends(get_db)):
    tenant = get_active_tenant(db, slug)
    if not tenant:
        return redirect("/")
    items = cart_items(request, slug)
    if not items:
        return redirect(f"/store/{slug}")
    subtotal = sum(float(i.get("line_total") or 0) for i in items.values())
    selected = "upi" if tenant.enable_upi else ("bank_transfer" if tenant.enable_bank else "")
    return render(
        "store/checkout.html",
        store_ctx(request, tenant, {
            "items": items,
            "subtotal": subtotal,
            "error": "",
            "form": {},
            "selected_method": selected,
        }),
    )


@router.post("/store/{slug}/checkout", response_class=HTMLResponse)
async def checkout_post(
    slug: str,
    request: Request,
    db: Session = Depends(get_db),
    csrf_token: str = Form(""),
    customer_name: str = Form(""),
    customer_email: str = Form(""),
    customer_phone: str = Form(""),
    shipping_address: str = Form(""),
    city: str = Form(""),
    postal_code: str = Form(""),
    payment_method: str = Form("upi"),
    transaction_ref: str = Form(""),
    notes: str = Form(""),
    payment_proof: UploadFile | None = File(None),
):
    tenant = get_active_tenant(db, slug)
    if not tenant:
        return redirect("/")
    items = cart_items(request, slug)
    if not items:
        return redirect(f"/store/{slug}")
    subtotal = sum(float(i.get("line_total") or 0) for i in items.values())
    form = {
        "customer_name": customer_name,
        "customer_email": customer_email,
        "customer_phone": customer_phone,
        "shipping_address": shipping_address,
        "city": city,
        "postal_code": postal_code,
        "transaction_ref": transaction_ref,
        "notes": notes,
    }
    error = ""
    payment_proof_path = None
    if not verify_csrf(request, csrf_token):
        error = "Session security token expired. Please reload and submit again."
    else:
        customer_name = clean_string(customer_name)
        customer_email = clean_string(customer_email)
        customer_phone = clean_string(customer_phone)
        shipping_address = clean_string(shipping_address)
        city = clean_string(city)
        postal_code = clean_string(postal_code)
        payment_method = clean_string(payment_method)
        transaction_ref = clean_string(transaction_ref)
        notes = clean_string(notes)
        if not customer_name or not customer_email or not customer_phone or not shipping_address:
            error = "Please fill in all required customer and delivery address fields."
        elif "@" not in customer_email:
            error = "Please enter a valid email address."
        elif payment_method == "upi":
            if not tenant.enable_upi:
                error = "UPI payments are not enabled for this store."
            elif not transaction_ref:
                error = "Please enter your UPI transaction reference number / UTR ID."
            elif not payment_proof or not payment_proof.filename:
                error = "Please upload your UPI payment confirmation screenshot."
            else:
                up_res = process_upload(payment_proof, slug, "payments")
                if not up_res.get("success"):
                    error = "Payment screenshot error: " + (up_res.get("error") or "upload failed")
                else:
                    payment_proof_path = up_res["path"]
        elif payment_method == "cod":
            error = "Cash on Delivery is currently in a frozen state and unavailable for orders."
        elif payment_method == "bank_transfer":
            if not tenant.enable_bank:
                error = "Bank Wire transfer is currently disabled by this store."
        elif payment_method == "card":
            error = "Card payment gateway is coming soon and is currently unavailable."
        else:
            error = "Please select a valid payment method."

        if not error:
            try:
                order_number = f"GLV-{slug[:4].upper()}-{datetime.now().strftime('%Y%m%d')}-{secrets.token_hex(2).upper()}"
                payment_status = "paid" if payment_method == "card" else "pending"
                order = Order(
                    tenant_id=tenant.id,
                    order_number=order_number,
                    customer_name=customer_name,
                    customer_email=customer_email,
                    customer_phone=customer_phone,
                    shipping_address=shipping_address,
                    city=city,
                    postal_code=postal_code,
                    total_amount=Decimal(str(subtotal)),
                    payment_method=payment_method,
                    payment_status=payment_status,
                    payment_proof=payment_proof_path,
                    transaction_ref=transaction_ref,
                    status="pending",
                    notes=notes,
                )
                db.add(order)
                db.flush()
                for item in items.values():
                    start = item.get("rental_start") or None
                    start_date = None
                    if start:
                        try:
                            start_date = date.fromisoformat(str(start)[:10])
                        except ValueError:
                            start_date = None
                    db.add(OrderItem(
                        order_id=order.id,
                        tenant_id=tenant.id,
                        product_id=item.get("product_id"),
                        product_name=item.get("name"),
                        is_rental=bool(item.get("is_rental")),
                        rental_type=item.get("rental_type"),
                        rental_start_date=start_date,
                        rental_days=item.get("rental_days"),
                        quantity=int(item.get("qty") or 1),
                        unit_price=Decimal(str(item.get("unit_price") or 0)),
                        line_total=Decimal(str(item.get("line_total") or 0)),
                        total_price=Decimal(str(item.get("line_total") or 0)),
                    ))
                    if not item.get("is_rental"):
                        prod = db.get(Product, item.get("product_id"))
                        if prod and prod.tenant_id == tenant.id:
                            prod.stock_quantity = max(0, (prod.stock_quantity or 0) - int(item.get("qty") or 1))
                db.commit()
                try:
                    send_order_confirmation(
                        {
                            "order_number": order_number,
                            "customer_name": customer_name,
                            "customer_email": customer_email,
                            "payment_method": payment_method,
                            "payment_status": payment_status,
                            "total_amount": subtotal,
                        },
                        tenant,
                        list(items.values()),
                    )
                except Exception:
                    pass
                save_cart(request, slug, {})
                return redirect(f"/store/{slug}/order/{order_number}")
            except Exception as exc:
                db.rollback()
                error = f"Failed to place order: {exc}"

    return render(
        "store/checkout.html",
        store_ctx(request, tenant, {
            "items": items,
            "subtotal": subtotal,
            "error": error,
            "form": form,
            "selected_method": payment_method,
        }),
    )


@router.get("/store/{slug}/order/{order_number}", response_class=HTMLResponse)
def order_success(slug: str, order_number: str, request: Request, db: Session = Depends(get_db)):
    tenant = get_active_tenant(db, slug)
    if not tenant:
        return redirect("/")
    order = (
        db.query(Order)
        .options(joinedload(Order.items))
        .filter(Order.order_number == order_number, Order.tenant_id == tenant.id)
        .first()
    )
    if not order:
        return redirect(f"/store/{slug}")
    return render("store/order_success.html", store_ctx(request, tenant, {"order": order}))
