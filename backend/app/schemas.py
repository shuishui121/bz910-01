from datetime import date
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field


# ----------------------------------------------------------------- auth
class LoginIn(BaseModel):
    username: str
    password: str


# ----------------------------------------------------------------- player
class PlayerOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    name: str
    gender: str
    birth_date: date
    group_name: str
    joined_year: int
    status: str
    relationship: str | None = None  # 家长视角:与孩子关系
    is_lead: bool | None = None      # 教练视角:是否主教练


# ----------------------------------------------------------------- training
class TrainingWeekIn(BaseModel):
    week_no: int = Field(ge=1, le=53)
    training_date: date
    technical_items: list[dict[str, Any]] = Field(default_factory=list)
    physical_items: list[dict[str, Any]] = Field(default_factory=list)
    matches: list[dict[str, Any]] = Field(default_factory=list)
    summary: str | None = None


# ----------------------------------------------------------------- fitness
class FitnessTestIn(BaseModel):
    test_date: date
    week_no: int | None = Field(default=None, ge=1, le=53)
    metrics: dict[str, float]  # {metric_code: raw_value}


class MetricScore(BaseModel):
    code: str
    name: str
    unit: str
    raw: float
    score: float | None      # 标准分 T
    direction: str


class FitnessTestOut(BaseModel):
    id: int
    test_date: date
    week_no: int | None
    total_score: float | None
    metrics: list[MetricScore]


# ----------------------------------------------------------------- comments
class CommentIn(BaseModel):
    season_year: int = Field(ge=2000, le=2100)
    month: int = Field(ge=1, le=12)
    content: str
    base_version: int | None = None  # 编辑所基于的版本;为空=新建


class CommentConflictIn(BaseModel):
    season_year: int
    month: int
    content: str
    action: Literal["overwrite", "merge"]
    merged_content: str | None = None  # action=merge 时使用合并后的文本


class CommentOut(BaseModel):
    id: int
    season_year: int
    month: int
    content: str
    coach_id: int
    coach_name: str | None = None
    version: int
    updated_at: Any


# ----------------------------------------------------------------- promotion
class PromotionConfirmIn(BaseModel):
    recommended: bool
    target_group: str | None = None
    coach_note: str | None = None
