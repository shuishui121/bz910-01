from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ..database import get_db
from ..deps import current_user, ensure_player_access
from ..models import coach_assignments, parent_links, players
from ..response import ok

router = APIRouter(prefix="/players", tags=["学员"])


@router.get("")
async def list_my_players(db: AsyncSession = Depends(get_db), user=Depends(current_user)):
    """按角色返回可见学员:教练=负责名单,家长=自家孩子,管理员=全部。"""
    if user["role"] == "coach":
        stmt = (
            select(players, coach_assignments.c.is_lead)
            .join(coach_assignments,
                  coach_assignments.c.player_id == players.c.id)
            .where(coach_assignments.c.coach_id == user["id"])
            .order_by(coach_assignments.c.is_lead.desc(), players.c.id)
        )
        rows = (await db.execute(stmt)).all()
        data = []
        for r in rows:
            d = _player_dict(r._mapping)
            d["is_lead"] = bool(r.is_lead)
            data.append(d)
        return ok(data)

    if user["role"] == "parent":
        stmt = (
            select(players, parent_links.c.relationship)
            .join(parent_links, parent_links.c.player_id == players.c.id)
            .where(parent_links.c.parent_id == user["id"])
        )
        rows = (await db.execute(stmt)).all()
        data = []
        for r in rows:
            d = _player_dict(r._mapping)
            d["relationship"] = r.relationship
            data.append(d)
        return ok(data)

    rows = (await db.execute(select(players).order_by(players.c.id))).all()
    return ok([_player_dict(r._mapping) for r in rows])


@router.get("/{player_id}")
async def player_detail(player_id: int, db=Depends(get_db), user=Depends(current_user)):
    await ensure_player_access(db, user, player_id)
    row = (
        await db.execute(select(players).where(players.c.id == player_id))
    ).first()
    return ok(_player_dict(row._mapping))


def _player_dict(m) -> dict:
    return {
        "id": m["id"],
        "name": m["name"],
        "gender": m["gender"],
        "birth_date": m["birth_date"].isoformat(),
        "group_name": m["group_name"],
        "joined_year": m["joined_year"],
        "status": m["status"],
    }
