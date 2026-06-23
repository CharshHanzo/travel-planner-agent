# Travel Planner Agent

基于 LangGraph 多 Agent 协作的智能旅行规划助手，支持对话式交互、意图识别、偏好学习、实时天气查询、景点/美食搜索和高德地图路线可视化。

---

## 架构设计

```
┌─────────────────────────────────────────────────────────────┐
│                      Frontend (Vue 3)                        │
│  Vue 3 + TypeScript + Vite + Element Plus + Pinia           │
│  SSE 流式通信 | 高德地图可视化 | Markdown 渲染              │
└──────────────────────────────┬──────────────────────────────┘
                               │ SSE / REST API
┌──────────────────────────────┴──────────────────────────────┐
│                    Backend (FastAPI)                          │
│  ChatSupervisor (对话主管)                                    │
│  ├── 意图识别 (weather/activities/food/plan/modify/general) │
│  ├── 上下文管理 (城市/天气/活动/美食/偏好)                  │
│  └── 偏好学习引擎 (LearningEngine)                           │
├─────────────────────────────────────────────────────────────┤
│                  Multi-Agent System (LangGraph)               │
│  ┌──────────────┐ ┌──────────────┐ ┌──────────┐ ┌────────┐ │
│  │ WeatherAgent │ │ActivityAgent │ │ FoodAgent│ │RouteAgent│
│  └──────┬───────┘ └──────┬───────┘ └────┬─────┘ └───┬────┘ │
└─────────┼────────────────┼──────────────┼───────────┼───────┘
          │                │              │           │
┌─────────┴────────────────┴──────────────┴───────────┴───────┐
│                  MCP Tool Server (FastMCP)                    │
│  get_weather      search_activities   search_restaurants     │
│  (OpenWeatherMap)  (Firecrawl Search)  (Firecrawl Search)    │
│                                              plan_route       │
│                                              (高德地图 API)   │
└─────────────────────────────────────────────────────────────┘
```

### 核心流程

```
用户输入 → 意图识别 → 上下文提取(城市/偏好)
                │
    ┌───────────┼───────────────────────────────┐
    ▼           ▼           ▼                   ▼
 weather    activities     food          generate_plan
    │           │           │                   │
    ▼           ▼           ▼           ┌───────┴───────┐
WeatherAgent  ActivityAgent FoodAgent   │ 汇总所有Agent │
    │           │           │           │ 生成Markdown  │
    └───────────┴───────────┘           │ + 坐标JSON    │
                                        └───────────────┘
```

---

## 技术栈

| 层级 | 技术 |
|------|------|
| **前端框架** | Vue 3 + TypeScript + Vite |
| **UI 组件库** | Element Plus |
| **状态管理** | Pinia |
| **后端框架** | FastAPI (Python) |
| **Agent 框架** | LangGraph + LangGraph Supervisor |
| **LLM 集成** | LangChain + langchain-openai |
| **工具协议** | MCP (Model Context Protocol) |
| **大语言模型** | 通义千问 (DashScope) / MiMo-V2.5 (Xiaomi) |
| **地图服务** | 高德地图 API |
| **天气服务** | OpenWeatherMap API |
| **搜索服务** | Firecrawl Search API |
| **前后端通信** | SSE (Server-Sent Events) |

---

## 快速开始

### 1. 环境要求

- Python 3.10+
- Node.js 18+

### 2. 克隆项目

```bash
git clone <repo-url>
cd travel-planner-agent
```

### 3. 配置环境变量

**后端** - 复制 `backend/.env.example` 为 `backend/.env`：

```env
# LLM 提供商 (dashscope 或 xiaomi)
LLM_PROVIDER=xiaomi

# 通义千问配置
DASHSCOPE_API_KEY=your_dashscope_api_key
DASHSCOPE_BASE_URL=https://dashscope.aliyuncs.com/compatible-mode/v1
DASHSCOPE_MODEL=qwen-plus-2025-07-28

# 小米 MiMo 配置
XIAOMI_API_KEY=your_xiaomi_api_key
XIAOMI_BASE_URL=https://token-plan-cn.xiaomimimo.com/v1
XIAOMI_MODEL=MiMo-V2.5

# MCP Server 地址
MCP_SERVER_URL=http://127.0.0.1:8000/sse
```

**MCP 工具服务** - 在项目根目录 `.env` 中配置：

```env
# 天气服务 (OpenWeatherMap)
OPENWEATHER_API_KEY=your_openweather_api_key

# 网页搜索 (Firecrawl)
FIRECRAWL_API_KEY=your_firecrawl_api_key

# 地图服务 (高德地图)
AMAP_API_KEY=your_amap_api_key
```

**前端** - 复制 `frontend/.env.example` 为 `frontend/.env.development`：

```env
VITE_API_BASE=http://127.0.0.1:8001
```

### 4. 启动服务

**Step 1: 启动 MCP 工具服务**

```bash
# 在项目根目录
pip install -r requirements.txt
python travel_tools_mcp_server.py
# 默认监听 http://127.0.0.1:8000/sse
```

**Step 2: 启动后端服务**

```bash
cd backend
pip install -r requirements.txt
uvicorn app.main:app --host 0.0.0.0 --port 8001 --reload
```

**Step 3: 启动前端服务**

```bash
cd frontend
npm install
npm run dev
# 访问 http://localhost:5173
```

---

## 项目结构

```
travel-planner-agent/
├── travel_tools_mcp_server.py    # MCP 工具服务 (天气/景点/美食/路线)
├── requirements.txt               # MCP 服务依赖
├── .env                           # MCP 服务环境变量
│
├── backend/                       # 后端服务
│   ├── app/
│   │   ├── main.py               # FastAPI 入口
│   │   ├── config.py             # 应用配置
│   │   ├── db.py                 # 数据库初始化
│   │   ├── agents/
│   │   │   ├── graph.py          # LangGraph 多Agent系统 + ChatSupervisor
│   │   │   ├── prompts.py        # Agent Prompt 模板
│   │   │   └── tools.py          # MCP 工具客户端封装
│   │   ├── api/v1/
│   │   │   ├── endpoints/
│   │   │   │   ├── chat.py       # 对话式规划 (SSE 流式)
│   │   │   │   ├── travel.py     # 快速规划
│   │   │   │   ├── history.py    # 历史记录
│   │   │   │   └── user.py       # 用户偏好
│   │   │   └── schemas/          # 请求/响应模型
│   │   ├── models/               # 数据模型 (SQLModel)
│   │   ├── services/
│   │   │   ├── learning_engine.py # 偏好学习引擎
│   │   │   ├── stream_handler.py  # 流式响应处理
│   │   │   └── trip_service.py    # 行程服务
│   │   └── utils/                # 工具函数
│   ├── requirements.txt
│   └── .env.example
│
└── frontend/                      # 前端服务
    ├── src/
    │   ├── main.ts               # Vue 入口
    │   ├── App.vue               # 根组件
    │   ├── views/
    │   │   ├── ChatPlan.vue      # 对话式规划页面
    │   │   ├── PlannerView.vue   # 快速规划页面
    │   │   └── HistoryView.vue   # 历史记录页面
    │   ├── components/
    │   │   ├── chat/             # 聊天相关组件
    │   │   ├── map/              # 高德地图组件
    │   │   └── common/           # 通用组件
    │   ├── stores/               # Pinia 状态管理
    │   ├── api/                  # API 调用封装
    │   ├── composables/          # 组合式函数
    │   └── router/               # 路由配置
    ├── package.json
    └── vite.config.ts
```

---

## 核心功能说明

### MCP 工具服务

| 工具 | 数据源 | 说明 |
|------|--------|------|
| `get_weather` | OpenWeatherMap | 获取指定城市指定日期的天气预报 |
| `search_activities` | Firecrawl Search | 全网搜索目的地景点活动 |
| `search_restaurants` | Firecrawl Search | 全网搜索目的地美食餐厅 |
| `plan_route` | 高德地图 | 根据坐标规划最优游览路线 |

### Agent 系统

| Agent | 职责 | 工具 |
|-------|------|------|
| **WeatherAgent** | 天气查询与出行建议 | `get_weather` |
| **ActivityAgent** | 景点活动搜索与推荐 | `search_activities` |
| **FoodAgent** | 美食餐厅搜索与推荐 | `search_restaurants` |
| **RouteAgent** | 游览路线规划 | `plan_route` |
| **ChatSupervisor** | 意图识别、上下文管理、Agent 调度 | - |

### 对话式规划流程

1. 用户发送消息
2. ChatSupervisor 识别意图 (weather / activities / food / generate_plan / modify / general)
3. 从消息中提取城市、偏好信息
4. 按需调用对应 Agent
5. Agent 调用 MCP 工具获取真实数据
6. 汇总生成 Markdown 格式旅行计划
7. 通过 SSE 流式返回前端，支持地图可视化

---

## API 接口

| 方法 | 路径 | 说明 |
|------|------|------|
| POST | `/api/v1/travel/plan-chat` | 对话式规划 (SSE 流式) |
| GET | `/api/v1/travel/history/trips` | 获取历史行程列表 |
| GET | `/api/v1/travel/history/sessions/{id}` | 获取会话详情 |
| DELETE | `/api/v1/travel/history/trips/{id}` | 删除行程记录 |
| GET | `/api/v1/travel/user/preferences` | 获取用户偏好 |
| POST | `/api/v1/travel/user/preferences` | 更新用户偏好 |
| GET | `/health` | 健康检查 |

---

## License

MIT
