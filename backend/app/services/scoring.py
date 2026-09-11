"""体测原始值 → 标准分(T 分)换算。

规则: z = (x - mean) / stddev; 成绩越小越好的指标取 -z。
      T = 50 + 10z,截断到 [20, 80]。
常模优先按 性别+年龄 精确匹配,否则回退到该年龄通用常模(gender IS NULL)。
"""
from datetime import date

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ..models import fitness_metrics, fitness_norms, players

CLAMP_LOW, CLAMP_HIGH = 20.0, 80.0


def age_on(birth: date, on: date) -> int:
    return on.year - birth.year - ((on.month, on.day) < (birth.month, birth.day))


async def load_metric_catalog(db: AsyncSession) -> dict[str, dict]:
    rows = await db.execute(
        select(fitness_metrics).order_by(fitness_metrics.c.sort_order)
    )
    return {
        r.code: {
            "id": r.id,
            "code": r.code,
            "name": r.name,
            "unit": r.unit,
            "direction": r.direction,
        }
        for r in rows
    }


async def _norm(db: AsyncSession, metric_id: int, age: int, gender: str):
    row = (
        await db.execute(
            select(fitness_norms.c.mean, fitness_norms.c.stddev)
            .where(
                fitness_norms.c.metric_id == metric_id,
                fitness_norms.c.age == age,
                fitness_norms.c.gender == gender,
            )
        )
    ).first()
    if row is None:
        row = (
            await db.execute(
                select(fitness_norms.c.mean, fitness_norms.c.stddev).where(
                    fitness_norms.c.metric_id == metric_id,
                    fitness_norms.c.age == age,
                    fitness_norms.c.gender.is_(None),
                )
            )
        ).first()
    return row


async def score_test(
    db: AsyncSession, player_row, test_date: date, raw_metrics: dict[str, float]
) -> tuple[list[dict], float | None]:
    """返回 (逐项得分列表, 标准分均值)。player_row 为 players 表的 Row。"""
    catalog = await load_metric_catalog(db)
    age = max(8, min(14, age_on(player_row.birth_date, test_date)))
    scored: list[dict] = []
    total_parts: list[float] = []

    for code, raw in raw_metrics.items():
        meta = catalog.get(code)
        if meta is None:
            continue
        norm = await _norm(db, meta["id"], age, player_row.gender)
        t_score: float | None = None
        if norm is not None and float(norm.stddev) > 0:
            z = (float(raw) - float(norm.mean)) / float(norm.stddev)
            if meta["direction"] == "lower_better":
                z = -z
            t_score = round(min(CLAMP_HIGH, max(CLAMP_LOW, 50 + 10 * z)), 2)
            total_parts.append(t_score)
        scored.append(
            {
                "code": code,
                "name": meta["name"],
                "unit": meta["unit"],
                "raw": float(raw),
                "score": t_score,
                "direction": meta["direction"],
            }
        )

    total = round(sum(total_parts) / len(total_parts), 2) if total_parts else None
    return scored, total
