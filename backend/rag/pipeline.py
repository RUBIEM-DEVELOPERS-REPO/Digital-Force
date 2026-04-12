"""
Digital Force — Multimodal RAG Ingestion Pipeline
Handles: PDF, DOCX, images, video, audio, CSV, URLs, plain text.
"""

import logging
import uuid
from pathlib import Path
from typing import Optional
from config import get_settings
from rag.retriever import store, ensure_collections

logger = logging.getLogger(__name__)
settings = get_settings()


# ─── Text Chunker ────────────────────────────────────────

def chunk_text(text: str, chunk_size: int = 512, overlap: int = 64) -> list[str]:
    """Semantic-ish chunking by sentence boundaries."""
    import re
    sentences = re.split(r'(?<=[.!?])\s+', text.strip())
    chunks, current, current_len = [], [], 0
    for s in sentences:
        s_len = len(s)
        if current_len + s_len > chunk_size and current:
            chunks.append(" ".join(current))
            # Keep last sentence for overlap
            current = current[-1:] if overlap > 0 else []
            current_len = len(current[0]) if current else 0
        current.append(s)
        current_len += s_len
    if current:
        chunks.append(" ".join(current))
    return [c for c in chunks if len(c.strip()) > 20]


# ─── Parsers ──────────────────────────────────────────────

async def parse_pdf(file_path: str) -> str:
    """Extract text from PDF using PyMuPDF."""
    try:
        import fitz  # PyMuPDF
        doc = fitz.open(file_path)
        return "\n".join(page.get_text() for page in doc)
    except Exception as e:
        logger.error(f"PDF parse error: {e}")
        return ""


async def parse_docx(file_path: str) -> str:
    """Extract text from Word document."""
    try:
        from docx import Document
        doc = Document(file_path)
        return "\n".join(p.text for p in doc.paragraphs if p.text.strip())
    except Exception as e:
        logger.error(f"DOCX parse error: {e}")
        return ""


async def parse_csv(file_path: str) -> str:
    """Convert CSV rows to natural language text."""
    try:
        import pandas as pd
        df = pd.read_csv(file_path)
        # Convert to natural language rows
        rows = []
        for _, row in df.iterrows():
            row_text = ", ".join([f"{col}: {val}" for col, val in row.items() if str(val).strip()])
            rows.append(row_text)
        summary = f"Dataset with {len(df)} rows and columns: {', '.join(df.columns.tolist())}\n"
        return summary + "\n".join(rows[:200])  # Cap at 200 rows
    except Exception as e:
        logger.error(f"CSV parse error: {e}")
        return ""


async def parse_url(url: str) -> str:
    """Scrape and clean text from a URL."""
    try:
        import httpx
        from bs4 import BeautifulSoup
        async with httpx.AsyncClient(timeout=15, follow_redirects=True) as client:
            resp = await client.get(url, headers={"User-Agent": "Mozilla/5.0"})
            soup = BeautifulSoup(resp.text, "lxml")
            # Remove noise
            for tag in soup(["script", "style", "nav", "footer", "header", "aside"]):
                tag.decompose()
            return soup.get_text(separator="\n", strip=True)[:50000]
    except Exception as e:
        logger.error(f"URL parse error ({url}): {e}")
        return ""


async def parse_image(file_path: str) -> str:
    """Generate text description of an image using GPT-4o Vision."""
    if not settings.openai_api_key:
        return f"Image asset: {Path(file_path).name}"
    try:
        import base64
        from openai import AsyncOpenAI
        client = AsyncOpenAI(api_key=settings.openai_api_key)
        with open(file_path, "rb") as f:
            b64 = base64.b64encode(f.read()).decode()
        ext = Path(file_path).suffix.lstrip(".").lower()
        media_type = {"jpg": "jpeg", "jpeg": "jpeg", "png": "png", "webp": "webp"}.get(ext, "jpeg")
        resp = await client.chat.completions.create(
            model=settings.openai_reasoning_model,
            messages=[{
                "role": "user",
                "content": [
                    {"type": "image_url", "image_url": {"url": f"data:image/{media_type};base64,{b64}"}},
                    {"type": "text", "text": "Describe this image in detail for a social media context. Include: visual elements, text visible, colors, mood, and how it could be used for marketing."}
                ]
            }],
            max_tokens=500,
        )
        return resp.choices[0].message.content
    except Exception as e:
        logger.error(f"Image parse error: {e}")
        return f"Image: {Path(file_path).name}"


async def parse_audio_video(file_path: str) -> str:
    """Transcribe audio/video using OpenAI Whisper."""
    try:
        import whisper
        model = whisper.load_model("base")
        result = model.transcribe(file_path)
        return result.get("text", "")
    except Exception as e:
        logger.error(f"Audio/video transcription error: {e}")
        return ""


# ─── Main Pipeline ────────────────────────────────────────

async def ingest(
    source_type: str,
    source_path: str,
    knowledge_item_id: str,
    title: str = "",
    category: str = "other",
    tags: list[str] = None,
) -> dict:
    """
    Main ingestion pipeline. Parses → chunks → embeds → stores in Qdrant.
    Returns: {success, chunk_count, qdrant_ids}
    """
    await ensure_collections()

    # Step 1: Parse
    logger.info(f"[RAG] Ingesting {source_type}: {source_path}")
    raw_text = ""

    type_lower = source_type.lower()
    if type_lower == "pdf":
        raw_text = await parse_pdf(source_path)
    elif type_lower in ("docx", "doc"):
        raw_text = await parse_docx(source_path)
    elif type_lower == "csv":
        raw_text = await parse_csv(source_path)
    elif type_lower == "url":
        raw_text = await parse_url(source_path)
    elif type_lower in ("image", "png", "jpg", "jpeg", "webp"):
        raw_text = await parse_image(source_path)
    elif type_lower in ("video", "audio", "mp4", "mov", "mp3", "wav"):
        raw_text = await parse_audio_video(source_path)
    elif type_lower == "text":
        try:
            raw_text = Path(source_path).read_text(encoding="utf-8")
        except Exception:
            raw_text = source_path  # Treat as raw text if not a path
    else:
        return {"success": False, "error": f"Unsupported source type: {source_type}"}

    if not raw_text or len(raw_text.strip()) < 10:
        return {"success": False, "error": "No extractable content found"}

    # Step 2: Chunk
    chunks = chunk_text(raw_text)
    logger.info(f"[RAG] {len(chunks)} chunks from {source_type}")

    # Determine collection
    collection = "brand" if category == "brand_voice" else "knowledge"

    # Step 3: Embed + Store
    qdrant_ids = []
    for i, chunk in enumerate(chunks):
        metadata = {
            "knowledge_item_id": knowledge_item_id,
            "title": title,
            "source_type": source_type,
            "category": category,
            "tags": tags or [],
            "chunk_index": i,
            "total_chunks": len(chunks),
        }
        try:
            pid = await store(chunk, metadata, collection=collection)
            qdrant_ids.append(pid)
        except Exception as e:
            logger.error(f"[RAG] Store failed for chunk {i}: {e}")

    return {
        "success": True,
        "chunk_count": len(chunks),
        "qdrant_ids": qdrant_ids,
        "raw_text_preview": raw_text[:500],
    }
