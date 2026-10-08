# AI 面试备考助手

PAYATHON 2026 黑客松参赛作品（赛道：Vibe Pay）。面向所有求职者的 AI 模拟面试备考工具：自由选择任意岗位，系统按「题库优先 + AI 兜底」出题，用户在线作答，AI 按四维度评分并给出「是否录取」判定与提升建议。

## 功能一览

- **岗位画像定制**：岗位自由输入 + 常见岗位快捷选择（会计 / HR / 前台 / 销售 / 技术开发 / 运营），可选填职责描述、期望薪资档、工作年限。
- **智能出题**：题库优先，命中则从预设题库抽取；无预设则大模型即时生成，并在显眼处标注「该岗位暂无预设题库，以下题目由 AI 为您即时生成」。每题带来源标识（「来自预设题库」/「AI 即时生成」）。
- **模拟答题**：文字作答，支持追问式多轮问答。
- **评分判定**：四维度评分卡（沟通表达 / 岗位专业匹配 / 经验匹配 / 应变能力，各 1-5 分）+ 总分（1-20）+ 录取概率（百分比）+ 改进建议。
- **题库与 AI 解析**：预设题库覆盖 6 个常见岗位，附解析；订阅用户可解锁 AI 深度解析。
- **练习记录**：记录每次成绩、题目来源与薄弱维度，形成成长曲线。
- **免费/订阅**：免费用户每日 3 次模拟、简化评分；订阅用户无限次 + 完整题库 + AI 深度解析。支付为 Vibe Pay 占位，含测试开关。

## 技术栈

- 后端：Python + FastAPI，SQLite（标准库 `sqlite3`）
- 前端：纯 HTML/CSS/JS 单页应用，支持 Web 与 H5 移动端
- 大模型：通过环境变量读取 Anthropic 兼容接口（`ANTHROPIC_BASE_URL` / `ANTHROPIC_AUTH_TOKEN` / `ANTHROPIC_MODEL`）
- 认证：邮箱 + 密码（PBKDF2 加盐哈希）+ 会话 token
- 支付：Vibe Pay 占位接口（`/api/pay/*`），真实接入后续替换

## 快速开始

### 1. 配置环境变量

复制 `.env.example` 为 `.env`，填入真实值：

```bash
# Windows (PowerShell)
Copy-Item .env.example .env
```

编辑 `.env`，填上你的 API Key：

```
ANTHROPIC_BASE_URL=https://api.deepseek.com/anthropic
ANTHROPIC_AUTH_TOKEN=你的_API_Key
ANTHROPIC_MODEL=deepseek-v4-pro
```

> 密钥只能放在环境变量或 `.env`（已被 `.gitignore` 忽略），绝不要写进代码或提交到仓库。

### 2. 安装依赖

项目已自带 `.venv` 虚拟环境（Python 3.14），激活后安装：

```powershell
# 激活虚拟环境
.\.venv\Scripts\Activate.ps1
# 安装依赖
pip install -r requirements.txt
```

### 3. 启动服务

```powershell
uvicorn app.main:app --reload --port 8000
```

浏览器打开 <http://127.0.0.1:8000> 即可使用。接口文档见 <http://127.0.0.1:8000/docs>。

> 若 PowerShell 报「禁止运行脚本」，先执行 `Set-ExecutionPolicy -Scope Process RemoteSigned`。

## 项目结构

```
heikesong/
├── app/
│   ├── main.py            # 应用入口：初始化数据库、挂载路由与静态前端
│   ├── config.py          # 环境变量 / .env 读取（密钥不硬编码）
│   ├── database.py        # SQLite 连接、建表、题库种子导入
│   ├── security.py        # 密码哈希 + 会话 token
│   ├── deps.py            # 依赖：当前用户 / 订阅状态 / 免费额度
│   ├── models.py          # Pydantic 请求模型
│   ├── llm.py             # 大模型调用 + JSON 容错解析
│   ├── question_bank.py   # 题库优先 + AI 兜底出题
│   ├── scoring.py         # 评分卡组装 + 薄弱维度
│   └── routers/           # auth / interview / bank / records / pay
├── data/
│   └── question_bank_seed.json   # 预设题库（首次启动自动导入）
├── static/                # 前端单页应用
├── requirements.txt
├── .env.example
└── README.md
```

## 主要接口

| 方法 | 路径 | 说明 |
|---|---|---|
| POST | `/api/auth/register` | 注册 |
| POST | `/api/auth/login` | 登录 |
| POST | `/api/interview/generate` | 出题（题库/AI 兜底，返回每题来源） |
| POST | `/api/interview/followup` | 追问式多轮问答 |
| POST | `/api/interview/score` | 评分卡 + 落库练习记录 |
| GET | `/api/bank/positions` | 已有题库的岗位 |
| GET | `/api/bank?position=xx` | 题库浏览（解析为订阅内容） |
| POST | `/api/bank/analysis` | AI 深度解析（订阅专属） |
| GET | `/api/records` | 练习记录 |
| GET | `/api/records/growth` | 成长曲线数据 |
| POST | `/api/pay/create-order` | Vibe Pay 下单占位 |
| POST | `/api/pay/test-activate` | 测试：一键开通订阅 |

## 免责声明

AI 评分结果仅供模拟练习参考，**不代表真实录取结果**。
