"""
Digital Force — Agent Email Notification Utility

Sends branded HTML emails FROM digitalforce1st@gmail.com TO digitalforce1st@gmail.com
(Reply-To is set so replies come back to the same inbox for polling).

Each approval email embeds a unique token in the subject line:
  [Digital Force | Ref: <token>]

The inbox poller (email_inbox.py) reads replies, matches the token,
and triggers the appropriate agent action.
"""

import logging
import uuid
import smtplib
from datetime import datetime, timedelta
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from typing import Optional
from config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()

# Send FROM this address
EMAIL_FROM      = settings.smtp_from_email or settings.smtp_username
EMAIL_FROM_NAME = settings.smtp_from_name or "Digital Force"


async def send_agent_email(
    subject: str,
    body_text: str,
    body_html: Optional[str] = None,
    approval_token: Optional[str] = None,
    to_email: Optional[str] = None,
) -> bool:
    """
    Send an email to the user's inbox.
    If approval_token is provided, it's embedded in the subject for reply matching.
    """
    if not settings.smtp_username or not settings.smtp_password:
        logger.warning("[Email] SMTP not configured — skipping")
        return False

    recipient = to_email or settings.smtp_username
    if not recipient:
        return False

    full_subject = f"[Digital Force] {subject}"
    if approval_token:
        full_subject += f" | Ref: {approval_token}"

    msg = MIMEMultipart("alternative")
    msg["Subject"]  = full_subject
    msg["From"]     = f"{EMAIL_FROM_NAME} <{EMAIL_FROM}>"
    msg["To"]       = recipient
    msg["Reply-To"] = EMAIL_FROM  # Replies come back to the FROM inbox for IMAP polling

    msg.attach(MIMEText(body_text, "plain"))
    html = body_html or _auto_html(subject, body_text, approval_token)
    msg.attach(MIMEText(html, "html"))

    try:
        import asyncio
        loop = asyncio.get_event_loop()
        await loop.run_in_executor(None, _smtp_send, msg, recipient)
        logger.info(f"[Email] ✅ Sent '{full_subject}' to {recipient}")
        return True
    except Exception as e:
        logger.error(f"[Email] Failed: {e}")
        return False


def _smtp_send(msg: MIMEMultipart, recipient: str):
    with smtplib.SMTP(settings.smtp_host, settings.smtp_port) as server:
        server.ehlo()
        server.starttls()
        server.login(settings.smtp_username, settings.smtp_password)
        server.sendmail(EMAIL_FROM, recipient, msg.as_string())


def _auto_html(subject: str, text: str, token: Optional[str] = None) -> str:
    paragraphs = "".join(
        f"<p style='margin:0 0 12px;line-height:1.6;color:rgba(255,255,255,0.75);'>{line}</p>"
        for line in text.split("\n") if line.strip()
    )
    reply_hint = ""
    if token:
        reply_hint = """
        <div style='margin-top:24px;padding:16px;border-radius:12px;background:rgba(124,58,237,0.12);border:1px solid rgba(124,58,237,0.25);'>
          <p style='margin:0 0 8px;font-weight:600;color:#A78BFA;font-size:0.9rem;'>💬 How to respond</p>
          <p style='margin:0;color:rgba(255,255,255,0.6);font-size:0.85rem;'>
            Simply <strong style='color:#fff;'>reply to this email</strong> with one of:
            <br><br>
            &nbsp;&nbsp;✅ <strong>approve</strong> — to authorise and execute<br>
            &nbsp;&nbsp;❌ <strong>skip</strong> — to drop this task<br>
            <br>
            Or open your <a href='http://localhost:3000/chat' style='color:#A78BFA;'>Digital Force dashboard</a> and respond in chat.
          </p>
        </div>
        """

    return f"""<!DOCTYPE html>
<html><head><meta charset="utf-8"></head>
<body style="margin:0;padding:0;background:#0d0d1a;font-family:Inter,Arial,sans-serif;">
  <table width="100%" cellpadding="0" cellspacing="0">
    <tr><td align="center" style="padding:40px 20px;">
      <table width="600" cellpadding="0" cellspacing="0"
        style="background:#13131f;border-radius:16px;border:1px solid rgba(255,255,255,0.08);overflow:hidden;">
        <tr>
          <td style="padding:28px 32px;background:linear-gradient(135deg,#7C3AED22,#22D3EE11);
            border-bottom:1px solid rgba(255,255,255,0.06);">
            <span style="font-size:1.1rem;font-weight:700;color:#fff;">⚡ Digital Force</span>
            <span style="font-size:0.75rem;color:rgba(255,255,255,0.35);margin-left:10px;">Autonomous Agency</span>
          </td>
        </tr>
        <tr>
          <td style="padding:32px;">
            <h2 style="margin:0 0 20px;font-size:1.1rem;font-weight:600;color:#fff;">{subject}</h2>
            {paragraphs}
            {reply_hint}
          </td>
        </tr>
        <tr>
          <td style="padding:16px 32px;border-top:1px solid rgba(255,255,255,0.06);">
            <p style="margin:0;font-size:0.72rem;color:rgba(255,255,255,0.2);">
              Sent autonomously by your Digital Force agents.
              {f"Reference: {token}" if token else ""}
            </p>
          </td>
        </tr>
      </table>
    </td></tr>
  </table>
</body></html>"""


# ─── Specialised helpers ──────────────────────────────────────────────────────

async def _get_user_email(user_id: str) -> Optional[str]:
    if not user_id:
        return None
    try:
        from database import async_session, User
        from sqlalchemy import select
        async with async_session() as session:
            stmt = select(User.email).where(User.id == user_id)
            result = await session.execute(stmt)
            return result.scalar_one_or_none()
    except Exception as e:
        logger.error(f"[Email] Failed to fetch user email: {e}")
        return None


async def notify_api_key_needed(
    capability: str,
    api_name: str,
    signup_url: str,
    why_needed: str,
    is_free: bool,
    user_id: str = "",
    goal_id: str = "",
) -> Optional[str]:
    """
    Notify about a missing API credential.
    Returns the approval token (stored in DB by caller).
    """
    to_email = await _get_user_email(user_id)
    
    free_note = "✅ Free tier available — no credit card needed." if is_free else "⚠️ May require a paid plan — check pricing before signing up."
    subject = f"Action Required: API Key Needed for {capability}"
    body = f"""Your Digital Force agents want to unlock a new capability but need a credential.

Capability: {capability}

Why this is needed:
{why_needed}

API / Service: {api_name}
{free_note}
Sign up: {signup_url}

Once you have the key, add it in your dashboard under Settings → Integrations.
Your agents will automatically retry the stalled task.

— Your Digital Force Agents"""

    token = str(uuid.uuid4())[:8].upper()
    await send_agent_email(subject, body, approval_token=token, to_email=to_email)
    return token


async def notify_high_risk_approval(
    action_description: str,
    risk_reason: str,
    skill_name: str,
    user_id: str = "",
    goal_id: str = "",
) -> Optional[str]:
    """
    Email user for high-risk approval. Returns the token stored in PendingEmailApproval.
    """
    to_email = await _get_user_email(user_id)
    
    subject = f"Approval Required: {action_description}"
    body = f"""Your Digital Force agents have built a fix for a roadblock but need your green light.

Action: {action_description}

Why this needs your approval:
{risk_reason}

Skill built: {skill_name}

Reply to this email with:
  approve — to authorise and execute
  skip — to drop this task

Or respond in your Digital Force chat dashboard.

— Your Digital Force Agents"""

    token = str(uuid.uuid4())[:8].upper()

    # Store in DB so inbox poller can match replies
    try:
        from database import PendingEmailApproval, async_session
        from datetime import timedelta
        async with async_session() as session:
            session.add(PendingEmailApproval(
                id=str(uuid.uuid4()),
                token=token,
                user_id=user_id,
                action_type="high_risk",
                skill_name=skill_name,
                goal_id=goal_id,
                description=action_description,
                expires_at=datetime.utcnow() + timedelta(hours=48),
            ))
            await session.commit()
    except Exception as e:
        logger.error(f"[Email] Could not store pending approval: {e}")

    await send_agent_email(subject, body, approval_token=token, to_email=to_email)
    return token


async def notify_campaign_complete(
    campaign_title: str,
    summary: str,
    metrics: dict,
    user_id: str = "",
) -> bool:
    to_email = await _get_user_email(user_id)
    
    subject = f"Campaign Complete: {campaign_title}"
    metrics_text = "\n".join([f"  • {k}: {v}" for k, v in metrics.items()]) or "  No metrics recorded yet."
    body = f"""Your campaign has finished.

Campaign: {campaign_title}

Summary:
{summary}

Results:
{metrics_text}

Check your Digital Force dashboard for full analytics.

— Your Digital Force Agents"""
    return await send_agent_email(subject, body, to_email=to_email)
