# 盯盘助手 (A-Share Stock Monitor)

个人A股智能监控工具。通过 AKShare 采集实时行情与资讯，支持目标价/涨跌停/量能异动等多种预警，触发后自动推送至微信（PushPlus）。内置 AI 分析（Claude/DeepSeek 多模型），支持自然语言选股、板块轮动预测、大资金监控。Vue 3 移动端 UI，手机随时查看。

## Features

- **自选股管理** — 添加/删除自选股，实时行情展示（价格、涨跌幅、成交量）
- **智能预警推送** — 目标价、涨停、跌停、量能异动四种预警类型，触发后推送至微信
  - 目标价预警：一次性触发（one-shot），触发后自动关闭
  - 涨停/跌停/量能异动：每日预警，每天最多触发一次，09:30 自动重置
  - 边沿触发机制 + 30分钟冷却去重，避免重复打扰
- **AI 一键分析** — 汇总行情、财务、资讯数据，调用 AI 生成公司分析要点
- **AI 智能选股** — 用中文描述选股条件（如"市盈率低于15的蓝筹股"），AI 自动解析并筛选
- **板块轮动预测** — AI 分析板块表现与资金流向，预测下一轮热门板块及龙头股
- **大资金监控** — 每5分钟扫描全市场资金流向，净流入超5000万或排名前1%时推送提醒
- **资讯快报** — 盘中每5分钟检查个股新闻，去重后推送重要资讯
- **收盘日报** — 每日15:05自动推送自选股收盘行情汇总
- **系统健康检查** — 每日09:00检测 AKShare 连通性、PushPlus Token 状态、数据新鲜度
- **演示模式** — `DATA_MODE=mock` 使用内置模拟数据，无需 AKShare 连接，方便海外开发调试
- **多 AI 模型支持** — 支持 Claude、DeepSeek、OpenAI、Qwen 四种模型，可按任务类型分别配置
- **移动端优先** — Vue 3 + Vant 4 SPA，适配手机浏览器

## Tech Stack

| 层级 | 技术 |
|------|------|
| 后端 | Python 3.11+, FastAPI, APScheduler, aiosqlite |
| 数据 | AKShare（同花顺接口） |
| AI | Claude (Anthropic SDK), DeepSeek, OpenAI, Qwen (OpenAI-compatible) |
| 推送 | PushPlus（微信推送，每日上限180条） |
| 前端 | Vue 3 + Vite + Vant 4（移动端 SPA） |
| 数据库 | SQLite (WAL mode, aiosqlite) |
| 部署 | Docker / uvicorn（单 worker） |

## UI Overview

移动端优先设计，包含以下页面：

- **首页 (Home)** — 自选股列表，实时行情卡片，快速添加/删除股票
- **个股详情 (StockDetail)** — 行情详情、K线、财务数据、AI分析入口
- **预警管理 (Alerts)** — 创建/编辑/删除预警规则，查看触发记录
- **智能选股 (Screener)** — 自然语言输入选股条件，或使用预设筛选（低估值蓝筹/近期强势/高股息）
- **板块轮动 (Sectors)** — 板块轮动预测、大资金流入排行
- **设置 (Settings)** — PushPlus Token 配置、推送测试、推送配额查看

## Quick Start

### 1. 克隆项目

```bash
git clone <repo-url>
cd my-idea
```

### 2. 安装后端依赖

```bash
uv sync
```

### 3. 安装前端依赖

```bash
cd frontend
npm install
cd ..
```

### 4. 配置环境变量

```bash
cp .env.example .env
```

编辑 `.env`，填入必要的 Token 和 API Key（详见下方「配置说明」）。

### 5. 启动后端

```bash
# 演示模式（无需 AKShare 连接）
DATA_MODE=mock uv run uvicorn app.main:app --host 0.0.0.0 --port 8000

# 生产模式（需要中国大陆 IP）
DATA_MODE=live uv run uvicorn app.main:app --host 0.0.0.0 --port 8000
```

### 6. 启动前端

```bash
cd frontend
npx vite
```

前端默认运行在 `http://localhost:5173`，后端 API 在 `http://localhost:8000`。

## Configuration

`.env` 文件配置说明：

| 变量 | 说明 | 默认值 |
|------|------|--------|
| `DATA_MODE` | `mock` 使用模拟数据，`live` 使用 AKShare 实时数据 | `live` |
| `PUSHPLUS_TOKEN` | PushPlus 推送 Token（在 pushplus.plus 注册获取） | 空 |
| `DEEPSEEK_API_KEY` | DeepSeek API 密钥 | 空 |
| `CLAUDE_API_KEY` | Claude / Anthropic API 密钥 | 空 |
| `AI_PROVIDER_ANALYSIS` | 深度分析使用的 AI 模型 (claude/deepseek/openai/qwen) | `claude` |
| `AI_PROVIDER_SCREENING` | 选股筛选使用的 AI 模型 | `deepseek` |
| `DATABASE_URL` | SQLite 数据库路径 | `sqlite+aiosqlite:///data/stock_monitor.db` |
| `LOG_LEVEL` | 日志级别 (DEBUG/INFO/WARNING/ERROR) | `INFO` |
| `TIMEZONE` | 时区（调度和展示用） | `Asia/Shanghai` |

## Deployment

### 服务器选择

- 服务器可以部署在美国等海外地区（无需 ICP 备案），用户从中国访问
- 但 **AKShare 数据源仅在中国大陆 IP 可用**
  - 海外服务器开发调试：使用 `DATA_MODE=mock`
  - 生产环境：部署在中国大陆 VPS，使用 `DATA_MODE=live`

### Docker 部署

```bash
# 单 worker 运行（APScheduler 约束，不可多 worker）
uvicorn app.main:app --host 0.0.0.0 --port 8000 --workers 1
```

### 注意事项

- **必须使用单个 uvicorn worker**：APScheduler 在每个 worker 中独立运行，多 worker 会导致定时任务重复执行
- SQLite 使用 WAL 模式，支持并发读取
- PushPlus 每日推送上限 180 条，系统在 150 条时发出警告，180 条时硬停止

## Architecture

```
┌─────────────┐     ┌──────────────────────────────────┐
│  Vue 3 SPA  │────>│  FastAPI Backend                 │
│  (Vant 4)   │     │                                  │
└─────────────┘     │  ┌─────────┐  ┌──────────────┐  │
                    │  │ Routers │  │  APScheduler  │  │
                    │  └────┬────┘  └──────┬───────┘  │
                    │       │              │           │
                    │  ┌────┴──────────────┴────────┐  │
                    │  │        Services            │  │
                    │  │  alerting / ai / screener  │  │
                    │  │  push / capital_flow       │  │
                    │  │  sector_rotation / cache   │  │
                    │  └────────────┬───────────────┘  │
                    │              │                   │
                    │  ┌───────────┴────────────────┐  │
                    │  │   Data Providers           │  │
                    │  │   AKShare / Mock / Demo    │  │
                    │  └───────────────────────────-┘  │
                    └──────────────────────────────────┘
                              │            │
                    ┌─────────┴──┐  ┌──────┴───────┐
                    │  SQLite DB │  │  PushPlus    │
                    │  (WAL)     │  │  (微信推送)   │
                    └────────────┘  └──────────────┘
```

**定时任务一览：**

| 任务 | 时间 | 说明 |
|------|------|------|
| 行情轮询 + 预警 | 盘中每分钟 | 9:30-11:30, 13:00-15:00 |
| 资讯检查 | 盘中每5分钟 | 去重推送个股新闻 |
| 大资金监控 | 盘中每5分钟 | 净流入异常时推送 |
| 收盘日报 | 15:05 | 自选股收盘行情汇总 |
| 日报预警重置 | 09:30 | 重置每日预警触发状态 |
| 板块轮动刷新 | 09:00 | AI 预测板块轮动 |
| 系统健康检查 | 09:00 | AKShare/PushPlus 连通性检测 |
| 交易日历刷新 | 06:00 | 加载最新交易日历 |

## PushPlus 微信推送设置指南

PushPlus 是一个免费的微信消息推送服务，用于将预警信息推送到你的微信。

### 注册步骤

1. 打开微信，搜索公众号 **「pushplus推送加」**，关注该公众号
2. 在公众号菜单中点击「功能」->「开始使用」
3. 用微信扫码登录 pushplus.plus 网站
4. 登录后在首页可以看到你的 **Token**（一串字母数字）
5. 复制这个 Token，填入 `.env` 文件的 `PUSHPLUS_TOKEN=` 后面
6. 启动系统后，在「设置」页面点击「测试推送」，确认微信能收到消息

### 注意事项

- PushPlus 免费版每天可推送 200 条消息，本系统限制为 180 条以留出安全余量
- 如果收不到消息，请确认是否关注了 pushplus 公众号
- Token 请妥善保管，不要分享给他人

## Disclaimer

本工具为个人学习和研究用途。

**数据仅供参考，不构成任何投资建议。** 股市有风险，投资需谨慎。作者不对因使用本工具产生的任何投资损失承担责任。
