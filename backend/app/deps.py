"""鉴权与数据权限依赖。

角色权限:
  admin  —— 全部数据
  coach  —— 仅本人当赛季 coach_assignments 中负责的学员(可写训练/体测/评语)
  parent —— 仅本人 parent_links 绑定的孩子(只读)
"""
from fastapi import Depends, Header
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from .database import get_db
from .models import coach_assignments, parent_links, users
from .response import BizError
from .security import decode_token

async def current_user(
    authorization: str | None = Header(default=None),
    db: AsyncSession = Depends(get_db),
) -> dict:
    if not authorization or not authorization.lower().startswith("bearer "):
        raise BizError(40100, "未登录或缺少令牌", http_status=401)
    token = authorization.split(" ", 1)[1].strip()
    try:
        payload = decode_token(token)
    except ValueError:
        raise BizError(40100, "登录已失效,请重新登录", http_status=401)

    row = (
        await db.execute(select(users).where(users.c.id == int(payload["sub"])))
    ).first()
    if row is None or not row.is_active:
        raise BizError(40100, "账号不存在或已停用", http_status=401)
    return dict(row._mapping)


def require_roles(*roles: str):
    async def _checker(user=Depends(current_user)):
        if user["role"] not in roles:
            raise BizError(40300, "无权访问该功能", http_status=403)
        return user
    return _checker


async def ensure_player_access(
    db: AsyncSession, user: dict, player_id: int, *, writable: bool = False
) -> None:
    """家长始终只读;教练需为该学员负责教练且当赛季在带。"""
    if user["role"] == "admin":
        return
    if user["role"] == "parent":
        if writable:
            raise BizError(40300, "家长账号为只读权限", http_status=403)
        ok_row = (
            await db.execute(
                select(parent_links.c.id).where(
                    parent_links.c.parent_id == user["id"],
                    parent_links.c.player_id == player_id,
                )
            )
        ).first()
        if ok_row is None:
            raise BizError(40300, "只能查看自己孩子的档案", http_status=403)
        return
    if user["role"] == "coach":
        row = (
            await db.execute(
                select(coach_assignments.c.id).where(
                    coach_assignments.c.coach_id == user["id"],
                    coach_assignments.c.player_id == player_id,
                )
            )
        ).first()
        if row is None:
            raise BizError(40300, "该学员不在你的负责名单中", http_status=403)
        return
    raise BizError(40300, "未知角色", http_status=403)
