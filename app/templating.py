from fastapi.templating import Jinja2Templates

from app.config import BASE_DIR
from app.security import e, money, money0

templates = Jinja2Templates(directory=str(BASE_DIR / "templates"))
templates.env.filters["e"] = e
templates.env.filters["money"] = money
templates.env.filters["money0"] = money0
templates.env.globals["e"] = e


def render(name: str, context: dict, status_code: int = 200):
    return templates.TemplateResponse(context["request"], name, context, status_code=status_code)
