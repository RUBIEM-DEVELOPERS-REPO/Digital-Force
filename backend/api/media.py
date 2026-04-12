"""Digital Force — Media Library API"""
import json, uuid, logging
from pathlib import Path
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc
from database import get_db, MediaAsset
from auth import get_current_user
from config import get_settings

router = APIRouter(prefix="/api/media", tags=["media"])
logger = logging.getLogger(__name__)
settings = get_settings()
UPLOAD_DIR = Path(settings.media_upload_dir)

IMAGE_TYPES = {"png", "jpg", "jpeg", "webp", "gif"}
VIDEO_TYPES = {"mp4", "mov", "avi", "webm"}
AUDIO_TYPES = {"mp3", "wav", "m4a"}
DOC_TYPES = {"pdf", "docx", "doc"}

@router.post("/upload")
async def upload_media(
    file: UploadFile = File(...),
    tags: str = Form("[]"),
    alt_text: str = Form(""),
    db: AsyncSession = Depends(get_db),
    user: dict = Depends(get_current_user),
):
    ext = Path(file.filename).suffix.lstrip(".").lower()
    asset_type = ("image" if ext in IMAGE_TYPES else "video" if ext in VIDEO_TYPES
                  else "audio" if ext in AUDIO_TYPES else "pdf" if ext == "pdf" else "document")

    asset_id = str(uuid.uuid4())
    filename = f"{asset_id}_{file.filename}"
    dest = UPLOAD_DIR / filename
    dest.write_bytes(await file.read())

    asset = MediaAsset(
        id=asset_id, filename=filename, original_filename=file.filename,
        file_path=str(dest), public_url=f"/media/{filename}",
        file_size_bytes=dest.stat().st_size, mime_type=file.content_type or f"application/{ext}",
        asset_type=asset_type, manual_tags=tags, alt_text=alt_text,
        uploaded_by=user.get("sub"),
    )

    # Auto-tag with Vision if image
    if asset_type == "image" and settings.openai_api_key:
        try:
            from rag.pipeline import parse_image
            description = await parse_image(str(dest))
            asset.ai_description = description[:1000]
        except Exception as e:
            logger.warning(f"Auto-tagging failed: {e}")

    db.add(asset)
    await db.flush()
    return {"id": asset_id, "url": f"/media/{filename}", "type": asset_type, "filename": file.filename}


@router.get("")
async def list_media(asset_type: str = None, db: AsyncSession = Depends(get_db), user: dict = Depends(get_current_user)):
    q = select(MediaAsset).order_by(desc(MediaAsset.created_at)).limit(200)
    result = await db.execute(q)
    assets = result.scalars().all()
    items = [{
        "id": a.id, "filename": a.original_filename, "url": a.public_url,
        "type": a.asset_type, "size": a.file_size_bytes,
        "tags": json.loads(a.manual_tags or "[]"),
        "auto_tags": json.loads(a.auto_tags or "[]"),
        "ai_description": a.ai_description,
        "usage_count": a.usage_count,
        "created_at": a.created_at.isoformat(),
    } for a in assets if not asset_type or a.asset_type == asset_type]
    return items


@router.delete("/{asset_id}")
async def delete_media(asset_id: str, db: AsyncSession = Depends(get_db), user: dict = Depends(get_current_user)):
    asset = await db.get(MediaAsset, asset_id)
    if not asset:
        raise HTTPException(404, "Asset not found")
    try:
        Path(asset.file_path).unlink(missing_ok=True)
    except Exception:
        pass
    await db.delete(asset)
    return {"deleted": True}
