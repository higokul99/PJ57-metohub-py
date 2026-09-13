import json

DEFAULT_THEME = {
    "bg_color": "#f8fafc",
    "card_bg": "#ffffff",
    "card_border": "#e2e8f0",
    "header_bg": "rgba(255, 255, 255, 0.95)",
    "header_text": "#0f172a",
    "text_color": "#0f172a",
    "text_muted": "#64748b",
    "primary_color": "#0f172a",
    "primary_hover": "#334155",
    "primary_text": "#ffffff",
    "accent_color": "#2563eb",
    "border_color": "#e2e8f0",
    "footer_bg": "#ffffff",
    "footer_text": "#64748b",
    "input_bg": "#ffffff",
    "input_border": "#cbd5e1",
}

THEME_PRESETS = {
    "neutral_white": DEFAULT_THEME.copy(),
    "pure_monochrome": {
        "bg_color": "#ffffff",
        "card_bg": "#ffffff",
        "card_border": "#e5e7eb",
        "header_bg": "#ffffff",
        "header_text": "#000000",
        "text_color": "#000000",
        "text_muted": "#4b5563",
        "primary_color": "#000000",
        "primary_hover": "#262626",
        "primary_text": "#ffffff",
        "accent_color": "#111827",
        "border_color": "#e5e7eb",
        "footer_bg": "#ffffff",
        "footer_text": "#6b7280",
        "input_bg": "#ffffff",
        "input_border": "#d1d5db",
    },
    "warm_ivory": {
        "bg_color": "#fafaf9",
        "card_bg": "#ffffff",
        "card_border": "#e7e5e4",
        "header_bg": "#fafaf9",
        "header_text": "#1c1917",
        "text_color": "#1c1917",
        "text_muted": "#78716c",
        "primary_color": "#1c1917",
        "primary_hover": "#44403c",
        "primary_text": "#ffffff",
        "accent_color": "#b45309",
        "border_color": "#e7e5e4",
        "footer_bg": "#fafaf9",
        "footer_text": "#78716c",
        "input_bg": "#ffffff",
        "input_border": "#d6d3d1",
    },
    "modern_platinum": {
        "bg_color": "#f1f5f9",
        "card_bg": "#ffffff",
        "card_border": "#cbd5e1",
        "header_bg": "#ffffff",
        "header_text": "#0f172a",
        "text_color": "#0f172a",
        "text_muted": "#64748b",
        "primary_color": "#2563eb",
        "primary_hover": "#1d4ed8",
        "primary_text": "#ffffff",
        "accent_color": "#3b82f6",
        "border_color": "#cbd5e1",
        "footer_bg": "#ffffff",
        "footer_text": "#64748b",
        "input_bg": "#ffffff",
        "input_border": "#cbd5e1",
    },
    "midnight_slate": {
        "bg_color": "#0b0f19",
        "card_bg": "#111827",
        "card_border": "#1f2937",
        "header_bg": "#111827",
        "header_text": "#f9fafb",
        "text_color": "#f9fafb",
        "text_muted": "#9ca3af",
        "primary_color": "#6366f1",
        "primary_hover": "#4f46e5",
        "primary_text": "#ffffff",
        "accent_color": "#818cf8",
        "border_color": "#1f2937",
        "footer_bg": "#0b0f19",
        "footer_text": "#9ca3af",
        "input_bg": "#1f2937",
        "input_border": "#374151",
    },
}


def get_store_theme(tenant) -> dict:
    theme = DEFAULT_THEME.copy()
    if tenant is None:
        return theme
    raw = getattr(tenant, "theme_settings", None)
    saved = {}
    if raw:
        try:
            decoded = json.loads(raw)
            if isinstance(decoded, dict):
                saved = decoded
        except Exception:
            saved = {}
    if not saved and getattr(tenant, "theme_color", None):
        saved["primary_color"] = tenant.theme_color
    theme.update({k: v for k, v in saved.items() if v})
    return theme


def render_store_theme_css(tenant) -> str:
    t = get_store_theme(tenant)

    def c(key: str) -> str:
        return str(t.get(key, DEFAULT_THEME[key])).replace(";", "")

    return f"""
    :root {{
        --store-bg: {c("bg_color")};
        --store-card-bg: {c("card_bg")};
        --store-card-border: {c("card_border")};
        --store-header-bg: {c("header_bg")};
        --store-header-text: {c("header_text")};
        --store-text: {c("text_color")};
        --store-muted: {c("text_muted")};
        --store-primary: {c("primary_color")};
        --store-primary-hover: {c("primary_hover")};
        --store-primary-text: {c("primary_text")};
        --store-accent: {c("accent_color")};
        --store-border: {c("border_color")};
        --store-footer-bg: {c("footer_bg")};
        --store-footer-text: {c("footer_text")};
        --store-input-bg: {c("input_bg")};
        --store-input-border: {c("input_border")};
    }}
    body.store-body {{
        background-color: var(--store-bg) !important;
        color: var(--store-text) !important;
    }}
    .store-header {{
        background: var(--store-header-bg) !important;
        border-bottom-color: var(--store-card-border) !important;
    }}
    .store-brand .store-name, .store-nav-link {{
        color: var(--store-header-text) !important;
    }}
    .product-card, .checkout-card, .checkout-summary-card, .info-receipt-card, .order-receipt-box, .order-meta-pill-bar, .rental-configurator-card, .gallery-main-wrap {{
        background: var(--store-card-bg) !important;
        border-color: var(--store-card-border) !important;
        color: var(--store-text) !important;
    }}
    .store-footer {{
        background: var(--store-footer-bg) !important;
        color: var(--store-footer-text) !important;
        border-top: 1px solid var(--store-card-border) !important;
    }}
    """
