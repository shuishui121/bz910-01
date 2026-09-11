"""SQLAlchemy Core 表定义,与 db/init/01_schema.sql 保持一致。"""
from sqlalchemy import (
    BigInteger,
    Boolean,
    CheckConstraint,
    Column,
    Date,
    DateTime,
    Integer,
    MetaData,
    Numeric,
    String,
    Table,
    Text,
    func,
)
from sqlalchemy.dialects.postgresql import ENUM as PGEnum
from sqlalchemy.dialects.postgresql import JSONB

metadata = MetaData()

role_enum = PGEnum("coach", "parent", "admin", name="user_role", create_type=False)
gender_enum = PGEnum("male", "female", name="gender_type", create_type=False)
direction_enum = PGEnum(
    "higher_better", "lower_better", name="metric_direction", create_type=False
)
promo_enum = PGEnum(
    "suggested", "confirmed", "adjusted", "rejected",
    name="promotion_status", create_type=False,
)
player_status_enum = PGEnum(
    "active", "promoted", "left", name="player_status", create_type=False
)

users = Table(
    "users", metadata,
    Column("id", BigInteger, primary_key=True),
    Column("username", String(64), nullable=False, unique=True),
    Column("password_hash", String(255), nullable=False),
    Column("full_name", String(64), nullable=False),
    Column("role", role_enum, nullable=False),
    Column("phone", String(32)),
    Column("is_active", Boolean, nullable=False, server_default="true"),
    Column("created_at", DateTime(timezone=True), server_default=func.now()),
)

players = Table(
    "players", metadata,
    Column("id", BigInteger, primary_key=True),
    Column("name", String(64), nullable=False),
    Column("gender", gender_enum, nullable=False),
    Column("birth_date", Date, nullable=False),
    Column("group_name", String(32), nullable=False, server_default="启蒙组"),
    Column("joined_year", Integer, nullable=False),
    Column("status", player_status_enum, nullable=False, server_default="active"),
    Column("created_at", DateTime(timezone=True), server_default=func.now()),
)

coach_assignments = Table(
    "coach_assignments", metadata,
    Column("id", BigInteger, primary_key=True),
    Column("coach_id", BigInteger, nullable=False),
    Column("player_id", BigInteger, nullable=False),
    Column("season_year", Integer, nullable=False),
    Column("is_lead", Boolean, nullable=False, server_default="false"),
    Column("created_at", DateTime(timezone=True), server_default=func.now()),
)

parent_links = Table(
    "parent_links", metadata,
    Column("id", BigInteger, primary_key=True),
    Column("parent_id", BigInteger, nullable=False),
    Column("player_id", BigInteger, nullable=False),
    Column("relationship", String(16), nullable=False, server_default="parent"),
    Column("verified", Boolean, nullable=False, server_default="true"),
    Column("created_at", DateTime(timezone=True), server_default=func.now()),
)

fitness_metrics = Table(
    "fitness_metrics", metadata,
    Column("id", BigInteger, primary_key=True),
    Column("code", String(32), nullable=False, unique=True),
    Column("name", String(64), nullable=False),
    Column("unit", String(16), nullable=False, server_default=""),
    Column("direction", direction_enum, nullable=False),
    Column("sort_order", Integer, nullable=False, server_default="0"),
)

fitness_norms = Table(
    "fitness_norms", metadata,
    Column("id", BigInteger, primary_key=True),
    Column("metric_id", BigInteger, nullable=False),
    Column("age", Integer, nullable=False),
    Column("gender", gender_enum),
    Column("mean", Numeric(8, 2), nullable=False),
    Column("stddev", Numeric(8, 2), nullable=False),
)

training_weeks = Table(
    "training_weeks", metadata,
    Column("id", BigInteger, primary_key=True),
    Column("player_id", BigInteger, nullable=False),
    Column("season_year", Integer, nullable=False),
    Column("week_no", Integer, nullable=False),
    Column("training_date", Date, nullable=False),
    Column("coach_id", BigInteger, nullable=False),
    Column("technical_items", JSONB, nullable=False, server_default="[]"),
    Column("physical_items", JSONB, nullable=False, server_default="[]"),
    Column("matches", JSONB, nullable=False, server_default="[]"),
    Column("summary", Text),
    Column("created_at", DateTime(timezone=True), server_default=func.now()),
    Column("updated_at", DateTime(timezone=True), server_default=func.now()),
)

fitness_tests = Table(
    "fitness_tests", metadata,
    Column("id", BigInteger, primary_key=True),
    Column("player_id", BigInteger, nullable=False),
    Column("season_year", Integer, nullable=False),
    Column("test_date", Date, nullable=False),
    Column("week_no", Integer),
    Column("coach_id", BigInteger, nullable=False),
    Column("metrics", JSONB, nullable=False),
    Column("total_score", Numeric(6, 2)),
    Column("created_at", DateTime(timezone=True), server_default=func.now()),
    Column("updated_at", DateTime(timezone=True), server_default=func.now()),
)

monthly_comments = Table(
    "monthly_comments", metadata,
    Column("id", BigInteger, primary_key=True),
    Column("player_id", BigInteger, nullable=False),
    Column("season_year", Integer, nullable=False),
    Column("month", Integer, nullable=False),
    Column("content", Text, nullable=False, server_default=""),
    Column("coach_id", BigInteger, nullable=False),
    Column("version", Integer, nullable=False, server_default="1"),
    Column("created_at", DateTime(timezone=True), server_default=func.now()),
    Column("updated_at", DateTime(timezone=True), server_default=func.now()),
)

comment_versions = Table(
    "comment_versions", metadata,
    Column("id", BigInteger, primary_key=True),
    Column("comment_id", BigInteger, nullable=False),
    Column("player_id", BigInteger, nullable=False),
    Column("season_year", Integer, nullable=False),
    Column("month", Integer, nullable=False),
    Column("content", Text, nullable=False),
    Column("coach_id", BigInteger, nullable=False),
    Column("version", Integer, nullable=False),
    Column("edited_at", DateTime(timezone=True), server_default=func.now()),
)

promotion_suggestions = Table(
    "promotion_suggestions", metadata,
    Column("id", BigInteger, primary_key=True),
    Column("player_id", BigInteger, nullable=False),
    Column("season_year", Integer, nullable=False),
    Column("quarter", Integer, nullable=False),
    Column("total_score", Numeric(6, 2), nullable=False),
    Column("rank_in_group", Integer),
    Column("cohort_size", Integer),
    Column("percentile", Numeric(5, 2)),
    Column("recommended", Boolean, nullable=False, server_default="false"),
    Column("target_group", String(32)),
    Column("status", promo_enum, nullable=False, server_default="suggested"),
    Column("coach_id", BigInteger),
    Column("coach_note", Text),
    Column("generated_at", DateTime(timezone=True), server_default=func.now()),
    Column("confirmed_at", DateTime(timezone=True)),
    CheckConstraint("quarter BETWEEN 1 AND 4", name="ps_quarter_chk"),
)
