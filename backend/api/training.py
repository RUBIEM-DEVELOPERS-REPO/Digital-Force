"""
Digital Force — Training/Knowledge API
Multimodal RAG ingestion endpoints.
"""

import json
import uuid
import logging
from pathlib import Path
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form, BackgroundTasks
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc
from pydantic import BaseModel
from typing import Optional

from database import get_db, KnowledgeItem
from auth import get_current_user
from config import get_settings

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/training", tags=["training"])
settings = get_settings()

UPLOAD_DIR = Path(settings.media_upload_dir)
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)

ALLOWED_EXTENSIONS = {
    "pdf", "docx", "doc", "txt", "md",
    "png", "jpg", "jpeg", "webp", "gif",
    "mp4", "mov", "avi", "webm",
    "mp3", "wav", "m4a",
    "csv", "xlsx", "xls",
}


async def _process_knowledge_item(item_id: str, source_type: str, source_path: str,
                                   title: str, category: str, tags: list[str]):
    """Background task: ingest document into RAG."""
    try:
        from rag.pipeline import ingest
        from database import async_session, KnowledgeItem as KI
        from datetime import datetime

        logger.info(f"[Training] Processing item {item_id}")

        result = await ingest(
            source_type=source_type,
            source_path=source_path,
            knowledge_item_id=item_id,
            title=title,
            category=category,
            tags=tags,
        )

        async with async_session() as db:
            item = await db.get(KI, item_id)
            if item:
                if result.get("success"):
                    item.processing_status = "indexed"
                    item.qdrant_ids = json.dumps(result.get("qdrant_ids", []))
                    item.chunk_count = result.get("chunk_count", 0)
                    item.raw_content = result.get("raw_text_preview", "")[:2000]
                    item.processed_at = datetime.utcnow()
                else:
                    item.processing_status = "failed"
                    item.error_message = result.get("error", "Unknown error")
                await db.commit()
                logger.info(f"[Training] Indexed {item.chunk_count} chunks for {item_id}")

    except Exception as e:
        logger.error(f"[Training] Processing failed for {item_id}: {e}")
        from database import async_session, KnowledgeItem as KI
        async with async_session() as db:
            item = await db.get(KI, item_id)
            if item:
                item.processing_status = "failed"
                item.error_message = str(e)
                await db.commit()


@router.post("/upload")
async def upload_knowledge(
    background_tasks: BackgroundTasks,
    file: Optional[UploadFile] = File(None),
    url: Optional[str] = Form(None),
    raw_text: Optional[str] = Form(None),
    title: str = Form(""),
    category: str = Form("other"),
    tags: str = Form("[]"),
    db: AsyncSession = Depends(get_db),
    user: dict = Depends(get_current_user),
):
    """Upload any format for RAG ingestion: file, URL, or raw text."""
    if not file and not url and not raw_text:
        raise HTTPException(400, "Provide a file, URL, or raw text")

    item_id = str(uuid.uuid4())
    tags_list = json.loads(tags) if tags else []
    source_path = ""
    source_type = "text"

    if file:
        ext = Path(file.filename).suffix.lstrip(".").lower()
        if ext not in ALLOWED_EXTENSIONS:
            raise HTTPException(400, f"File type '.{ext}' not supported")
        source_type = ext
        dest = UPLOAD_DIR / f"{item_id}_{file.filename}"
        dest.write_bytes(await file.read())
        source_path = str(dest)

    elif url:
        source_type = "url"
        source_path = url

    elif raw_text:
        source_type = "text"
        # Save as temp file
        dest = UPLOAD_DIR / f"{item_id}_text.txt"
        dest.write_text(raw_text, encoding="utf-8")
        source_path = str(dest)

    item = KnowledgeItem(
        id=item_id,
        title=title or (file.filename if file else url or "Text Input"),
        source_type=source_type,
        source_path=source_path,
        source_url=url,
        category=category,
        tags=json.dumps(tags_list),
        processing_status="processing",
        uploaded_by=user.get("sub"),
    )
    db.add(item)
    await db.flush()

    background_tasks.add_task(
        _process_knowledge_item, item_id, source_type, source_path,
        item.title, category, tags_list
    )

    return {
        "id": item_id,
        "status": "processing",
        "message": "Document is being indexed into the knowledge base. This may take a moment.",
    }


@router.post("/url")
async def ingest_url(
    background_tasks: BackgroundTasks,
    body: dict,
    db: AsyncSession = Depends(get_db),
    user: dict = Depends(get_current_user),
):
    """Quick URL ingestion endpoint."""
    url = body.get("url")
    if not url:
        raise HTTPException(400, "URL required")
    item_id = str(uuid.uuid4())
    item = KnowledgeItem(
        id=item_id, title=url, source_type="url",
        source_path=url, source_url=url,
        category=body.get("category", "other"),
        tags=json.dumps(body.get("tags", [])),
        processing_status="processing",
        uploaded_by=user.get("sub"),
    )
    db.add(item)
    await db.flush()
    background_tasks.add_task(
        _process_knowledge_item, item_id, "url", url,
        url, body.get("category", "other"), body.get("tags", [])
    )
    return {"id": item_id, "status": "processing"}


@router.get("")
async def list_knowledge(db: AsyncSession = Depends(get_db), user: dict = Depends(get_current_user)):
    result = await db.execute(select(KnowledgeItem).order_by(desc(KnowledgeItem.created_at)).limit(100))
    items = result.scalars().all()
    return [{
        "id": i.id, "title": i.title, "source_type": i.source_type,
        "category": i.category, "processing_status": i.processing_status,
        "chunk_count": i.chunk_count, "tags": json.loads(i.tags or "[]"),
        "created_at": i.created_at.isoformat(),
    } for i in items]


@router.delete("/{item_id}")
async def delete_knowledge(
    item_id: str, db: AsyncSession = Depends(get_db), user: dict = Depends(get_current_user)
):
    item = await db.get(KnowledgeItem, item_id)
    if not item:
        raise HTTPException(404, "Item not found")
    # TODO: Remove from Qdrant
    await db.delete(item)
    return {"deleted": True}
