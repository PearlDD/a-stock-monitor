# 盯盘助手 · A-Share Stock Monitor

面向个人投资者的 A 股与常见美股自选股、价格提醒 Web 应用。用户通过邮箱注册登录，设置目标价、涨停、跌停或换手率提醒；后台在对应市场交易时段轮询腾讯财经行情，达到规则后使用该用户自己的 PushPlus Token 发送微信通知。行情存在延迟，所有数据仅供参考，不构成投资建议。

## 已有功能

- Supabase Auth 邮箱注册、登录与会话恢复。
- 每个用户独立的自选股、提醒规则、发送配额和 PushPlus 设置。
- 目标价一次性提醒；涨跌停及换手率提醒按交易日去重。
- 盘中分钟级行情检查、收盘日报、A 股/美股（如 `AAPL`）搜索、个股行情与资金流展示。
- PushPlus Token 在数据库中以 AES-256-GCM 加密保存；服务端密钥只存在于部署环境。

资讯、公告、真实 K 线和“资金流入”尚未接入可靠的专用数据源；界面会显示空结果或近似指标，不能当作生产级数据功能。

## 架构与数据流

```text
Vue 3 / Vant SPA ──Bearer JWT──> Netlify Functions ──service role──> Supabase PostgreSQL
       │                                      │
       └── Supabase Auth <────────────────────┤
                                              ├── 腾讯财经行情（HTTPS，超时+重试）
                                              └── PushPlus（按用户加密 Token）

Netlify Cron -> poll-quotes -> 校验规则 -> PostgreSQL 原子领取发送权 -> PushPlus
```

`alert_deliveries` 以“规则 + 交易日”唯一约束防止并发定时任务重复发送。定时任务是 at-least-once：外部服务在“已接收消息、但结果未写库”这一极小窗口失败时，仍可能出现一次重复，属于通知系统无法完全消除的边界。

## 技术栈

- 前端：Vue 3、Vite、Vant、Axios、Supabase JS
- 后端：Node.js 22、Netlify Functions
- 数据库与认证：Supabase PostgreSQL / Auth / Row Level Security
- 行情：腾讯财经公开接口（GBK 响应）
- 通知：PushPlus

## 本地启动

前提：Node.js 22+、Supabase 项目、Netlify CLI（用于本地运行 Functions）。

```bash
git clone <your-private-repository-url>
cd a-stock-monitor
npm ci
cp .env.example .env
npx supabase db push       # 或在 Supabase SQL Editor 按顺序执行 migrations
npx netlify dev
```

应用从 Netlify 本地地址打开，而不是单独运行 `npm run dev`，以确保 `/api` Functions 可用。`npm run build` 只验证前端构建。

## 环境变量

将以下变量配置到本地 `.env` 和 Netlify 的环境变量面板；**绝不提交 `.env`、服务角色密钥或加密密钥**。

| 变量 | 用途 | 是否公开 |
| --- | --- | --- |
| `SUPABASE_URL` | Functions 连接 Supabase | 否（服务端） |
| `SUPABASE_SERVICE_ROLE_KEY` | Functions 验证用户与执行定时任务 | 严格保密 |
| `VITE_SUPABASE_URL` | 浏览器连接 Supabase Auth | 可公开 |
| `VITE_SUPABASE_ANON_KEY` | 浏览器匿名公钥 | 可公开（依赖 RLS） |
| `APP_ENCRYPTION_KEY` | base64 编码的 32 字节 AES 密钥 | 严格保密、不可随意轮换 |
| `ALLOWED_ORIGIN` | 正式站点完整来源，如 `https://example.netlify.app` | 否 |

在 Netlify / Supabase 中分别设置好变量后，用户在“设置”页保存自己的 PushPlus Token。不要再使用共享的 `PUSHPLUS_TOKEN`，否则会造成跨用户通知泄露。

## 部署步骤

1. 创建 Supabase 项目，启用 Email/Password 登录，并配置确认邮件重定向 URL 为正式站点。
2. 按顺序执行 `supabase/migrations/001_init.sql` 与 `002_multi_tenant_security.sql`。迁移不会删除旧数据；旧版全局数据的 `user_id` 为 `NULL`，为防泄露不会出现在任何账号中。需要保留时，请在备份后人工归属到正确用户。
3. 在 Netlify 导入仓库，设置上表全部环境变量，Node 版本保持 20，部署。
4. 将 `ALLOWED_ORIGIN` 与最终 Netlify 域名完全一致；在 Supabase Auth 中添加同一站点到允许重定向地址。
5. 创建测试账号，保存测试 PushPlus Token，创建目标价规则并从设置页发送测试通知。
6. 配置外部监控定期请求一个独立的 HTTP 健康端点（当前 `health-check` 是内部定时检查，不能替代公网 health endpoint），并接入 Netlify/Supabase 错误告警。

## 测试与运维检查

```bash
npm ci
npm run build
```

部署前至少验证：未登录 API 返回 401；A 用户无法读取/修改 B 用户数据；无效股票代码和阈值返回 400；行情服务超时可重试；同一规则同一交易日只产生一个 `alert_deliveries` 记录；PushPlus 失败会留下失败记录供后续重试。应把 Netlify Function 日志、Supabase 数据库错误与外部可用性检查接入告警平台，并定期轮换服务角色密钥和加密密钥（轮换加密密钥前须制定数据重加密方案）。

## 已知限制

- 腾讯公开行情接口没有稳定 SLA、限流承诺或完整休市日历；当前实现有单次请求最多 50 股、超时和指数退避，但生产场景建议更换为有授权的数据供应商并使用交易日历。
- Netlify Cron 不是精确实时调度；若运行错过，当前不会自动补齐历史行情。
- 资金流提醒尚未具备用户级规则与去重，已禁止其自动广播，只保留展示/日志能力。
- 尚未配置 Sentry 等错误追踪以及公开 health endpoint；这是下一阶段的上线前必做项。

## 安全说明

服务角色密钥只能由 Functions 使用，绝不可放入 `VITE_*`、浏览器代码、截图或仓库。数据库权限由 RLS 强制执行；Functions 还会校验 Supabase Bearer JWT。请保留 `.gitignore` 对 `.env` 的排除，并在发现密钥泄露时立即在供应商控制台撤销和轮换。
