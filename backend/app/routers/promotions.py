"""季度升组建议。

季末取每位学员在该季度内最近一次体测总分(标准分均分),按当前训练组内
降序排名:前 30% 推荐升组。教练可在系统建议基础上修改确认。
重新生成不会覆盖教练已确认/驳回的结论。
"""
import calendar
import math
from datetime import date

from fastapi import APIRouter, Depends
from sqlalchemy import func, select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession

from ..database import get_db
from ..deps import current_user, ensure_player_access
from ..models import (
    coach_assignments,
    fitness_tests,
    parent_links,
    players,
    promotion_suggestions,
)
from ..response import BizError, ok
from ..schemas import PromotionConfirmIn

router = APIRouter(prefix="/promotions", tags=["升组建议"])

NEXT_GROUP = {"启蒙组": "提高组", "提高组": "精英组"}


def _quarter_range(year: int, quarter: int) -> tuple[date, date]:
    start_month = (quarter - 1) * 3 + 1
    end_month = start_month + 2
    last_day = calendar.monthrange(year, end_month)[1]
    return date(year, start_month, 1), date(year, end_month, last_day)


@router.post("/generate", summary="季末自动生成(前30%推荐升组)")
async def generate(
    season_year: int,
    quarter: int,
    db: AsyncSession = Depends(get_db),
    user=Depends(current_user),
):
    if user["role"] not in ("coach", "admin"):
        raise BizError(40300, "仅教练/管理员可生成升组建议", http_status=403)

    start, end = _quarter_range(season_year, quarter)

    # 全体在册学员 + 该季度最近一次体测
    all_players = (
        await db.execute(
            select(players).where(players.c.status != "left").order_by(players.c.group_name)
        )
    ).all()

    cohort: dict[str, list[tuple]] = {}  # group_name -> [(player, latest_test)]
    for p in all_players:
        t = (
            await db.execute(
                select(fitness_tests)
                .where(
                    fitness_tests.c.player_id == p.id,
                    fitness_tests.c.season_year == season_year,
                    fitness_tests.c.test_date >= start,
                    fitness_tests.c.test_date <= end,
                    fitness_tests.c.total_score.is_not(None),
                )
                .order_by(fitness_tests.c.test_date.desc())
                .limit(1)
            )
        ).first()
        if t is not None:
            cohort.setdefault(p.group_name, []).append((p, t))

    upserted = 0
    for group_name, members in cohort.items():
        members.sort(key=lambda x: float(x[1].total_score), reverse=True)
        size = len(members)
        cutoff = math.ceil(size * 0.30)  # 前 30%

        for rank, (p, t) in enumerate(members, start=1):
            recommended = rank <= cutoff
            percentile = round((1 - (rank - 1) / size) * 100, 2)
            target = NEXT_GROUP.get(group_name) if recommended else None

            existing = (
                await db.execute(
                    select(promotion_suggestions.c.status).where(
                        promotion_suggestions.c.player_id == p.id,
                        promotion_suggestions.c.season_year == season_year,
                        promotion_suggestions.c.quarter == quarter,
                    )
                )
            ).first()
            # 教练已确认/调整/驳回的结论不被重新生成覆盖
            if existing is not None and existing.status != "suggested":
                continue

            stmt = (
                pg_insert(promotion_suggestions)
                .values(
                    player_id=p.id,
                    season_year=season_year,
                    quarter=quarter,
                    total_score=t.total_score,
                    rank_in_group=rank,
                    cohort_size=size,
                    percentile=percentile,
                    recommended=recommended,
                    target_group=target,
                    status="suggested",
                )
                .on_conflict_do_update(
                    constraint="promotion_suggestions_player_id_season_year_quarter_key",
                    set_={
                        "total_score": t.total_score,
                        "rank_in_group": rank,
                        "cohort_size": size,
                        "percentile": percentile,
                        "recommended": recommended,
                        "target_group": target,
                    },
                )
            )
            await db.execute(stmt)
            upserted += 1

    await db.commit()
    return ok({"upserted": upserted, "groups": list(cohort)}, "升组建议已生成")


@router.get("")
async def list_suggestions(
    season_year: int,
    quarter: int,
    group_name: str | None = None,
    db: AsyncSession = Depends(get_db),
    user=Depends(current_user),
):
    stmt = (
        select(
            promotion_suggestions.c.id,
            promotion_suggestions.c.player_id,
            players.c.name.label("player_name"),
            players.c.group_name,
            promotion_suggestions.c.total_score,
            promotion_suggestions.c.rank_in_group,
            promotion_suggestions.c.cohort_size,
            promotion_suggestions.c.percentile,
            promotion_suggestions.c.recommended,
            promotion_suggestions.c.target_group,
            promotion_suggestions.c.status,
            promotion_suggestions.c.coach_id,
            promotion_suggestions.c.coach_note,
            promotion_suggestions.c.generated_at,
            promotion_suggestions.c.confirmed_at,
        )
        .join(players, players.c.id == promotion_suggestions.c.player_id)
        .where(
            promotion_suggestions.c.season_year == season_year,
            promotion_suggestions.c.quarter == quarter,
        )
        .order_by(players.c.group_name, promotion_suggestions.c.rank_in_group)
    )
    if group_name:
        stmt = stmt.where(players.c.group_name == group_name)

    if user["role"] == "coach":
        stmt = stmt.where(
            promotion_suggestions.c.player_id.in_(
                select(coach_assignments.c.player_id).where(
                    coach_assignments.c.coach_id == user["id"]
                )
            )
        )
    elif user["role"] == "parent":
        stmt = stmt.where(
            promotion_suggestions.c.player_id.in_(
                select(parent_links.c.player_id).where(
                    parent_links.c.parent_id == user["id"]
                )
            )
        )

    rows = (await db.execute(stmt)).all()
    return ok([
        {
            "id": r.id,
            "player_id": r.player_id,
            "player_name": r.name,
            "group_name": r.group_name,
            "total_score": float(r.total_score),
            "rank_in_group": r.rank_in_group,
            "cohort_size": r.cohort_size,
            "percentile": float(r.percentile) if r.percentile is not None else None,
            "recommended": r.recommended,
            "target_group": r.target_group,
            "status": r.status,
            "coach_id": r.coach_id,
            "coach_note": r.coach_note,
            "generated_at": r.generated_at.isoformat() if r.generated_at else None,
            "confirmed_at": r.confirmed_at.isoformat() if r.confirmed_at else None,
        }
        for r in rows
    ])


@router.put("/{suggestion_id}/confirm", summary="教练修改并确认升组建议")
async def confirm(
    suggestion_id: int,
    season_year: int,
    body: PromotionConfirmIn,
    db: AsyncSession = Depends(get_db),
    user=Depends(current_user),
):
    if user["role"] not in ("coach", "admin"):
        raise BizError(40300, "仅教练可确认升组建议", http_status=403)

    row = (
        await db.execute(
            select(promotion_suggestions).where(
                promotion_suggestions.c.id == suggestion_id,
                promotion_suggestions.c.season_year == season_year,
            )
        )
    ).first()
    if row is None:
        raise BizError(40400, "升组建议不存在", http_status=404)

    await ensure_player_access(db, user, row.player_id, writable=True)

    status = "confirmed" if body.recommended == row.recommended else "adjusted"
    result = await db.execute(
        promotion_suggestions.update()
        .where(promotion_suggestions.c.id == suggestion_id)
        .values(
            recommended=body.recommended,
            target_group=body.target_group
            if body.target_group is not None
            else row.target_group,
            coach_note=body.coach_note,
            coach_id=user["id"],
            status=status,
            confirmed_at=func.now(),
        )
        .returning(promotion_suggestions)
    )
    await db.commit()
    return ok({"id": suggestion_id, "status": status}, "升组结论已确认")
