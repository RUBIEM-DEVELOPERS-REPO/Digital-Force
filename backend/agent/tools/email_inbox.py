"""
Digital Force — Agent Email Inbox Poller

Connects to the inbox specified in .env via IMAP.
Polls every 60 seconds for UNSEEN replies to agent emails.
Matches the [Ref: TOKEN] in the subject, parses 'approve' or 'skip',
and marks the DB record. Also pushes a chat message so the standard
agency loop (daemon/agent) picks up the approval.
"""

import asyncio
import imaplib
import email
import logging
import re
from datetime import datetime
from email.header import decode_header

from config import get_settings
from database import async_session, PendingEmailApproval, ChatMessage

logger = logging.getLogger(__name__)
settings = get_settings()

POLL_INTERVAL_SEC = 120


def _get_imap_host() -> str:
    """Derive IMAP host from SMTP host (e.g. smtp.gmail.com -> imap.gmail.com)"""
    if "gmail.com" in settings.smtp_host:
        return "imap.gmail.com"
    return settings.smtp_host.replace("smtp", "imap")


def _decode_str(s: str) -> str:
    if not s:
        return ""
    decoded, charset = decode_header(s)[0]
    if isinstance(decoded, bytes):
        try:
            return decoded.decode(charset or 'utf-8')
        except Exception:
            return decoded.decode('utf-8', errors='ignore')
    return str(decoded)


def _extract_text_body(msg) -> str:
    if msg.is_multipart():
        for part in msg.walk():
            ctype = part.get_content_type()
            cdispo = str(part.get('Content-Disposition'))
            if ctype == 'text/plain' and 'attachment' not in cdispo:
                try:
                    return part.get_payload(decode=True).decode()
                except Exception:
                    pass
    else:
        try:
            return msg.get_payload(decode=True).decode()
        except Exception:
            pass
    return ""


async def poll_email_inbox():
    """Background task to poll the inbox via IMAP."""
    if not settings.smtp_username or not settings.smtp_password:
        logger.warning("[InboxPoller] Email not configured — poller disabled.")
        return

    host = _get_imap_host()
    logger.info(f"[InboxPoller] Started polling {host} for replies to {settings.smtp_username}")

    while True:
        try:
            await asyncio.to_thread(_check_inbox, host)
        except Exception as e:
            logger.error(f"[InboxPoller] Error during poll: {e}")
        
        await asyncio.sleep(POLL_INTERVAL_SEC)


def _check_inbox(host: str):
    """Blocking IMAP check, runs in a thread."""
    try:
        mail = imaplib.IMAP4_SSL(host)
        mail.login(settings.smtp_username, settings.smtp_password)
        mail.select('inbox')

        _, search_data = mail.search(None, 'UNSEEN')
        for num in search_data[0].split():
            _, data = mail.fetch(num, '(RFC822)')
            msg = email.message_from_bytes(data[0][1])
            subject = _decode_str(msg.get("Subject", ""))
            
            # Check if this is a reply to one of our approval emails
            token_match = re.search(r'Ref:\s*([A-Z0-9]{8})', subject)
            if not token_match:
                continue
                
            token = token_match.group(1)
            body = _extract_text_body(msg)
            
            # Parse approval intent from body (mostly first non-empty line)
            lines = [l.strip().lower() for l in body.split('\n') if l.strip()]
            body_head = lines[0] if lines else ""
            
            resolution = None
            if any(w in body_head for w in ["approve", "go ahead", "yes", "do it"]):
                resolution = "approved"
            elif any(w in body_head for w in ["skip", "drop", "no"]):
                resolution = "skipped"
                
            if resolution:
                logger.info(f"[InboxPoller] Received '{resolution}' for token {token}")
                # We need an event loop to run async DB ops
                try:
                    loop = asyncio.get_running_loop()
                except RuntimeError:
                    loop = None
                    
                if loop and loop.is_running():
                    asyncio.run_coroutine_threadsafe(_process_approval_reply(token, resolution), loop)
                else:
                    asyncio.run(_process_approval_reply(token, resolution))

        mail.close()
        mail.logout()
    except Exception as e:
        if "EOF" in str(e):
            logger.info(f"[InboxPoller] IMAP timeout/EOF (expected if no new mail). Retrying next cycle.")
        else:
            logger.error(f"[InboxPoller] IMAP connection failed: {e}")


async def _process_approval_reply(token: str, resolution: str):
    """Process an approval reply found via IMAP and resume the agent."""
    from sqlalchemy import select
    try:
        async with async_session() as session:
            stmt = select(PendingEmailApproval).where(PendingEmailApproval.token == token)
            result = await session.execute(stmt)
            pending = result.scalar_one_or_none()
            
            if not pending or pending.resolved:
                logger.info(f"[InboxPoller] Token {token} already resolved or not found in DB.")
                return
                
            # Mark it
            pending.resolved = True
            pending.resolution = resolution
            pending.resolved_at = datetime.utcnow()
            
            # Insert a ChatMessage from the user so the agent picks it up
            # This simulates the user typing "approve" or "skip" in the dashboard
            import uuid
            msg_content = "approve" if resolution == "approved" else "skip"
            
            msg = ChatMessage(
                id=str(uuid.uuid4()),
                user_id=pending.user_id,
                role="user",
                agent_name=None,
                goal_id=pending.goal_id,
                content=msg_content,
            )
            session.add(msg)
            await session.commit()
            
            logger.info(f"[InboxPoller] ✅ Successfully processed email {resolution} for goal {pending.goal_id}")
            
    except Exception as e:
        logger.error(f"[InboxPoller] Failed to process approval reply: {e}")
