# 携程智能助手

一个基于 `LangGraph + Gradio + FastAPI` 的旅行智能助手示例项目，支持航班查询、航班改签/取消、酒店预订、租车、旅行推荐，以及基于企业 FAQ 的政策检索。

当前项目提供两种使用方式：

1. 直接运行 `Gradio`，通过网页聊天界面访问。
2. 运行 `FastAPI`，通过 `/docs` 打开 Swagger 文档并调试接口。

## 项目结构

```text
.
├── main.py                     # FastAPI 启动入口
├── graph_chat/graph_gradio.py  # Gradio 启动入口
├── api/                        # FastAPI 路由
├── graph_chat/                 # LangGraph 工作流
├── tools/                      # 航班、酒店、租车、FAQ 检索工具
├── config/                     # 项目配置
├── static/                     # 静态资源
├── order_faq.md                # 企业政策 FAQ
└── travel2.sqlite              # 备份测试数据
```

## 运行环境

- Python `3.10+`
- 建议使用虚拟环境
- 如果要运行 `FastAPI` 的用户登录/注册相关接口，需要准备 MySQL
- 如果只运行 `Gradio` 聊天界面，主要依赖项目内置的 SQLite 测试数据

## 安装依赖

仓库当前提供了 `requirements.txt`，也可以先按下面的核心依赖安装：

```bash
pip install fastapi uvicorn gradio pymysql sqlalchemy dynaconf python-dotenv python-jose passlib bcrypt python-multipart pandas numpy
pip install langchain langchain-core langchain-community langgraph langchain-openai dashscope
```

如果你的环境里有缺失包，再根据报错继续补装即可。

## 环境变量

项目里通过 `.env` 加载大模型相关配置，至少需要准备：

```env
DASHSCOPE_API_KEY=your_api_key
BASE_URL=your_base_url
```

说明：

- `graph_chat/llm_tavily.py` 中当前使用的是 `ChatTongyi(model="qwen3-max")`
- `tools/retriever_vector.py` 中使用了 `DashScopeEmbeddings`
- 不要把真实密钥提交到 GitHub

## 配置说明

默认配置文件在 `config/development.yml`。

其中 FastAPI 默认监听：

- `HOST: 127.0.0.1`
- `PORT: 8000`

FastAPI 还依赖一套 MySQL 配置：

```yml
DATABASE:
  DRIVER: mysql
  NAME: your_db_name
  HOST: 127.0.0.1
  PORT: 3306
  USERNAME: root
  PASSWORD: your_password
```

如果你只体验 `Gradio` 页面，可以先不处理这部分 MySQL 配置。

## 方式一：通过 Gradio 直接访问

### 启动命令

在项目根目录执行：

```bash
python graph_chat/graph_gradio.py
```

### 访问地址

启动后，终端会输出一个本地访问地址，通常是：

```text
http://127.0.0.1:7860
```

### 说明

- 页面提供一个聊天输入框，可以直接输入旅行相关问题
- 工作流在涉及敏感操作时会中断，并提示你输入 `y` 继续执行
- 启动时会自动执行 `update_dates()`，将 SQLite 测试数据刷新到当前时间附近

### 适合场景

- 快速体验智能助手能力
- 验证 LangGraph 工作流
- 不依赖 FastAPI 文档页面

## 方式二：运行 FastAPI 并访问接口文档

### 启动命令

在项目根目录执行：

```bash
python main.py
```

服务默认运行在：

```text
http://127.0.0.1:8000
```

### 打开 Swagger 文档

浏览器访问：

```text
http://127.0.0.1:8000/docs
```

项目会自动挂载接口文档认证依赖，因此推荐通过 `/docs` 调试接口。

### 主要接口

- `POST /api/register/`：注册用户
- `POST /api/login/`：普通登录，返回项目自定义 token
- `POST /api/auth/`：Swagger 文档里的授权入口
- `POST /api/graph/`：调用工作流

### 在 `/docs` 中调用接口的建议顺序

1. 先调用 `POST /api/register/` 创建用户
2. 再调用 `POST /api/auth/` 获取 `access_token`
3. 点击 Swagger 页面右上角 `Authorize`
4. 按项目要求填入：`JWT <你的token>`
5. 再调用 `POST /api/graph/`

注意：

- 项目自定义的文档鉴权格式不是 `Bearer token`，而是 `JWT token`
- 如果 MySQL 没有准备好，`register/login/auth` 这类接口将无法正常使用

### `/api/graph/` 请求示例

请求体示例：

```json
{
  "user_input": "帮我查一下我的航班信息",
  "config": {
    "configurable": {
      "passenger_id": "3442 587242",
      "thread_id": "test-thread-001"
    }
  }
}
```

返回示例：

```json
{
  "assistant": "这里会返回 AI 助手的回复内容"
}
```

如果工作流遇到需要确认的敏感操作，接口会返回类似提示：

```text
AI助手马上根据你要求，执行相关操作。您是否批准上述操作？输入'y'继续；否则，请说明您请求的更改。
```

此时再次调用 `/api/graph/`，把 `user_input` 传成 `y`，并保持同一个 `thread_id` 即可继续当前会话。

## 常见问题

### 1. 为什么 Gradio 能跑，但 FastAPI 接口不能完整使用？

因为这两个入口依赖的资源不完全一样：

- `Gradio` 主要依赖 LangGraph、SQLite 测试数据和模型配置
- `FastAPI` 除了工作流本身，还依赖 MySQL 用户体系和 JWT 认证流程

### 2. 为什么需要保持同一个 `thread_id`？

项目的工作流使用 `MemorySaver` 做会话检查点。多轮对话、确认操作、继续执行都依赖同一个 `thread_id`。

### 3. 为什么输入 `y` 才会继续？

项目把部分写操作放在 `interrupt_before` 节点前中断，目的是在真正执行敏感动作前先征得用户确认。

