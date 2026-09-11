from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ..database import get_db
from ..deps import current_user, ensure_player_access
from ..models import fitness_tests, players
from ..response import BizError, ok
from ..schemas import FitnessTestIn
from ..services.scoring import score_test

router = APIRouter(prefix="/players/{player_id}/fitness", tags=["体测与成长曲线"])


@router.get("")
async def list_tests(
    player_id: int,
    season_year: int = 2026,
    db: AsyncSession = Depends(get_db),
    user=Depends(current_user),
):
    await ensure_player_access(db, user, player_id)
    rows = (
        await db.execute(
            select(fitness_tests)
            .where(
                fitness_tests.c.player_id == player_id,
                fitness_tests.c.season_year == season_year,
            )
            .order_by(fitness_tests.c.test_date)
        )
    ).all()
    return ok([_serialize(r._mapping) for r in rows])


@router.post("", summary="录入住测并自动换算标准分")
async def create_test(
    player_id: int,
    body: FitnessTestIn,
    season_year: int = 2026,
    db: AsyncSession = Depends(get_db),
    user=Depends(current_user),
):
    await ensure_player_access(db, user, player_id, writable=True)
    if not body.metrics:
        raise BizError(40001, "至少录入一项体测指标")

    player = (
        await db.execute(select(players).where(players.c.id == player_id))
    ).first()
    if player is None:
        raise BizError(40400, "学员不存在", http_status=404)

    scored, total = await score_test(db, player, body.test_date, body.metrics)

    result = await db.execute(
        fitness_tests.insert()
        .values(
            player_id=player_id,
            season_year=season_year,
            test_date=body.test_date,
            week_no=body.week_no,
            coach_id=user["id"],
            metrics=body.metrics,
            total_score=total,
        )
        .returning(fitness_tests)
    )
    await db.commit()
    row = result.first()._mapping
    return ok({**_serialize(row), "metrics": scored}, "体测已录入,标准分已计算")


@router.get("/growth-chart", summary="成长曲线:各指标标准分随训练周变化")
async def growth_chart(
    player_id: int,
    season_year: int = 2026,
    db: AsyncSession = Depends(get_db),
    user=Depends(current_user),
):
    """
    返回:
      weeks   —— 横轴(训练周数)
      series  —— [{code,name,unit,data:[{week,raw,score}...]}]
      totals  —— 各周体测总分
    """
    await ensure_player_access(db, user, player_id)
    rows = (
        await db.execute(
            select(fitness_tests)
            .where(
                fitness_tests.c.player_id == player_id,
                fitness_tests.c.season_year == season_year,
            )
            .order_by(fitness_tests.c.test_date)
        )
    ).all()

    player = (
        await db.execute(select(players).where(players.c.id == player_id))
    ).first()

    points: dict[str, list] = {}
    weeks, totals = [], []
    for r in rows:
        m = r._mapping
        week = m.week_no
        if week is None:  # 未标注周次时按测试顺序编号
            week = len(weeks) + 1
        scored, total = await score_test(db, player, m.test_date, m.metrics)
        weeks.append(week)
        totals.append({"week": week, "test_date": m.test_date.isoformat(),
                       "total_score": float(m.total_score) if m.total_score is not None else total})
        for item in scored:
            points.setdefault(item["code"], {**item, "data": []})
            points[item["code"]]["data"].append(
                {"week": week, "raw": item["raw"], "score": item["score"]}
            )

    series = [
        {"code": v["code"], "name": v["name"], "unit": v["unit"],
         "direction": v["direction"], "data": v["data"]}
        for v in points.values()
    ]
    return ok({"weeks": weeks, "series": series, "totals": totals})


def _serialize(m) -> dict:
    return {
        "id": m["id"],
        "test_date": m["test_date"].isoformat(),
        "week_no": m["week_no"],
        "total_score": float(m["total_score"]) if m["total_score"] is not None else None,
        "metrics": m["metrics"],
    }
