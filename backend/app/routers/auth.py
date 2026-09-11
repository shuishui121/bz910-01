from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ..database import get_db
from ..deps import current_user
from ..models import users
from ..response import BizError, ok
from ..schemas import LoginIn
from ..security import create_access_token, verify_password

router = APIRouter(prefix="/auth", tags=["认证"])


@router.post("/login")
async def login(body: LoginIn, db: AsyncSession = Depends(get_db)):
    row = (
        await db.execute(select(users).where(users.c.username == body.username))
    ).first()
    if row is None or not verify_password(body.password, row.password_hash):
        raise BizError(40100, "用户名或密码错误", http_status=401)
    if not row.is_active:
        raise BizError(40300, "账号已停用", http_status=403)

    token = create_access_token(row.id, row.role)
    return ok(
        {
            "token": token,
            "user": {
                "id": row.id,
                "username": row.username,
                "full_name": row.full_name,
                "role": row.role,
            },
        },
        "登录成功",
    )


@router.get("/me")
async def me(user=Depends(current_user)):
    return ok(
        {
            "id": user["id"],
            "username": user["username"],
            "full_name": user["full_name"],
            "role": user["role"],
        }
    )
