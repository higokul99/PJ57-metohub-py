"""Create demo merchants used by the login page."""
from app.database import SessionLocal
from app.models import Category, Plan, Tenant, User
from app.security import hash_password

DEMOS = [
    {
        "name": "Meera Shah",
        "email": "meera@aurajewels.com",
        "store": "Aura Jewels",
        "slug": "aura-jewels",
        "business_type": "Rental Jewellery",
        "tagline": "Designer Bridal Jewellery on Rent",
        "theme": "#d97706",
        "plan_slug": "pro",
        "upi": "aura@upi",
    },
    {
        "name": "Alex Chen",
        "email": "alex@casecraft.com",
        "store": "CaseCraft",
        "slug": "casecraft",
        "business_type": "Mobile Cases",
        "tagline": "Protective cases, crafted well",
        "theme": "#2563eb",
        "plan_slug": "essential",
        "upi": "casecraft@upi",
    },
    {
        "name": "Sophia Rao",
        "email": "sophia@scentaura.com",
        "store": "ScentAura",
        "slug": "scentaura",
        "business_type": "Perfumes & Fragrances",
        "tagline": "Luxury scents for every mood",
        "theme": "#7c3aed",
        "plan_slug": "base",
        "upi": "scentaura@upi",
    },
]


def run():
    db = SessionLocal()
    try:
        for demo in DEMOS:
            if db.query(User).filter(User.email == demo["email"]).first():
                print(f"skip {demo['email']}")
                continue
            plan = db.query(Plan).filter(Plan.slug == demo["plan_slug"]).first()
            if not plan:
                raise SystemExit("Plans are missing. Import schema.sql first.")
            user = User(
                name=demo["name"],
                email=demo["email"],
                password_hash=hash_password("password123"),
                role="seller",
                status="active",
            )
            db.add(user)
            db.flush()
            tenant = Tenant(
                user_id=user.id,
                plan_id=plan.id,
                name=demo["store"],
                slug=demo["slug"],
                business_type=demo["business_type"],
                tagline=demo["tagline"],
                theme_color=demo["theme"],
                contact_email=demo["email"],
                status="active",
                enable_upi=True,
                upi_id=demo["upi"],
            )
            db.add(tenant)
            db.flush()
            db.add(Category(tenant_id=tenant.id, name="Featured", slug="featured"))
            print(f"created {demo['email']}")
        db.commit()
    finally:
        db.close()


if __name__ == "__main__":
    run()
