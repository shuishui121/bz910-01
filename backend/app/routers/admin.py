from fastapi import APIRouter, Depends
from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession

from ..database import get_db
from ..deps import current_user, require_roles
from ..models import fitness_metrics
from ..response import BizError, ok

router = APIRouter(tags=["基础数据与归档"])


@router.get("/metrics", summary="体测指标目录")
async def list_metrics(db: AsyncSession = Depends(get_db), user=Depends(current_user)):
    rows = await db.execute(
        select(fitness_metrics).order_by(fitness_metrics.c.sort_order)
    )
    return ok([
        {
            "id": r.id,
            "code": r.code,
            "name": r.name,
            "unit": r.unit,
            "direction": r.direction,
        }
        for r in rows
    ])


@router.post("/admin/archive/{year}", summary="按年份归档(摘除历史赛季分区)")
async def archive_year(
    year: int,
    db: AsyncSession = Depends(get_db),
    user=Depends(require_roles("admin")),
):
    if year >= 2025:
        raise BizError(40001, "只能归档历史年份,当前赛季不可摘除")

    result = await db.execute(
        text("SELECT parent_name, archived_table, rows_archived "
             "FROM archive_season(:y)"),
        {"y": year},
    )
    await db.commit()
    return ok(
        [dict(r._mapping) for r in result],
        f"{year} 赛季分区已摘除为独立归档表,可转储冷存储后删除",
    )
