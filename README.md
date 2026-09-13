# Metohub Python (FastAPI + MySQL)

Multi-tenant e-commerce SaaS converted from the PHP app in `4-glov`. Merchants register a store, sell or rent products, and customers check out per tenant with isolated carts and orders.

## Features

- Tenant-isolated catalogs, carts, orders, and uploads
- Base / Essential / Pro plans with product limits
- Retail + rental pricing (daily / weekend)
- WebP image conversion under 400KB
- UPI screenshot checkout, bank transfer, frozen COD, coming-soon cards
- Merchant admin: products, categories, orders, branding theme, payments

## Setup (XAMPP MariaDB)

1. Start MariaDB in XAMPP.
2. Create the database and import schema:

```bash
/Applications/XAMPP/xamppfiles/bin/mysql -u root < schema.sql
```

3. Install Python deps and configure env:

```bash
cd /Applications/XAMPP/xamppfiles/htdocs/github/1-metora/4-saas/5-glov-py
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
```

4. Seed demo merchants (password `password123`):

```bash
python seed.py
```

5. Run the app:

```bash
python run.py
```

- Platform: http://127.0.0.1:8000
- Merchant admin: http://127.0.0.1:8000/admin
- API docs: http://127.0.0.1:8000/api/docs

Demo logins: `meera@aurajewels.com`, `alex@casecraft.com`, `sophia@scentaura.com` / `password123`.
