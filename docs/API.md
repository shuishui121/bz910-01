# API 接口文档

省队青训营训练档案平台 · 后端 FastAPI
交互式文档：服务启动后访问 `http://localhost:8000/docs`（或经前端网关 `http://localhost:8080/docs`）。

- 基础路径：`/api/v1`
- 认证方式：请求头 `Authorization: Bearer <token>`（登录接口返回 JWT）
- 角色：`coach` 教练 / `parent` 家长 / `admin` 管理员

## 1. 统一响应结构

所有接口（含错误）均返回：

```json
{ "code": 0, "data": {}, "message": "ok" }
```

| code | 含义 |
|------|------|
| 0 | 成功 |
| 40001 | 业务参数错误 |
| 40100 | 未登录 / 令牌失效 |
| 40300 | 无权限（越权访问他人学员、家长写入等） |
| 40400 | 资源不存在 |
| 40901 | **评语版本冲突**，data 中带回服务端当前版本 |
| 42200 | 请求体校验失败 |
| 50000 | 服务器内部错误 |

## 2. 认证

### POST /auth/login
请求：
```json
{ "username": "coach_li", "password": "coach123" }
```
返回 `data`：
```json
{
  "token": "eyJhbGciOi...",
  "user": { "id": 2, "username": "coach_li", "full_name": "李教练", "role": "coach" }
}
```
演示账号：`coach_li/coach123`、`coach_wang/coach123`、`parent_ming/parent123`、`admin/admin123`。

### GET /auth/me
返回当前登录用户信息。

## 3. 学员

### GET /players
按角色返回可见学员：
- 教练：本人 `coach_assignments` 负责名单（含 `is_lead` 是否主教练）；
- 家长：仅 `parent_links` 绑定的孩子（含 `relationship`）；
- 管理员：全部学员。

`data`：
```json
[
  {
    "id": 1, "name": "张明明", "gender": "male",
    "birth_date": "2015-03-12", "group_name": "启蒙组",
    "joined_year": 2024, "status": "active",
    "is_lead": true
  }
]
```

### GET /players/{player_id}
学员详情。非负责教练 / 非该学员家长 → `40300`。

## 4. 每周训练

查询参数 `season_year`（默认 2026），用于按赛季年份隔离与归档。

### GET /players/{player_id}/training-weeks?season_year=2026
返回该赛季各周训练记录（技术项 / 体能项 / 对抗赛 / 小结），按周次升序。

### PUT /players/{player_id}/training-weeks?season_year=2026
教练录入或更新某周（按 学员+赛季+周次 唯一，重复提交即覆盖）。家长调用 → `40300`。

```json
{
  "week_no": 12,
  "training_date": "2026-03-16",
  "technical_items": [
    { "name": "正手攻球", "sets": 4, "reps": "20个", "note": "注意收拍" }
  ],
  "physical_items": [
    { "name": "间歇跑", "load": "200米×6", "sets": 1, "note": "" }
  ],
  "matches": [
    { "name": "队内循环赛 vs 赵小蕾", "score": "3:1", "result": "胜", "note": "" }
  ],
  "summary": "本周技术稳定性提升,体能后半程略吃力。"
}
```

## 5. 体测与成长曲线

### POST /players/{player_id}/fitness?season_year=2026
录入住测原始值，服务端按 **指标×年龄×性别常模** 自动换算标准分 T：

- `z = (x - mean) / stddev`，成绩越小越好的指标（计时类）取 `-z`；
- `T = 50 + 10z`，截断到 [20, 80]；
- `total_score` = 各指标 T 分均值（体测总分）。

请求：
```json
{ "test_date": "2026-03-20", "week_no": 12, "metrics": { "run_50m": 8.7, "jump_long": 172 } }
```

### GET /players/{player_id}/fitness?season_year=2026
历次体测（日期、周次、总分、原始指标）。

### GET /players/{player_id}/fitness/growth-chart?season_year=2026
**成长曲线图数据**：横轴为训练周数，纵轴为各体测指标标准分。

```json
{
  "weeks": [10, 12],
  "series": [
    {
      "code": "run_50m", "name": "50米跑", "unit": "秒",
      "direction": "lower_better",
      "data": [ { "week": 10, "raw": 8.9, "score": 55.2 },
                { "week": 12, "raw": 8.7, "score": 58.1 } ]
    }
  ],
  "totals": [
    { "week": 10, "test_date": "2026-03-06", "total_score": 54.3 },
    { "week": 12, "test_date": "2026-03-20", "total_score": 57.1 }
  ]
}
```

### GET /metrics
体测指标目录（code、名称、单位、优劣方向），录入表单据此动态生成。

## 6. 月度评语（乐观锁 + 冲突处理）

评语按 学员+赛季+月份 唯一，带 `version` 版本号；每次修改版本 +1，并向 `comment_versions` 写入历史。

### GET /players/{player_id}/comments?season_year=2026
返回各月评语及当前版本号、最后修改教练。

### PUT /players/{player_id}/comments
新建或更新。`base_version` 为编辑时所基于的版本，新建时传 `null`。

```json
{ "season_year": 2026, "month": 3, "content": "本月进步明显……", "base_version": 2 }
```

**并发冲突场景（两位教练同时编辑）：**
若提交时服务端版本已不是 `base_version`，返回 HTTP 409：

```json
{
  "code": 40901,
  "data": {
    "current_version": 3,
    "current_content": "王教练刚提交的内容……",
    "current_coach_name": "王教练",
    "submitted_content": "李教练本次写的内容……"
  },
  "message": "评语已被其他教练修改,请选择覆盖或合并"
}
```

前端弹窗展示双方文本，由后提交者选择：

### POST /players/{player_id}/comments/resolve
```json
{
  "season_year": 2026, "month": 3,
  "content": "李教练本次写的内容……",
  "action": "merge",
  "merged_content": "合并整理后的最终文本……"
}
```
- `action = "overwrite"`：以 `content`（我的版本）直接覆盖；
- `action = "merge"`：以 `merged_content` 落库（教练对照双方文本手工合并）。
两种方式版本号均 +1 并留痕。

### GET /players/{player_id}/comments/{season_year}/{month}/versions
该月评语的历史版本链（版本号、内容、修改教练、时间）。

## 7. 季度升组建议

### POST /promotions/generate?season_year=2026&quarter=1
教练 / 管理员在季末触发：
1. 取每位学员该季度内**最近一次**有总分的体测；
2. 按当前训练组分组、总分降序排名；
3. 组内前 30%（`ceil(组人数 × 0.30)`）置 `recommended=true`，给目标组（启蒙组→提高组→精英组）；
4. 计算组内排名、人数、百分位。

重复生成只刷新仍是 `suggested` 的记录；**教练已确认 / 调整 / 驳回的结论不会被覆盖**。
返回 `data.upserted` 为本次更新条数。

### GET /promotions?season_year=2026&quarter=1
按权限过滤：教练只见负责学员，家长只见自家孩子。
`data[]` 字段：`id, player_id, player_name, group_name, total_score, rank_in_group, cohort_size, percentile, recommended, target_group, status, coach_note, generated_at, confirmed_at`。

`status`：`suggested` 待确认 / `confirmed` 教练已确认 / `adjusted` 教练调整了系统建议 / `rejected` 已驳回。

### PUT /promotions/{id}/confirm?season_year=2026
教练在系统建议基础上修改确认。结论与系统建议一致记 `confirmed`，不一致记 `adjusted`。

```json
{ "recommended": true, "target_group": "提高组", "coach_note": "技术达标,心理稳定性还需观察一个月,同意升组。" }
```

## 8. 年度归档（管理员）

业务表（周训练 / 体测 / 评语 / 升组建议）均按 `season_year` 做 RANGE 分区。

### POST /admin/archive/{year}
仅管理员。执行库函数 `archive_season(year)`，把四张表对应年份的分区 **DETACH** 为独立表
（如 `training_weeks_y2024`），可转储冷存储后删除，实现按年份归档。
为防误操作，接口限制只能归档早于 2025 的历史年份；当前赛季调用返回 `40001`。

```json
{
  "code": 0,
  "data": [
    { "parent_name": "training_weeks", "archived_table": "training_weeks_y2024", "rows_archived": 320 },
    { "parent_name": "fitness_tests",  "archived_table": "fitness_tests_y2024",  "rows_archived": 80 },
    { "parent_name": "monthly_comments","archived_table": "monthly_comments_y2024","rows_archived": 80 },
    { "parent_name": "promotion_suggestions","archived_table": "promotion_suggestions_y2024","rows_archived": 40 }
  ],
  "message": "2024 赛季分区已摘除为独立归档表,可转储冷存储后删除"
}
```
回查归档年份：`ALTER TABLE training_weeks ATTACH PARTITION training_weeks_y2024 FOR VALUES FROM (2024) TO (2025);`

## 9. 健康检查

`GET /health` → `{ "code": 0, "data": { "status": "up" }, "message": "ok" }`（无需认证）。

## 10. 权限矩阵

| 资源 | 教练（负责该学员） | 教练（非负责） | 家长（本人孩子） | 家长（他人孩子） | 管理员 |
|---|---|---|---|---|---|
| 学员列表/详情 | ✅ 仅负责名单 | — | ✅ 仅自家孩子 | ❌ 40300 | ✅ 全部 |
| 周训练 读 | ✅ | ❌ | ✅ | ❌ | ✅ |
| 周训练/体测 写 | ✅ | ❌ | ❌（只读） | ❌ | ✅ |
| 评语 读 | ✅ | ❌ | ✅ | ❌ | ✅ |
| 评语 写（含冲突处理） | ✅ | ❌ | ❌ | ❌ | ✅ |
| 成长曲线 | ✅ | ❌ | ✅ | ❌ | ✅ |
| 升组生成/确认 | ✅（负责范围） | ❌ | ❌ | ❌ | ✅ |
| 年度归档 | ❌ | ❌ | ❌ | ❌ | ✅ |
