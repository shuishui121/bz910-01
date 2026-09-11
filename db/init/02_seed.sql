-- =============================================================================
-- 种子数据:账号 / 学员 / 负责关系 / 体测指标与常模
-- 口令经 pgcrypto crypt() 以 bcrypt 落库,后端 passlib 可直接校验。
-- =============================================================================

-- 账号(口令见括号,演示环境用,生产请修改)
INSERT INTO users (username, password_hash, full_name, role, phone) VALUES
  ('admin',      crypt('admin123',  gen_salt('bf')), '系统管理员', 'admin',  NULL),
  ('coach_li',   crypt('coach123',  gen_salt('bf')), '李教练',     'coach',  '13800000001'),
  ('coach_wang', crypt('coach123',  gen_salt('bf')), '王教练',     'coach',  '13800000002'),
  ('parent_ming',crypt('parent123', gen_salt('bf')), '明明爸爸',   'parent', '13900000001')
ON CONFLICT (username) DO NOTHING;

-- 学员
INSERT INTO players (name, gender, birth_date, group_name, joined_year) VALUES
  ('张明明', 'male',   DATE '2015-03-12', '启蒙组', 2024),
  ('赵小蕾', 'female', DATE '2014-07-05', '提高组', 2023)
ON CONFLICT DO NOTHING;

-- 教练负责关系(两名教练同时负责张明明 -> 触发并发评语编辑场景)
INSERT INTO coach_assignments (coach_id, player_id, season_year, is_lead)
SELECT u.id, p.id, 2026, (u.username = 'coach_li')
FROM users u
JOIN players p ON (u.username, p.name) IN (
  ('coach_li',   '张明明'),
  ('coach_wang', '张明明'),
  ('coach_li',   '赵小蕾'))
ON CONFLICT DO NOTHING;

-- 家长绑定(明明爸爸只能看张明明)
INSERT INTO parent_links (parent_id, player_id, relationship)
SELECT u.id, p.id, 'father'
FROM users u, players p
WHERE u.username = 'parent_ming' AND p.name = '张明明'
ON CONFLICT DO NOTHING;

-- 体测指标目录
INSERT INTO fitness_metrics (code, name, unit, direction, sort_order) VALUES
  ('run_50m',        '50米跑',       '秒', 'lower_better',  1),
  ('endurance_run',  '耐力跑(800米)','秒', 'lower_better',  2),
  ('jump_long',      '立定跳远',     '厘米','higher_better', 3),
  ('sit_reach',      '坐位体前屈',   '厘米','higher_better', 4),
  ('sit_ups',        '1分钟仰卧起坐','个', 'higher_better',  5),
  ('rope_skip',      '1分钟跳绳',    '个', 'higher_better',  6),
  ('grip',           '握力',         '千克','higher_better', 7),
  ('shuttle_run',    '10米×4往返跑', '秒', 'lower_better',  8)
ON CONFLICT (code) DO NOTHING;

-- 常模:男女通用,按年龄线性给出均值(base + delta*(age-8))与标准差。
-- 数值为演示用近似常模,可由管理员后台按实测数据替换。
INSERT INTO fitness_norms (metric_id, age, gender, mean, stddev)
SELECT m.id,
       a.age,
       NULL,
       ROUND((p.base + p.delta * (a.age - 8))::numeric, 2),
       p.sd
FROM fitness_metrics m
JOIN LATERAL (VALUES
  ('run_50m',       11.20, -0.35, 0.70),
  ('endurance_run', 300.0, -9.0,  22.0),
  ('jump_long',     125.0,  7.5,  14.0),
  ('sit_reach',      8.0,   0.6,   3.2),
  ('sit_ups',       28.0,   2.2,   6.0),
  ('rope_skip',     95.0,   8.0,  18.0),
  ('grip',          12.5,   1.3,   2.8),
  ('shuttle_run',   14.10, -0.28, 0.85)
) AS p(code, base, delta, sd) ON p.code = m.code
CROSS JOIN LATERAL generate_series(8, 14) AS a(age)
ON CONFLICT (metric_id, age, gender) DO NOTHING;
