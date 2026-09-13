import random
from datetime import datetime, timedelta

from fastapi import APIRouter, Depends, Form, Request, UploadFile, File
from fastapi.responses import HTMLResponse
from sqlalchemy import func
from sqlalchemy.orm import Session, joinedload

from app.config import settings
from app.database import get_db
from app.deps import login_user, logout_user, redirect, template_globals
from app.models import Plan, Product, Tenant, User, Category, Page
from app.security import clean_string, hash_password, parse_features, slugify, verify_csrf, verify_password
from app.templating import render
from app.images import process_upload
router = APIRouter()

BUSINESS_THEMES = {
    "Rental Jewellery": "#d97706",
    "Mobile Cases": "#2563eb",
    "Perfumes & Fragrances": "#7c3aed",
}


def currency_symbol(currency: str) -> str:
    return {"USD": "$", "EUR": "€", "GBP": "£"}.get(currency, "₹")


@router.get("/", response_class=HTMLResponse)
def home(request: Request, db: Session = Depends(get_db)):
    tenants = db.query(Tenant).filter(Tenant.status == "active").order_by(Tenant.id.asc()).all()
    counts = dict(
        db.query(Product.tenant_id, func.count(Product.id))
        .filter(Product.status == "active")
        .group_by(Product.tenant_id)
        .all()
    )
    store_rows = [{"tenant": tenant, "product_count": counts.get(tenant.id, 0)} for tenant in tenants]
    plans = db.query(Plan).order_by(Plan.price_weekly.asc()).all()
    plan_cards = []
    for p in plans:
        plan_cards.append({"plan": p, "features": parse_features(p.features_json)})
    ctx = template_globals(request)
    ctx.update({"stores": store_rows, "plans": plan_cards, "year": datetime.now().year, "app_name": settings.APP_NAME})
    return render("platform/index.html", ctx)


@router.get("/register", response_class=HTMLResponse)
def register_get(request: Request, db: Session = Depends(get_db), plan: str = "base"):
    if request.session.get("user_id") and request.session.get("tenant_id"):
        return redirect("/admin/dashboard")
    plans = db.query(Plan).order_by(Plan.price_weekly.asc()).all()
    terms_page = db.query(Page).filter(Page.slug == "terms").first()
    ctx = template_globals(request)
    ctx.update({"plans": plans, "selected_plan": plan, "error": "", "form": {}, "year": datetime.now().year, "terms_page": terms_page})
    return render("platform/register.html", ctx)


@router.post("/register", response_class=HTMLResponse)
def register_post(
    request: Request,
    db: Session = Depends(get_db),
    csrf_token: str = Form(""),
    name: str = Form(""),
    email: str = Form(""),
    phone: str = Form(""),
    whatsapp: str = Form(""),
    country: str = Form(""),
    password: str = Form(""),
    confirm_password: str = Form(""),
    store_name: str = Form(""),
    store_slug: str = Form(""),
    business_type: str = Form("General Retail"),
    tagline: str = Form(""),
    support_email: str = Form(""),
    contact_phone: str = Form(""),
    plan_id: int = Form(1),
    currency: str = Form("₹"),
    transaction_id: str = Form(""),
    subscription_proof: UploadFile | None = File(None),
):
    plans = db.query(Plan).order_by(Plan.price_weekly.asc()).all()
    form = {
        "name": name,
        "email": email,
        "phone": phone,
        "whatsapp": whatsapp,
        "country": country,
        "store_name": store_name,
        "store_slug": store_slug,
        "business_type": business_type,
        "tagline": tagline,
        "support_email": support_email,
        "contact_phone": contact_phone,
        "plan_id": plan_id,
        "currency": currency,
        "transaction_id": transaction_id,
    }
    error = ""
    if not verify_csrf(request, csrf_token):
        error = "Security session expired. Please refresh and try again."
    else:
        name = clean_string(name)
        email = (email or "").strip().lower()
        support_email = (support_email or email).strip().lower()
        store_name = clean_string(store_name)
        store_slug = slugify(store_slug or store_name)
        business_type = clean_string(business_type)
        tagline = clean_string(tagline)[:50]
        
        if not name or not email or not password or not store_name or not support_email:
            error = "Please fill in all required fields."
        elif len(password) < 8:
            error = "Password must be at least 8 characters long."
        elif password != confirm_password:
            error = "Passwords do not match."
        elif db.query(User).filter(User.email == email).first():
            error = "An account with this email already exists. Please log in."
        else:
            if db.query(Tenant).filter(Tenant.slug == store_slug).first():
                store_slug = f"{store_slug}-{random.randint(10, 99)}"
            
            proof_path = None
            if subscription_proof and subscription_proof.filename:
                up = process_upload(subscription_proof, store_slug, "branding")
                if up.get("success"):
                    proof_path = up["path"]
                else:
                    error = "Payment proof upload failed: " + up.get("error", "")

            if not error:
                try:
                    user = User(
                        name=name, 
                        email=email, 
                        phone=clean_string(phone),
                        whatsapp=clean_string(whatsapp),
                        country=clean_string(country),
                        password_hash=hash_password(password), 
                        role="seller", 
                        status="active"
                    )
                    db.add(user)
                    db.flush()
                    
                    now = datetime.now()
                    plan = db.query(Plan).filter(Plan.id == plan_id).first()
                    trial_days = plan.trial_days if plan else 90
                    sub_days = (plan.week_count * 7) if plan else 364
                    
                    trial_end = now + timedelta(days=trial_days)
                    sub_end = trial_end + timedelta(days=sub_days)
                    
                    tenant = Tenant(
                        user_id=user.id,
                        plan_id=plan_id,
                        name=store_name,
                        slug=store_slug,
                        business_type=business_type,
                        tagline=tagline or f"Welcome to {store_name}",
                        currency="₹",
                        currency_symbol="₹",
                        theme_color=BUSINESS_THEMES.get(business_type, "#4f46e5"),
                        contact_email=support_email,
                        contact_phone=clean_string(contact_phone),
                        status="active",
                        enable_upi=True,
                        subscription_proof=proof_path,
                        subscription_transaction_id=clean_string(transaction_id),
                        trial_start=now,
                        trial_end=trial_end,
                        subscription_start=trial_end,
                        subscription_end=sub_end
                    )
                    db.add(tenant)
                    db.flush()
                    db.add(Category(tenant_id=tenant.id, name="Featured", slug="featured", description="Featured store collection"))
                    db.commit()
                    login_user(request, user, tenant)
                    return redirect("/admin/dashboard?new_store=1")
                except Exception as e:
                    db.rollback()
                    error = f"Registration failed due to a database error. Please try again."
    plans = db.query(Plan).order_by(Plan.price_weekly.asc()).all()
    terms_page = db.query(Page).filter(Page.slug == "terms").first()
    
    ctx = template_globals(request)
    ctx.update({"plans": plans, "selected_plan": "", "error": error, "form": form, "year": datetime.now().year, "terms_page": terms_page})
    return render("platform/register.html", ctx)


@router.get("/login", response_class=HTMLResponse)
def login_get(request: Request):
    if request.session.get("user_id") and request.session.get("tenant_id"):
        return redirect("/admin/dashboard")
    ctx = template_globals(request)
    ctx.update({
        "error": "",
        "email": "",
        "registered": request.query_params.get("registered"),
        "logged_out": request.query_params.get("logged_out"),
        "year": datetime.now().year,
    })
    return render("platform/login.html", ctx)


@router.post("/login", response_class=HTMLResponse)
async def login_post(
    request: Request,
    db: Session = Depends(get_db),
    csrf_token: str = Form(""),
    email: str = Form(""),
    password: str = Form(""),
):
    error = ""
    if not verify_csrf(request, csrf_token):
        error = "Security session expired. Please refresh and try again."
    elif not email or not password:
        error = "Please enter both your email and password."
    else:
        user = db.query(User).options(joinedload(User.tenant)).filter(User.email == email.strip()).first()
        if user and verify_password(password, user.password_hash):
            login_user(request, user, user.tenant)
            if user.role == "seller" and user.tenant:
                return redirect("/admin/dashboard")
            return redirect("/")
        error = "Invalid email address or password."
    ctx = template_globals(request)
    ctx.update({"error": error, "email": email, "registered": None, "logged_out": None, "year": datetime.now().year})
    return render("platform/login.html", ctx)


@router.get("/logout")
def logout(request: Request):
    logout_user(request)
    return redirect("/login?logged_out=1")
