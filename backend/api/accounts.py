from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from typing import List, Optional
from pydantic import BaseModel
import uuid

from database import get_db, PlatformConnection
from auth import get_current_user

router = APIRouter(prefix="/api/accounts", tags=["accounts"])

class AccountCreate(BaseModel):
    platform: str
    display_name: str
    account_label: str
    auth_data: Optional[str] = None
    account_name: Optional[str] = None

class AccountUpdate(BaseModel):
    display_name: Optional[str] = None
    account_label: Optional[str] = None
    auth_data: Optional[str] = None
    is_enabled: Optional[bool] = None

@router.get("/", response_model=List[dict])
async def list_accounts(db: AsyncSession = Depends(get_db), current_user = Depends(get_current_user)):
    stmt = select(PlatformConnection)
    result = await db.execute(stmt)
    accounts = result.scalars().all()
    # Mask sensitive data inside auth_data if we wanted, but since it's the owner's dashboard we return it
    out = []
    for a in accounts:
        out.append({
            "id": a.id,
            "platform": a.platform,
            "display_name": a.display_name,
            "account_label": a.account_label,
            "account_name": a.account_name,
            "auth_data": a.auth_data,
            "is_enabled": a.is_enabled,
            "connection_status": a.connection_status
        })
    return out

@router.post("")
async def create_account(account: AccountCreate, db: AsyncSession = Depends(get_db), current_user = Depends(get_current_user)):
    new_account = PlatformConnection(
        id=str(uuid.uuid4()),
        platform=account.platform,
        display_name=account.display_name,
        account_label=account.account_label,
        auth_data=account.auth_data,
        account_name=account.account_name,
        is_enabled=True,
        connection_status="connected" # Assume connected if they supply truth bucket info, or ghost will update it later
    )
    db.add(new_account)
    await db.commit()
    return {"status": "success", "id": new_account.id}

@router.put("/{account_id}")
async def update_account(account_id: str, updates: AccountUpdate, db: AsyncSession = Depends(get_db), current_user = Depends(get_current_user)):
    stmt = select(PlatformConnection).where(PlatformConnection.id == account_id)
    result = await db.execute(stmt)
    acc = result.scalar_one_or_none()
    if not acc:
        raise HTTPException(status_code=404, detail="Account not found")
        
    exclude = updates.model_dump(exclude_unset=True)
    for k, v in exclude.items():
        setattr(acc, k, v)
        
    await db.commit()
    return {"status": "success"}

@router.delete("/{account_id}")
async def delete_account(account_id: str, db: AsyncSession = Depends(get_db), current_user = Depends(get_current_user)):
    stmt = select(PlatformConnection).where(PlatformConnection.id == account_id)
    result = await db.execute(stmt)
    acc = result.scalar_one_or_none()
    if acc:
        await db.delete(acc)
        await db.commit()
    return {"status": "success"}
