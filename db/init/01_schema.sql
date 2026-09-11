-- =============================================================================
-- 省队青训营 · 训练档案平台 —— PostgreSQL 表结构
-- 设计要点:
--   1. 用户(教练/家长/管理员)统一存 users,以 role 区分;
--   2. 业务数据表(周训练 / 体测 / 月度评语 / 升组建议)均带 season_year,
--      并按 RANGE(season_year) 声明式分区 —— 历史年份可直接 DETACH 分区归档;
--   3. 月度评语带 version 乐观锁版本号,全量历史落 comment_versions;
--   4. 体测原始值与标准分分离:fitness_tests.metrics 存原始值,
--      标准分由 fitness_norms 常模(均值/标准差)实时换算后返回并落曲线。
-- =============================================================================

CREATE EXTENSION IF NOT EXISTS pgcrypto;

-- ---------------------------------------------------------------------- 枚举
DO $$ BEGIN
  CREATE TYPE user_role AS ENUM ('coach', 'parent', 'admin');
EXCEPTION WHEN duplicate_object THEN NULL; END $$;

DO $$ BEGIN
  CREATE TYPE gender_type AS ENUM ('male', 'female');
EXCEPTION WHEN duplicate_object THEN NULL; END $$;

DO $$ BEGIN
  CREATE TYPE metric_direction AS ENUM ('higher_better', 'lower_better');
EXCEPTION WHEN duplicate_object THEN NULL; END $$;

DO $$ BEGIN
  CREATE TYPE promotion_status AS ENUM ('suggested', 'confirmed', 'adjusted', 'rejected');
EXCEPTION WHEN duplicate_object THEN NULL; END $$;

DO $$ BEGIN
  CREATE TYPE player_status AS ENUM ('active', 'promoted', 'left');
EXCEPTION WHEN duplicate_object THEN NULL; END $$;

-- ------------------------------------------------------------- 通用 updated_at
CREATE OR REPLACE FUNCTION set_updated_at() RETURNS trigger AS $$
BEGIN
  NEW.updated_at = now();
  RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- ====================================================================== 账号
CREATE TABLE IF NOT EXISTS users (
    id            BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    username      VARCHAR(64)  NOT NULL UNIQUE,
    password_hash VARCHAR(255) NOT NULL,
    full_name     VARCHAR(64)  NOT NULL,
    role          user_role    NOT NULL,
    phone         VARCHAR(32),
    is_active     BOOLEAN      NOT NULL DEFAULT TRUE,
    created_at    TIMESTAMPTZ  NOT NULL DEFAULT now()
);

-- ====================================================================== 学员
CREATE TABLE IF NOT EXISTS players (
    id          BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    name        VARCHAR(64)   NOT NULL,
    gender      gender_type   NOT NULL,
    birth_date  DATE          NOT NULL,
    group_name  VARCHAR(32)   NOT NULL DEFAULT '启蒙组',   -- 当前训练组
    joined_year INTEGER       NOT NULL,                   -- 入队年份
    status      player_status NOT NULL DEFAULT 'active',
    created_at  TIMESTAMPTZ   NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS idx_players_group ON players(group_name, status);

-- ----------------------------------------------------------- 教练-学员 负责关系
-- 多对多:同一学员可由多名教练带训(故存在"两人同时编辑评语"场景)。
-- 责任关系按赛季(年份)维护,跨年度留痕。
CREATE TABLE IF NOT EXISTS coach_assignments (
    id          BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    coach_id    BIGINT NOT NULL REFERENCES users(id)   ON DELETE CASCADE,
    player_id   BIGINT NOT NULL REFERENCES players(id) ON DELETE CASCADE,
    season_year INTEGER NOT NULL,
    is_lead     BOOLEAN NOT NULL DEFAULT FALSE,        -- 是否主教练
    created_at  TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE (coach_id, player_id, season_year)
);
CREATE INDEX IF NOT EXISTS idx_ca_player ON coach_assignments(player_id, season_year);

-- ------------------------------------------------------------- 家长-孩子 绑定
CREATE TABLE IF NOT EXISTS parent_links (
    id           BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    parent_id    BIGINT NOT NULL REFERENCES users(id)   ON DELETE CASCADE,
    player_id    BIGINT NOT NULL REFERENCES players(id) ON DELETE CASCADE,
    relationship VARCHAR(16) NOT NULL DEFAULT 'parent', -- father/mother/...
    verified     BOOLEAN NOT NULL DEFAULT TRUE,
    created_at   TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE (parent_id, player_id)
);
CREATE INDEX IF NOT EXISTS idx_pl_player ON parent_links(player_id);

-- ================================================================= 体测指标目录
CREATE TABLE IF NOT EXISTS fitness_metrics (
    id         BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    code       VARCHAR(32) NOT NULL UNIQUE,   -- run_50m / jump_long / sit_reach ...
    name       VARCHAR(64) NOT NULL,          -- 50米跑
    unit       VARCHAR(16) NOT NULL DEFAULT '',
    direction  metric_direction NOT NULL,     -- 计时类成绩越小越好
    sort_order INTEGER NOT NULL DEFAULT 0
);

-- 标准分常模:按 指标 × 年龄 × 性别 给出均值与标准差,标准分 T = 50 + 10z
CREATE TABLE IF NOT EXISTS fitness_norms (
    id        BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    metric_id BIGINT NOT NULL REFERENCES fitness_metrics(id) ON DELETE CASCADE,
    age       INTEGER NOT NULL,              -- 8..14
    gender    gender_type,                   -- NULL 表示男女通用
    mean      NUMERIC(8,2) NOT NULL,
    stddev    NUMERIC(8,2) NOT NULL CHECK (stddev > 0),
    UNIQUE (metric_id, age, gender)
);

-- ===================================================================== 分区父表
-- 四张业务表统一按赛季年份 RANGE 分区,便于年度归档。

-- --------------------------------------------------------- 每周训练内容
CREATE TABLE IF NOT EXISTS training_weeks (
    id             BIGINT GENERATED ALWAYS AS IDENTITY,
    player_id      BIGINT NOT NULL REFERENCES players(id),
    season_year    INTEGER NOT NULL,
    week_no        INTEGER NOT NULL CHECK (week_no BETWEEN 1 AND 53),
    training_date  DATE NOT NULL,                       -- 该周周一
    coach_id       BIGINT NOT NULL REFERENCES users(id),
    technical_items JSONB NOT NULL DEFAULT '[]'::jsonb, -- [{name,sets,reps,note}]
    physical_items  JSONB NOT NULL DEFAULT '[]'::jsonb, -- [{name,distance/load,sets,note}]
    matches         JSONB NOT NULL DEFAULT '[]'::jsonb, -- [{name,score,result,note}]
    summary        TEXT,
    created_at     TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at     TIMESTAMPTZ NOT NULL DEFAULT now(),
    PRIMARY KEY (id, season_year),
    UNIQUE (player_id, season_year, week_no)
) PARTITION BY RANGE (season_year);

CREATE INDEX IF NOT EXISTS idx_tw_player ON training_weeks(player_id, season_year, week_no);
CREATE TRIGGER trg_tw_updated BEFORE UPDATE ON training_weeks
  FOR EACH ROW EXECUTE FUNCTION set_updated_at();

-- --------------------------------------------------------------- 体测记录
CREATE TABLE IF NOT EXISTS fitness_tests (
    id          BIGINT GENERATED ALWAYS AS IDENTITY,
    player_id   BIGINT NOT NULL REFERENCES players(id),
    season_year INTEGER NOT NULL,
    test_date   DATE NOT NULL,
    week_no     INTEGER CHECK (week_no BETWEEN 1 AND 53),
    coach_id    BIGINT NOT NULL REFERENCES users(id),
    metrics     JSONB NOT NULL,                 -- {"run_50m": 8.9, "jump_long": 165, ...}
    total_score NUMERIC(6,2),                   -- 各指标标准分均值(体测总分)
    created_at  TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at  TIMESTAMPTZ NOT NULL DEFAULT now(),
    PRIMARY KEY (id, season_year)
) PARTITION BY RANGE (season_year);

CREATE INDEX IF NOT EXISTS idx_ft_player ON fitness_tests(player_id, season_year, test_date);
CREATE TRIGGER trg_ft_updated BEFORE UPDATE ON fitness_tests
  FOR EACH ROW EXECUTE FUNCTION set_updated_at();

-- --------------------------------------------------------------- 月度评语(乐观锁)
CREATE TABLE IF NOT EXISTS monthly_comments (
    id          BIGINT GENERATED ALWAYS AS IDENTITY,
    player_id   BIGINT NOT NULL REFERENCES players(id),
    season_year INTEGER NOT NULL,
    month       INTEGER NOT NULL CHECK (month BETWEEN 1 AND 12),
    content     TEXT NOT NULL DEFAULT '',
    coach_id    BIGINT NOT NULL REFERENCES users(id), -- 最后提交教练
    version     INTEGER NOT NULL DEFAULT 1,           -- 乐观锁版本号
    created_at  TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at  TIMESTAMPTZ NOT NULL DEFAULT now(),
    PRIMARY KEY (id, season_year),
    UNIQUE (player_id, season_year, month)
) PARTITION BY RANGE (season_year);

CREATE TRIGGER trg_mc_updated BEFORE UPDATE ON monthly_comments
  FOR EACH ROW EXECUTE FUNCTION set_updated_at();

-- 评语历史版本(审计链,常规表长期保留)
CREATE TABLE IF NOT EXISTS comment_versions (
    id          BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    comment_id  BIGINT NOT NULL,
    player_id   BIGINT NOT NULL REFERENCES players(id),
    season_year INTEGER NOT NULL,
    month       INTEGER NOT NULL,
    content     TEXT NOT NULL,
    coach_id    BIGINT NOT NULL REFERENCES users(id),
    version     INTEGER NOT NULL,
    edited_at   TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS idx_cv_comment ON comment_versions(comment_id);
CREATE INDEX IF NOT EXISTS idx_cv_player  ON comment_versions(player_id, season_year, month);

-- --------------------------------------------------------------- 季度升组建议
CREATE TABLE IF NOT EXISTS promotion_suggestions (
    id             BIGINT GENERATED ALWAYS AS IDENTITY,
    player_id      BIGINT NOT NULL REFERENCES players(id),
    season_year    INTEGER NOT NULL,
    quarter        INTEGER NOT NULL CHECK (quarter BETWEEN 1 AND 4),
    total_score    NUMERIC(6,2) NOT NULL,   -- 季末体测总分(标准分均分)
    rank_in_group  INTEGER,
    cohort_size    INTEGER,
    percentile     NUMERIC(5,2),            -- 百分位,>=70 即前 30%
    recommended    BOOLEAN NOT NULL DEFAULT FALSE, -- 系统推荐升组
    target_group   VARCHAR(32),
    status         promotion_status NOT NULL DEFAULT 'suggested',
    coach_id       BIGINT REFERENCES users(id),     -- 确认/修改的教练
    coach_note     TEXT,
    generated_at   TIMESTAMPTZ NOT NULL DEFAULT now(),
    confirmed_at   TIMESTAMPTZ,
    PRIMARY KEY (id, season_year),
    UNIQUE (player_id, season_year, quarter)
) PARTITION BY RANGE (season_year);

CREATE INDEX IF NOT EXISTS idx_ps_quarter
  ON promotion_suggestions(season_year, quarter, status);

-- ========================================================= 年度分区自动建表函数
CREATE OR REPLACE FUNCTION create_season_partitions(p_start INTEGER, p_end INTEGER)
RETURNS INTEGER AS $$
DECLARE
  y INTEGER;
  n INTEGER := 0;
  tbl TEXT;
  parents TEXT[] := ARRAY[
      'training_weeks','fitness_tests','monthly_comments','promotion_suggestions'];
BEGIN
  FOREACH tbl IN ARRAY parents LOOP
    y := p_start;
    WHILE y <= p_end LOOP
      EXECUTE format(
        'CREATE TABLE IF NOT EXISTS %I PARTITION OF %I FOR VALUES FROM (%s) TO (%s)',
        tbl || '_y' || y, tbl, y, y + 1);
      n := n + 1;
      y := y + 1;
    END LOOP;
    EXECUTE format(
      'CREATE TABLE IF NOT EXISTS %I PARTITION OF %I DEFAULT',
      tbl || '_default', tbl);
  END LOOP;
  RETURN n;
END;
$$ LANGUAGE plpgsql;

-- 预置 2023-2030 赛季分区 + default 兜底
SELECT create_season_partitions(2023, 2030);

-- ========================================================= 年度归档:摘除旧赛季分区
-- 摘除后该分区成为独立表(<name>_yYYYY),可转储到冷存储或备份后 DROP;
-- 需要回查时执行: ALTER TABLE <parent> ATTACH PARTITION ... FOR VALUES FROM (y) TO (y+1);
CREATE OR REPLACE FUNCTION archive_season(p_year INTEGER)
RETURNS TABLE(parent_name TEXT, archived_table TEXT, rows_archived BIGINT) AS $$
DECLARE
  tbl TEXT;
  parents TEXT[] := ARRAY[
      'training_weeks','fitness_tests','monthly_comments','promotion_suggestions'];
  cnt BIGINT;
BEGIN
  FOREACH tbl IN ARRAY parents LOOP
    EXECUTE format('SELECT count(*) FROM %I', tbl || '_y' || p_year) INTO cnt;
    EXECUTE format('ALTER TABLE %I DETACH PARTITION %I',
                   tbl, tbl || '_y' || p_year);
    parent_name := tbl;
    archived_table := tbl || '_y' || p_year;
    rows_archived := cnt;
    RETURN NEXT;
  END LOOP;
END;
$$ LANGUAGE plpgsql;
