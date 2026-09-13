import secrets
from pathlib import Path

from fastapi import UploadFile
from PIL import Image

from app.config import BASE_DIR, settings

ALLOWED_TYPES = {"image/jpeg", "image/png", "image/webp", "image/gif"}


def process_upload(file: UploadFile, store_slug: str, subfolder: str = "products") -> dict:
    if not file or not file.filename:
        return {"success": False, "error": "No file was uploaded."}
    if file.content_type and file.content_type not in ALLOWED_TYPES:
        return {"success": False, "error": "Invalid image format. Allowed: JPG, PNG, WebP, GIF."}

    clean_slug = "".join(ch for ch in store_slug if ch.isalnum() or ch in "-_")
    clean_sub = "".join(ch for ch in subfolder if ch.isalnum() or ch in "-_")
    target_dir = BASE_DIR / "uploads" / "stores" / clean_slug / clean_sub
    target_dir.mkdir(parents=True, exist_ok=True)

    filename = secrets.token_hex(16) + ".webp"
    dest = target_dir / filename
    converted = convert_to_webp(file, dest)
    if not converted or not dest.exists():
        return {"success": False, "error": "Failed to convert image to WebP format."}

    size = dest.stat().st_size
    rel = f"uploads/stores/{clean_slug}/{clean_sub}/{filename}"
    return {
        "success": True,
        "path": rel,
        "file_name": filename,
        "filename": filename,
        "size_bytes": size,
        "size_kb": round(size / 1024, 2),
    }


def convert_to_webp(upload: UploadFile, dest: Path, max_bytes: int | None = None) -> bool:
    max_bytes = max_bytes or settings.MAX_IMAGE_BYTES
    try:
        upload.file.seek(0)
        img = Image.open(upload.file)
        if img.mode not in ("RGBA", "LA"):
            img = img.convert("RGB")
        max_dim = 1600
        if max(img.size) > max_dim:
            img.thumbnail((max_dim, max_dim), Image.Resampling.LANCZOS)
        quality = 85
        img.save(dest, "WEBP", quality=quality, method=4)
        while dest.exists() and dest.stat().st_size > max_bytes and quality > 30:
            quality -= 10
            img.save(dest, "WEBP", quality=quality, method=4)
        return dest.exists()
    except Exception:
        return False
