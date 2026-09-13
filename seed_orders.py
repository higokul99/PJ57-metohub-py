import random
import secrets
from datetime import date, datetime, timedelta
from decimal import Decimal

from app.database import SessionLocal
from app.models import Order, OrderItem, Product, Tenant, User

NUM_ORDERS = 80
TARGET_EMAIL = "montu@metora.in"

FIRST_NAMES = [
    "Aarav", "Vivaan", "Aditya", "Vihaan", "Arjun", "Sai", "Reyansh", "Krishna",
    "Ishaan", "Shaurya", "Ananya", "Diya", "Aadhya", "Saanvi", "Myra", "Pari",
    "Anika", "Navya", "Kavya", "Tara", "Rohan", "Siddharth", "Karan", "Arnav",
    "Prisha", "Riya", "Shreya", "Ira", "Neha", "Pooja", "Rahul", "Priya",
    "Amit", "Sneha", "Rakesh", "Meera", "Nikhil", "Shruti", "Varun", "Tanvi",
]

LAST_NAMES = [
    "Sharma", "Verma", "Patel", "Gupta", "Singh", "Kumar", "Reddy", "Iyer",
    "Nair", "Das", "Roy", "Bose", "Mehta", "Chopra", "Malhotra", "Kapoor",
    "Khanna", "Arora", "Bhatia", "Saxena", "Tripathi", "Tiwari", "Joshi",
    "Desai", "Rao", "Menon", "Pillai", "Chauhan", "Rathore", "Yadav",
]

CITIES = [
    "Mumbai", "Delhi", "Bangalore", "Hyderabad", "Ahmedabad", "Chennai",
    "Kolkata", "Pune", "Jaipur", "Surat", "Lucknow", "Kanpur", "Nagpur",
    "Indore", "Thane", "Bhopal", "Visakhapatnam", "Pimpri-Chinchwad",
    "Patna", "Vadodara", "Ghaziabad", "Ludhiana", "Agra", "Nashik",
    "Ranchi", "Faridabad", "Meerut", "Rajkot", "Kalyan-Dombivli", "Vasai-Virar",
]

STATUSES = ["pending", "processing", "completed", "cancelled"]
PAYMENT_METHODS = ["upi", "bank_transfer", "card"]
PAYMENT_STATUSES = ["pending", "paid", "refunded"]

ADDRESS_LINES = [
    "123, Green Park, Main Road",
    "45, Sector 17, Near Railway Station",
    "789, Maple Apartments, 2nd Floor",
    "12, Sunrise Colony, Off Highway 4",
    "567, Lotus Enclave, Block B",
    "34, Hill View Gardens, Opp. Mall",
    "901, Skyline Towers, MG Road",
    "67, Silver Oak Estate, Phase 2",
    "234, Juhu Scheme, Lane 5",
    "89, Diamond Residency, Plot 12",
    "156, Rosewood Society, Near Park",
    "432, Lake View Road, Behind Church",
    "78, Orange Heights, Flat 404",
    "221, Golden Avenue, Street 11",
    "654, Emerald Villas, Gate 3",
]


def random_phone():
    return "+91 " + str(random.randint(70000, 99999)) + str(random.randint(10000, 99999))


def random_pincode():
    return str(random.randint(110001, 690000))


def pick_weighted(items, weights):
    return random.choices(items, weights=weights, k=1)[0]


def run():
    db = SessionLocal()
    try:
        user = db.query(User).filter(User.email == TARGET_EMAIL).first()
        if not user:
            raise SystemExit(f"User {TARGET_EMAIL} not found")
        tenant = db.query(Tenant).filter(Tenant.user_id == user.id).first()
        if not tenant:
            raise SystemExit(f"No tenant found for user {TARGET_EMAIL}")

        products = db.query(Product).filter(
            Product.tenant_id == tenant.id,
            Product.status == "active",
        ).all()
        if not products:
            raise SystemExit("No products found in store")

        slug = tenant.slug or "store"
        slug_prefix = slug[:4].upper()

        # Choose weights: 40% completed, 30% processing, 20% pending, 10% cancelled
        status_weights = [20, 30, 40, 10]  # pending, processing, completed, cancelled
        payment_method_weights = [55, 15, 30]  # UPI heavy
        item_count_weights = [35, 40, 18, 5, 2]  # 1, 2, 3, 4, 5 items per order

        now = datetime.now()
        created_count = 0
        total_revenue = Decimal("0")

        for i in range(NUM_ORDERS):
            # Spread order dates over the past ~120 days with some recency bias
            days_back = int(random.triangular(0, 120, 30))
            order_dt = now - timedelta(
                days=days_back,
                hours=random.randint(0, 23),
                minutes=random.randint(0, 59),
            )

            # Pick customer
            first = random.choice(FIRST_NAMES)
            last = random.choice(LAST_NAMES)
            customer_name = f"{first} {last}"
            customer_email = f"{first.lower()}.{last.lower()}{random.randint(1, 999)}@example.com"
            customer_phone = random_phone()
            city = random.choice(CITIES)
            postal_code = random_pincode()
            shipping_address = f"{random.choice(ADDRESS_LINES)}, {city}"

            # Payment & status
            payment_method = pick_weighted(PAYMENT_METHODS, payment_method_weights)
            status = pick_weighted(STATUSES, status_weights)

            # If completed or processing, payment likely settled; adjust payment_status
            if status in ("completed", "processing"):
                payment_status = "paid"
            elif status == "cancelled":
                payment_status = random.choice(["pending", "paid", "refunded"])
            else:
                payment_status = pick_weighted(PAYMENT_STATUSES, [30, 65, 5])

            # Build items (1 to 5 products)
            num_items = pick_weighted([1, 2, 3, 4, 5], item_count_weights)
            chosen_products = random.sample(products, min(num_items, len(products)))
            items_list = []
            order_total = Decimal("0")

            for product in chosen_products:
                qty = random.choices([1, 2, 3], weights=[70, 22, 8])[0]
                unit_price = Decimal(product.price)
                line_total = unit_price * qty
                order_total += line_total

                items_list.append({
                    "product_id": product.id,
                    "product_name": product.name,
                    "quantity": qty,
                    "unit_price": unit_price,
                    "line_total": line_total,
                    "is_rental": bool(product.is_rental),
                    "rental_type": None,
                    "rental_start_date": None,
                    "rental_days": None,
                })

            # Generate unique order number
            date_str = order_dt.strftime("%Y%m%d")
            order_number = f"GLV-{slug_prefix}-{date_str}-{secrets.token_hex(2).upper()}"

            order = Order(
                tenant_id=tenant.id,
                order_number=order_number,
                customer_name=customer_name,
                customer_email=customer_email,
                customer_phone=customer_phone,
                shipping_address=shipping_address,
                city=city,
                postal_code=postal_code,
                total_amount=order_total,
                payment_method=payment_method,
                payment_status=payment_status,
                payment_proof=None,
                transaction_ref=(
                    f"TXN{order_dt.strftime('%d%m%Y')}{random.randint(100000, 999999)}"
                    if payment_status == "paid" else None
                ),
                is_rental_order=any(it["is_rental"] for it in items_list),
                rental_duration_days=1,
                rental_start_date=None,
                status=status,
                notes=random.choice([
                    None, None, None, None,
                    "Please deliver before 6 PM",
                    "Gift wrap required",
                    "Call before delivery",
                    "Leave at security desk",
                ]),
            )
            # Override created_at/updated_at via attribute (we set directly before flush)
            order.created_at = order_dt
            order.updated_at = order_dt
            db.add(order)
            db.flush()

            for it in items_list:
                db.add(OrderItem(
                    order_id=order.id,
                    tenant_id=tenant.id,
                    product_id=it["product_id"],
                    product_name=it["product_name"],
                    quantity=it["quantity"],
                    unit_price=it["unit_price"],
                    is_rental=it["is_rental"],
                    rental_type=it["rental_type"],
                    rental_start_date=it["rental_start_date"],
                    rental_days=it["rental_days"],
                    line_total=it["line_total"],
                    total_price=it["line_total"],
                ))

            total_revenue += order_total
            created_count += 1
            if (i + 1) % 20 == 0:
                db.commit()
                print(f"  → committed batch {i + 1}/{NUM_ORDERS}")

        db.commit()
        print(f"✅ Successfully created {created_count} orders for '{tenant.name}'")
        print(f"   Combined order total: ₹{total_revenue:,.2f}")
        print(f"   Avg order value:      ₹{total_revenue / created_count:,.2f}")

        # Quick summary by status
        rows = db.query(Order.status, db.func.count(Order.id), db.func.sum(Order.total_amount)) \
                 .filter(Order.tenant_id == tenant.id) \
                 .group_by(Order.status).all()
        print("\n📊 Order summary by status:")
        for s, c, t in rows:
            print(f"   {s:12s}  {c:>3d} orders  ₹{(t or Decimal('0')):>14,.2f}")
    finally:
        db.close()


if __name__ == "__main__":
    run()
