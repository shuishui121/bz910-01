"""月度评语 —— 乐观锁并发控制。

同一学员同月评语唯一。提交时携带 base_version:
  * 与服务端当前版本一致 -> 正常提交,版本号 +1;
  * 不一致 -> 409,返回双方内容,前端提示"覆盖/合并";
  * 并发插入撞唯一键  -> 同样按 409 冲突处理。
每次落库同步写 comment_versions 审计链。
"""
from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from ..database import get_db
from ..deps import current_user, ensure_player_access
from ..models import comment_versions, monthly_comments, users
from ..response import BizError, ok
from ..schemas import CommentConflictIn, CommentIn

router = APIRouter(prefix="/players/{player_id}/comments", tags=["月度评语"])


async def _fetch(db: AsyncSession, player_id: int, year: int, month: int):
    return (
        await db.execute(
            select(monthly_comments).where(
                monthly_comments.c.player_id == player_id,
                monthly_comments.c.season_year == year,
                monthly_comments.c.month == month,
            )
        )
    ).first()


async def _conflict(db: AsyncSession, player_id: int, year: int, month: int,
                    submitted: str) -> BizError:
    cur = await _fetch(db, player_id, year, month)
    coach_name = None
    if cur is not None:
        coach = (
            await db.execute(select(users.c.full_name).where(users.c.id == cur.coach_id))
        ).first()
        coach_name = coach[0] if coach else None
    return BizError(
        40901,
        "评语已被其他教练修改,请选择覆盖或合并",
        http_status=409,
        data={
            "current_version": cur.version if cur else 1,
            "current_content": cur.content if cur else "",
            "current_coach_name": coach_name,
            "submitted_content": submitted,
        },
    )


async def _write_history(db, row) -> None:
    await db.execute(
        comment_versions.insert().values(
            comment_id=row.id,
            player_id=row.player_id,
            season_year=row.season_year,
            month=row.month,
            content=row.content,
            coach_id=row.coach_id,
            version=row.version,
        )
    )


@router.get("")
async def list_comments(
    player_id: int,
    season_year: int = 2026,
    db: AsyncSession = Depends(get_db),
    user=Depends(current_user),
):
    await ensure_player_access(db, user, player_id)
    rows = (
        await db.execute(
            select(monthly_comments, users.c.full_name.label("coach_name"))
            .join(users, users.c.id == monthly_comments.c.coach_id)
            .where(
                monthly_comments.c.player_id == player_id,
                monthly_comments.c.season_year == season_year,
            )
            .order_by(monthly_comments.c.month)
        )
    ).all()
    return ok([
        {
            "id": r.id,
            "season_year": r.season_year,
            "month": r.month,
            "content": r.content,
            "coach_id": r.coach_id,
            "coach_name": r.coach_name,
            "version": r.version,
            "updated_at": r.updated_at.isoformat() if r.updated_at else None,
        }
        for r in rows
    ])


@router.put("", summary="新建/更新评语(携带 base_version 做乐观锁)")
async def save_comment(
    player_id: int,
    body: CommentIn,
    db: AsyncSession = Depends(get_db),
    user=Depends(current_user),
):
    await ensure_player_access(db, user, player_id, writable=True)
    cur = await _fetch(db, player_id, body.season_year, body.month)

    if cur is None:
        # 首次创建;并发下另一教练可能抢先插入 -> 唯一约束兜底转 409
        try:
            result = await db.execute(
                monthly_comments.insert()
                .values(
                    player_id=player_id,
                    season_year=body.season_year,
                    month=body.month,
                    content=body.content,
                    coach_id=user["id"],
                    version=1,
                )
                .returning(monthly_comments)
            )
            row = result.first()
            await _write_history(db, row)
            await db.commit()
        except IntegrityError:
            await db.rollback()
            raise await _conflict(db, player_id, body.season_year, body.month,
                                  body.content)
        return ok({"id": row.id, "version": 1, "content": row.content}, "评语已提交")

    # 已存在:版本不匹配即冲突
    if body.base_version != cur.version:
        raise await _conflict(db, player_id, body.season_year, body.month,
                              body.content)

    result = await db.execute(
        monthly_comments.update()
        .where(
            monthly_comments.c.id == cur.id,
            monthly_comments.c.version == cur.version,  # 原子CAS,双保险
        )
        .values(
            content=body.content,
            coach_id=user["id"],
            version=monthly_comments.c.version + 1,
        )
        .returning(monthly_comments)
    )
    row = result.first()
    if row is None:  # 极端并发下 CAS 落空
        raise await _conflict(db, player_id, body.season_year, body.month,
                              body.content)
    await _write_history(db, row)
    await db.commit()
    return ok(
        {"id": row.id, "version": row.version, "content": row.content},
        "评语已提交",
    )


@router.post("/resolve", summary="冲突解决:覆盖或合并后提交")
async def resolve_conflict(
    player_id: int,
    body: CommentConflictIn,
    db: AsyncSession = Depends(get_db),
    user=Depends(current_user),
):
    await ensure_player_access(db, user, player_id, writable=True)
    final_content = body.content if body.action == "overwrite" else body.merged_content
    if body.action == "merge" and not (final_content or "").strip():
        raise BizError(40001, "合并内容不能为空")

    cur = await _fetch(db, player_id, body.season_year, body.month)
    if cur is None:
        raise BizError(40400, "评语不存在,请直接新建", http_status=404)

    result = await db.execute(
        monthly_comments.update()
        .where(monthly_comments.c.id == cur.id)
        .values(
            content=final_content,
            coach_id=user["id"],
            version=monthly_comments.c.version + 1,
        )
        .returning(monthly_comments)
    )
    row = result.first()
    await _write_history(db, row)
    await db.commit()
    return ok(
        {"id": row.id, "version": row.version, "content": row.content},
        "已覆盖并提交" if body.action == "overwrite" else "合并内容已提交",
    )


@router.get("/{season_year}/{month}/versions", summary="评语历史版本")
async def comment_versions_list(
    player_id: int,
    season_year: int,
    month: int,
    db: AsyncSession = Depends(get_db),
    user=Depends(current_user),
):
    await ensure_player_access(db, user, player_id)
    rows = (
        await db.execute(
            select(comment_versions, users.c.full_name.label("coach_name"))
            .join(users, users.c.id == comment_versions.c.coach_id)
            .where(
                comment_versions.c.player_id == player_id,
                comment_versions.c.season_year == season_year,
                comment_versions.c.month == month,
            )
            .order_by(comment_versions.c.version)
        )
    ).all()
    return ok([
        {
            "version": r.version,
            "content": r.content,
            "coach_id": r.coach_id,
            "coach_name": r.coach_name,
            "edited_at": r.edited_at.isoformat() if r.edited_at else None,
        }
        for r in rows
    ])
