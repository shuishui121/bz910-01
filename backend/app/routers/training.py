from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession

from ..database import get_db
from ..deps import current_user, ensure_player_access
from ..models import training_weeks
from ..response import ok
from ..schemas import TrainingWeekIn

router = APIRouter(prefix="/players/{player_id}/training-weeks", tags=["周训练"])


@router.get("")
async def list_weeks(
    player_id: int,
    season_year: int = 2026,
    db: AsyncSession = Depends(get_db),
    user=Depends(current_user),
):
    await ensure_player_access(db, user, player_id)
    rows = (
        await db.execute(
            select(training_weeks)
            .where(
                training_weeks.c.player_id == player_id,
                training_weeks.c.season_year == season_year,
            )
            .order_by(training_weeks.c.week_no)
        )
    ).all()
    return ok([_serialize(r._mapping) for r in rows])


@router.put("")
async def upsert_week(
    player_id: int,
    body: TrainingWeekIn,
    season_year: int = 2026,
    db: AsyncSession = Depends(get_db),
    user=Depends(current_user),
):
    """录入/更新某周训练内容(按 学员+赛季+周次 唯一,重复提交为覆盖更新)。"""
    await ensure_player_access(db, user, player_id, writable=True)

    stmt = (
        pg_insert(training_weeks)
        .values(
            player_id=player_id,
            season_year=season_year,
            week_no=body.week_no,
            training_date=body.training_date,
            coach_id=user["id"],
            technical_items=body.technical_items,
            physical_items=body.physical_items,
            matches=body.matches,
            summary=body.summary,
        )
        .on_conflict_do_update(
            constraint="training_weeks_player_id_season_year_week_no_key",
            set_={
                "training_date": body.training_date,
                "coach_id": user["id"],
                "technical_items": body.technical_items,
                "physical_items": body.physical_items,
                "matches": body.matches,
                "summary": body.summary,
            },
        )
        .returning(training_weeks)
    )
    row = (await db.execute(stmt)).first()
    await db.commit()
    return ok(_serialize(row._mapping), "训练周报已保存")


def _serialize(m) -> dict:
    return {
        "id": m["id"],
        "week_no": m["week_no"],
        "training_date": m["training_date"].isoformat(),
        "coach_id": m["coach_id"],
        "technical_items": m["technical_items"],
        "physical_items": m["physical_items"],
        "matches": m["matches"],
        "summary": m["summary"],
        "updated_at": m["updated_at"].isoformat() if m["updated_at"] else None,
    }
