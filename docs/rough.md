Absolutely. We should design **three environments**, not two:

```text
LOCAL → TEST → PROD
```

The important principle remains: **same codebase, environment-specific `.env` configuration**.

### Environment model

| Environment | `APP_ENV` | URL                          | Database          |
| ----------- | --------- | ---------------------------- | ----------------- |
| Local       | `local`   | `http://127.0.0.1:8000`      | Local PostgreSQL  |
| Test        | `test`    | `https://test.metohub.cloud` | Docker PostgreSQL |
| Production  | `prod`    | `https://metohub.cloud`      | Docker PostgreSQL |

So your workflow becomes:

```text
                 SAME CODE
                    │
       ┌────────────┼────────────┐
       ▼            ▼            ▼
     LOCAL         TEST         PROD
       │            │            │
   local .env    test .env    prod .env
       │            │            │
   PostgreSQL   PostgreSQL   PostgreSQL
```

## `config.py`

I would keep the code like this:

```python
from pathlib import Path
from urllib.parse import quote_plus

from pydantic_settings import BaseSettings, SettingsConfigDict


BASE_DIR = Path(__file__).resolve().parent.parent


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=str(BASE_DIR / ".env"),
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=True,
    )

    # Application
    APP_NAME: str = "Metohub"
    APP_ENV: str = "local"
    APP_DEBUG: bool = False
    APP_URL: str = "http://127.0.0.1:8000"

    # Security
    SECRET_KEY: str

    # Database
    DB_HOST: str = "localhost"
    DB_PORT: int = 5432
    DB_NAME: str = "metohub"
    DB_USER: str = "metohub"
    DB_PASSWORD: str

    # Mail
    MAIL_HOST: str = "smtp.hostinger.com"
    MAIL_PORT: int = 465
    MAIL_USERNAME: str = ""
    MAIL_PASSWORD: str = ""
    MAIL_ENCRYPTION: str = "ssl"
    MAIL_FROM_ADDRESS: str = ""
    MAIL_FROM_NAME: str = "Metohub"

    # Uploads
    MAX_IMAGE_BYTES: int = 400 * 1024

    @property
    def database_url(self) -> str:
        user = quote_plus(self.DB_USER)
        password = quote_plus(self.DB_PASSWORD)

        return (
            f"postgresql+psycopg://"
            f"{user}:{password}@"
            f"{self.DB_HOST}:{self.DB_PORT}/"
            f"{self.DB_NAME}"
        )


settings = Settings()
```

### Notice the defaults

The defaults are appropriate for **local development**:

```python
APP_ENV = "local"
APP_DEBUG = False
APP_URL = "http://127.0.0.1:8000"
DB_HOST = "localhost"
DB_PORT = 5432
```

But credentials are required:

```python
SECRET_KEY: str
DB_PASSWORD: str
```

That means we never accidentally deploy with:

```text
secret = "change-me"
password = ""
```

---

# `.env` files

### Local

On your Mac:

```env
APP_NAME=Metohub
APP_ENV=local
APP_DEBUG=true
APP_URL=http://127.0.0.1:8000

SECRET_KEY=<LOCAL_SECRET>

DB_HOST=localhost
DB_PORT=5432
DB_NAME=metohub_local
DB_USER=metohub_local
DB_PASSWORD=<LOCAL_DB_PASSWORD>

MAIL_HOST=smtp.hostinger.com
MAIL_PORT=465
MAIL_USERNAME=
MAIL_PASSWORD=
MAIL_ENCRYPTION=ssl
MAIL_FROM_ADDRESS=
MAIL_FROM_NAME=Metohub

MAX_IMAGE_BYTES=409600
```

Your local PostgreSQL can be installed directly on your Mac or run through Docker.

---

### TEST VPS

```env
APP_NAME=Metohub
APP_ENV=test
APP_DEBUG=true
APP_URL=https://test.metohub.cloud

SECRET_KEY=<TEST_SECRET>

DB_HOST=postgres
DB_PORT=5432
DB_NAME=metohub_test
DB_USER=metohub_test
DB_PASSWORD=<TEST_DB_PASSWORD>

MAIL_HOST=smtp.hostinger.com
MAIL_PORT=465
MAIL_USERNAME=
MAIL_PASSWORD=
MAIL_ENCRYPTION=ssl
MAIL_FROM_ADDRESS=
MAIL_FROM_NAME=Metohub

MAX_IMAGE_BYTES=409600
```

---

### PROD VPS

```env
APP_NAME=Metohub
APP_ENV=prod
APP_DEBUG=false
APP_URL=https://metohub.cloud

SECRET_KEY=<PROD_SECRET>

DB_HOST=postgres
DB_PORT=5432
DB_NAME=metohub_prod
DB_USER=metohub_prod
DB_PASSWORD=<PROD_DB_PASSWORD>

MAIL_HOST=smtp.hostinger.com
MAIL_PORT=465
MAIL_USERNAME=
MAIL_PASSWORD=
MAIL_ENCRYPTION=ssl
MAIL_FROM_ADDRESS=
MAIL_FROM_NAME=Metohub

MAX_IMAGE_BYTES=409600
```

## One thing I'd change from my previous suggestion

I **wouldn't make `APP_DEBUG` automatically depend on `APP_ENV`**.

For example, avoid:

```python
APP_DEBUG = APP_ENV == "test"
```

Instead, explicitly configure it:

```env
APP_DEBUG=true
```

or:

```env
APP_DEBUG=false
```

That gives you control and prevents unexpected behavior.

---

# `run.py`

Keep `run.py` environment-neutral too:

```python
import uvicorn


if __name__ == "__main__":
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8000,
    )
```

Then Docker/local commands decide whether we use reload.

For local development:

```bash
uvicorn app.main:app --reload
```

For TEST/PROD:

```bash
uvicorn app.main:app --host 0.0.0.0 --port 8000
```

This is cleaner than putting deployment behavior inside the application.

---

# Git structure

I recommend:

```text
main
 │
 └── production

test
 │
 └── test environment
```

Local development doesn't need its own branch. You develop locally, commit to `test`, deploy/test, then merge into `main`.

```text
LOCAL
  │
  │ commit
  ▼
 test branch
  │
  ▼
TEST VPS
test.metohub.cloud
  │
  │ verified
  ▼
 main branch
  │
  ▼
PROD VPS
metohub.cloud
```

Most importantly:

> **There should be no `if test`, `if prod`, or `if local` database configuration scattered throughout the application.**

The application asks `settings` for configuration, and `.env` supplies the environment-specific values.

That's the architecture I'd lock in before we continue with PostgreSQL/Docker.



Yes — **I recommend making the code changes in Antigravity locally**, not directly on the VPS.

That gives you a much cleaner workflow:

```text
Antigravity (your Mac)
        │
        │ edit + test
        ▼
Git repository
        │
        ├── test branch
        │       ↓
        │   VPS TEST
        │
        └── main branch
                ↓
             VPS PROD
```

### What I'd do now

In Antigravity, open your local clone of:

```text
PJ57-metohub-py
```

Make the following changes **locally**:

1. `app/config.py`

   * PostgreSQL instead of MySQL
   * configuration loaded from `.env`
   * no secrets hardcoded
   * sensible local defaults

2. `requirements.txt`

   * remove `pymysql`
   * add `psycopg[binary]`

3. `run.py`

   * use `0.0.0.0`
   * don't hardcode reload behavior

4. `.env.example`

   * update it for PostgreSQL
   * document all required variables
   * **no actual passwords/secrets**

5. `.gitignore`

   * ensure `.env` is ignored

6. `schema.sql`

   * convert the MySQL schema to PostgreSQL

### Don't create the real `.env` in Git

Locally you'll have:

```text
PJ57-metohub-py/
├── .env              ← your local secrets, NOT committed
├── .env.example      ← committed
├── app/
├── requirements.txt
├── schema.sql
└── run.py
```

On the VPS we'll separately create:

```text
/srv/apps/metohub/test/metohub-code/.env
/srv/apps/metohub/prod/metohub-code/.env
```

Those will **never come from GitHub**.

### One important recommendation

Don't have Antigravity blindly rewrite the entire project.

Make the changes **incrementally**, and after each logical change we can verify the result. In particular, `schema.sql` needs careful PostgreSQL conversion because it contains MySQL-specific `ENUM`, `AUTO_INCREMENT`, and `ON DUPLICATE KEY UPDATE`.

If you want, **use Antigravity to make the changes, then paste the modified `config.py`, `requirements.txt`, `run.py`, and `schema.sql` here**. I'll review them before we deploy anything to the VPS.
