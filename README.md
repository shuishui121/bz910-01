# 省队青训营 · 训练档案平台

每年 40 名 8–14 岁运动员的训练计划、体测数据与教练评语统一档案平台。
教练录入周训练与月度评语，系统按常模自动换算标准分并生成成长曲线；家长独立账号只读自家孩子；
季末自动产出升组建议（组内体测总分前 30%），教练可修改确认；评语并发编辑带乐观锁冲突提示。

**技术栈**：FastAPI 3.x（async SQLAlchemy + asyncpg） · Vue 3 + Vite + Pinia · PostgreSQL 16（RANGE 分区） · Docker Compose。

## 一键启动

```bash
docker compose up -d --build
```

| 服务 | 地址 |
|---|---|
| 前端页面 | http://localhost:8080 |
| 后端 API | http://localhost:8000/api/v1 |
| Swagger 文档 | http://localhost:8080/docs （或 :8000/docs） |
| 健康检查 | http://localhost:8000/health |

首次启动自动执行 `db/init/01_schema.sql`（建表、2023–2030 分区、归档函数）与 `02_seed.sql`（账号、指标、常模、演示学员）。

演示账号：

| 角色 | 账号 / 密码 | 说明 |
|---|---|---|
| 主教练 | `coach_li` / `coach123` | 张明明（主教）、赵小蕾 |
| 协作教练 | `coach_wang` / `coach123` | 同时负责张明明 —— 用于复现评语并发冲突 |
| 家长 | `parent_ming` / `parent123` | 只能看张明明 |
| 管理员 | `admin` / `admin123` | 全部数据 + 年度归档 |

> 生产部署请修改 `docker-compose.yml` 中的数据库口令与 `JWT_SECRET`。

## 本地开发（不用 Docker）

```bash
# 仅启动数据库
docker run -d --name tdb -p 5432:5432 \
  -e POSTGRES_USER=training -e POSTGRES_PASSWORD=training \
  -e POSTGRES_DB=training_archive \
  -v "$PWD/db/init:/docker-entrypoint-initdb.d:ro" postgres:16-alpine

# 后端
cd backend && python -m venv .venv && . .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
uvicorn app.main:app --reload --port 8000

# 前端
cd frontend && npm install && npm run dev   # http://localhost:5173 ，/api 已代理到 8000
```

## 目录结构

```
.
├── db/init/
│   ├── 01_schema.sql        # 表结构、枚举、分区、归档函数
│   └── 02_seed.sql          # 账号/学员/指标/标准分常模
├── backend/
│   ├── app/
│   │   ├── main.py          # FastAPI 入口、CORS、异常处理、路由注册
│   │   ├── response.py      # 统一 {code,data,message} 与 BizError
│   │   ├── security.py      # bcrypt 口令 + JWT
│   │   ├── deps.py          # 登录依赖 / 角色 / 学员级数据权限
│   │   ├── models.py        # SQLAlchemy Core 表定义
│   │   ├── schemas.py       # Pydantic 模型
│   │   ├── services/scoring.py  # 原始值→标准分 T 换算
│   │   └── routers/         # auth/players/training/fitness/comments/promotions/admin
│   ├── requirements.txt
│   └── Dockerfile
├── frontend/
│   ├── src/
│   │   ├── api/http.js      # axios 实例：自动带 token、统一解包、401/409 处理
│   │   ├── stores/auth.js   # Pinia 登录态
│   │   ├── router.js        # 路由 + 角色守卫
│   │   ├── layouts/AppLayout.vue
│   │   ├── pages/           # 见下方清单
│   │   └── components/      # 见下方清单
│   ├── nginx.conf           # SPA 托管 + /api 反代
│   └── Dockerfile
├── docker-compose.yml
└── docs/API.md              # 完整接口文档（含权限矩阵、冲突协议、归档说明）
```

## Vue 页面与组件清单

| 类型 | 文件 | 职责 |
|---|---|---|
| 页面 | `pages/LoginPage.vue` | 账号密码登录，按角色落地 |
| 页面 | `pages/PlayerListPage.vue` | 教练看负责名单 / 家长只看自家孩子 / 管理员看全部，卡片入口 |
| 页面 | `pages/PlayerDetailPage.vue` | 学员详情，Tab：档案概览、周训练、体测与成长曲线、月度评语；赛季年份切换 |
| 页面 | `pages/PromotionPage.vue` | 季末生成升组建议、前 30% 标识、教练修改确认弹窗 |
| 布局 | `layouts/AppLayout.vue` | 侧边导航、当前用户、退出；家长隐藏「季度升组」 |
| 组件 | `components/TrainingWeekEditor.vue` | 教练录入周训练（技术/体能/对抗赛/小结），按周读取回填、幂等保存 |
| 组件 | `components/TrainingWeekViewer.vue` | 家长只读的周训练时间线 |
| 组件 | `components/ItemEditor.vue` | 技术项/体能项动态行编辑器 |
| 组件 | `components/FitnessPanel.vue` | 体测录入（指标目录动态生成）+ 历次体测表 |
| 组件 | `components/GrowthChart.vue` | **成长曲线**：SVG 折线，横轴周数、纵轴标准分 T；分类色板、十字线 tooltip、图例显隐、表格视图 |
| 组件 | `components/CommentPanel.vue` | 月度评语编辑（携带 base_version）；**409 冲突弹窗**：双方文本对照 → 覆盖 / 手工合并 |
| 基础 | `api/http.js`、`stores/auth.js`、`styles.colors.js`、`styles.css` | 请求封装、登录态、已通过色盲校验的图表色板、全局样式 |

## 关键设计

### 标准分与成长曲线
`fitness_norms` 按 指标×年龄×性别 存均值/标准差（种子数据为 8–14 岁演示常模，可替换为实测常模）。
`z = (x−mean)/stddev`，计时类（越小越好）取 −z，`T = 50 + 10z` 截断 [20,80]；体测总分为各指标 T 分均值。
成长曲线接口 `/fitness/growth-chart` 按测试周对齐每个指标序列，前端折线纵轴固定在统一标准分量纲，避免双轴。

### 评语并发冲突（乐观锁）
`monthly_comments.version` 单调递增，提交必须带读取时的 `base_version`；
不一致（或并发插入撞唯一键）返回 HTTP 409 + 双方内容，前端弹出对照框，后提交教练选择**覆盖**或**手工合并**，
解决后版本号 +1，旧版本全量落 `comment_versions`。另在 `UPDATE ... WHERE version=?` 做原子 CAS 双保险。

### 升组建议
季末取每人季度内最近一次体测总分，按 `group_name` 组内降序，`ceil(人数×30%)` 名 `recommended=true`，
记录排名/人数/百分位与目标组（启蒙组→提高组→精英组）。重复生成不覆盖教练已 `confirmed/adjusted/rejected` 的结论。

### 权限
- 教练：仅 `coach_assignments` 中本人负责的学员可读写；
- 家长：仅 `parent_links` 绑定的孩子，全接口只读，写入返回 `40300`；
- 管理员：全部数据，独占年度归档。
学员级鉴权统一走 `deps.ensure_player_access()`，列表接口同样按关系表过滤，不存在“改 ID 越权”。

### 按年份归档
`training_weeks / fitness_tests / monthly_comments / promotion_suggestions` 均 `PARTITION BY RANGE (season_year)`，
已建 2023–2030 分区与 default 兜底。归档：`POST /api/v1/admin/archive/{year}`（管理员），
四张表的当年分区被 DETACH 成独立表（如 `fitness_tests_y2024`），转储冷存储后即可删除；
回查用 `ATTACH PARTITION` 挂回。审计性质的 `comment_versions` 不分区、长期保留。

## 接口文档
见 [`docs/API.md`](docs/API.md)：全部端点、统一响应码、请求/响应示例、409 冲突协议与权限矩阵；
服务运行时也可直接用 Swagger（`/docs`）在线调试。
