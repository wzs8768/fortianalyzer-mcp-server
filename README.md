<!-- FortiAnalyzer MCP Server — FortiAnalyzer 8.0 JSON-RPC API 管理服务器 — 25 MCP 工具 · 1190+ API 端点 -->
<p align="center">
  <img src="https://img.shields.io/badge/FortiAnalyzer-MCP%20Server-blue?style=for-the-badge&logo=fortinet&logoColor=white" alt="FortiAnalyzer MCP Server"/>
</p>

<h1 align="center">FortiAnalyzer MCP Server</h1>

<p align="center">
  <strong>基于 Model Context Protocol (MCP) 的 FortiAnalyzer 管理服务器</strong>
</p>

<p align="center">
  <img src="https://img.shields.io/badge/Python-3.11+-3776AB?style=flat-square&logo=python&logoColor=white"/>
  <img src="https://img.shields.io/badge/MCP-1.0-green?style=flat-square"/>
  <img src="https://img.shields.io/badge/API端点-1190+-blue?style=flat-square"/>
  <img src="https://img.shields.io/badge/MCP工具-25+-orange?style=flat-square"/>
  <img src="https://img.shields.io/badge/覆盖模块-7+-purple?style=flat-square"/>
  <img src="https://img.shields.io/badge/license-MIT-blue?style=flat-square"/>
</p>

---

## 概述

FortiAnalyzer MCP Server 通过 [Model Context Protocol](https://modelcontextprotocol.io/) 暴露 FortiAnalyzer 管理能力，让 AI 助手和 MCP 兼容工具可以编程化管理日志分析、事件告警、报表生成、ADOM 管理、设备监控等。

基于 **全异步 Python** 构建，支持持久化 HTTP 连接池，安全优先默认配置。

**已覆盖 FortiAnalyzer 8.0 API 模块：**

| 模块 | 工具数 | 说明 |
|------|--------|------|
| ADOM 管理 | 5 | 列表/创建/删除/详情/设备列表 |
| 文件夹/分组 | 2 | 文件夹列表/设备分组列表 |
| 事件/告警 | 4 | 告警列表/告警计数/事件列表/事件计数 |
| 日志查看 | 3 | 日志统计/日志文件状态/读取日志文件 |
| FortiView | 2 | Top 源IP / Top 目的IP（异步 add→get） |
| 系统 | 6 | 状态/许可/HA/存储/性能/日志转发 |
| 报表 | 1 | 报表调度列表 |
| IOC | 1 | IOC 许可状态 |
| 通用请求 | 1 | `faz_request` — 调用任意 API 端点 |
| **总计** | **25** | |

---

## 功能

### 设备管理
- 多设备并发管理
- API Token 认证
- 连接测试和健康监控
- ADOM 发现和按 ADOM 操作

### ADOM 管理
- ADOM 列表、创建、删除
- ADOM 详情查询
- ADOM 内设备列表

### 事件和告警
- 事件列表查询
- 告警列表和确认
- 事件详情检索

### 日志查看
- 日志全文搜索
- 日志统计（按字段聚合）
- 日志设备列表

### 报表
- 报表列表查看
- 报表在线生成
- 报表调度管理

### 系统管理
- 系统状态监控
- 许可信息查询
- FortiView 实时数据
- IOC 威胁情报

---

## 快速开始

### 环境要求

- Python 3.11+
- FortiAnalyzer 8.0+
- API Token（推荐）或管理员账号

### 安装

```bash
git clone https://github.com/wzs8768/fortianalyzer-mcp-server.git
cd fortianalyzer-mcp-server

# 方式一：pip
python -m venv .venv
source .venv/bin/activate
pip install -e .

# 方式二：uv（推荐，更快）
uv venv
source .venv/bin/activate
uv pip install -e .
```

### 配置

创建配置文件 `config/config.json`（**文件位置**：`<项目目录>/config/config.json`）：

```json
{
  "server": {
    "host": "0.0.0.0",
    "port": 8915,
    "name": "fortianalyzer-mcp-server",
    "version": "1.0.0"
  },
  "fortianalyzer": {
    "devices": {
      "FAZ-01": {
        "host": "192.168.1.100",
        "port": 443,
        "api_token": "<FortiAnalyzer-API-Token>",
        "adom": "root",
        "verify_ssl": false,
        "timeout": 60
      }
    }
  },
  "auth": {
    "require_auth": true,
    "api_tokens": [
      {"name": "hermes-local", "token": "<your-generated-token>"}
    ],
    "allowed_origins": []
  },
  "logging": {
    "level": "INFO",
    "format": "%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    "file": "logs/server.log",
    "console": true
  }
}
```

> 基于 FortiAnalyzer 8.0 适配开发，其他版本 API 可能存在差异，使用前请自行验证。

### 配置字段说明

| 字段 | 说明 |
|------|------|
| `fortianalyzer.devices` | 管理的 FortiAnalyzer 设备列表，每台设备一个命名字段 |
| `fortianalyzer.devices.<name>.api_token` | FortiAnalyzer 设备本身的 API Token（在 FortiAnalyzer 上生成） |
| `fortianalyzer.devices.<name>.adom` | 默认 ADOM（通常为 `root`） |
| `auth.api_tokens` | **MCP Server 认证 Token 列表**，客户端连接时携带，服务端验证 |
| `auth.api_tokens[].name` | Token 名称/标签，用于识别使用者（如 `hermes-local`、`claude-win`） |
| `auth.api_tokens[].token` | Token 值，用 `python3 -c "import secrets; print(secrets.token_urlsafe(32))"` 生成。⚠️ 这是 **MCP Server 认证 Token**（本机生成），不要与上方 `api_token`（FortiAnalyzer 设备 API Token）混淆。 |
| `logging.file` | 日志文件路径，认证日志会记录客户端名称（如 `Auth OK — client=hermes-local`） |

### 启动服务

**HTTP / HTTPS**（网络访问）→ `server_http.py`

```bash
# HTTPS · SSE + Streamable HTTP 同时（可选，需要自签名证书，见下方）
python -m src.fortianalyzer_mcp.server_http --host 0.0.0.0 --port 8915 \
  --transport all --ssl-cert certs/server.crt --ssl-key certs/server.key

# HTTP · SSE + Streamable HTTP 同时
python -m src.fortianalyzer_mcp.server_http --host 0.0.0.0 --port 8916 --transport all
```

| `--transport` | 端点 |
|---------------|------|
| `all`（推荐） | `/fortianalyzer-mcp` + `/fortianalyzer-mcp-sse` 同时 |
| `streamable-http`（CLI 默认） | `/fortianalyzer-mcp` |
| `sse` | `/fortianalyzer-mcp-sse` |

> `server_http.py` 默认走 HTTP，加了 `--ssl-cert` + `--ssl-key` 就是 HTTPS，**与 `--transport` 无关**。要同时提供 HTTP 和 HTTPS，起两个进程用不同端口即可。

**自签名证书（内网测试）：**

```bash
openssl req -x509 -newkey rsa:4096 -keyout certs/server.key \
  -out certs/server.crt -days 3650 -nodes \
  -subj "/CN=<你的服务器IP>" -addext "subjectAltName=IP:<你的服务器IP>"
```

**systemd 服务（开机自启）：**

```bash
cp contrib/fortianalyzer-mcp.service ~/.config/systemd/user/
# 编辑 ExecStart 行，按需设置 --transport / --ssl-cert / --ssl-key
systemctl --user daemon-reload
systemctl --user enable --now fortianalyzer-mcp
```

### Docker 部署

无需安装 Python 环境，一条命令启动：

```bash
# 1. 克隆仓库并准备配置
git clone https://github.com/wzs8768/fortianalyzer-mcp-server.git
cd fortianalyzer-mcp-server

# 2. 创建 config/config.json（见上方[配置](#配置)）

# 3. 启动（HTTP · :8916）
docker compose up -d
```

**HTTPS 模式：**

```bash
# 1. 生成自签名证书
openssl req -x509 -newkey rsa:4096 -keyout certs/server.key \
  -out certs/server.crt -days 3650 -nodes \
  -subj "/CN=<服务器IP>" -addext "subjectAltName=IP:<服务器IP>"

# 2. 编辑 docker-compose.yml，取消 HTTPS 端口映射注释，添加启动参数：
#    command: [..., "--ssl-cert", "/app/certs/server.crt", "--ssl-key", "/app/certs/server.key", "--port", "8915"]

docker compose up -d
```

**容器特性：**

| 特性 | 说明 |
|------|------|
| 多阶段构建 | builder + runtime，镜像精简 |
| 安全运行 | 非 root 用户 `fazmcp` |
| 健康检查 | 每 30 秒 `GET /health` |
| 资源限制 | CPU 1 核 / 内存 512M |
| 日志持久化 | `./logs` 目录挂载 |
| 配置挂载 | `config/`、`certs/` 只读挂载 |

### MCP 客户端集成

#### 场景一：客户端与服务器在同一台机器（STDIO 模式）

客户端直接启动进程，无需预运行服务：

```json
{
  "mcpServers": {
    "fortianalyzer": {
      "command": "python",
      "args": ["-m", "src.fortianalyzer_mcp.server_http"],
      "env": { "FORTIANALYZER_MCP_CONFIG": "/path/to/config.json" }
    }
  }
}
```

适用于 Claude Desktop、OpenCode、Codex CLI 等 STDIO transport 客户端。

#### 场景二：客户端与服务器不在同一台机器（HTTP / HTTPS 模式）⭐

> **想同时提供 HTTP 和 HTTPS？** 启动两个进程，用不同端口（如 HTTPS→8915，HTTP→8916），按下方对应地址连接。

```json
// HTTPS · Streamable HTTP
{ "url": "https://<服务器IP>:8915/fortianalyzer-mcp",           "transport": "streamable-http" }

// HTTPS · SSE
{ "url": "https://<服务器IP>:8915/fortianalyzer-mcp-sse",       "transport": "sse" }

// HTTP · Streamable HTTP
{ "url": "http://<服务器IP>:8916/fortianalyzer-mcp",            "transport": "streamable-http" }

// HTTP · SSE
{ "url": "http://<服务器IP>:8916/fortianalyzer-mcp-sse",        "transport": "sse" }
```

> ⚠️ Claude Desktop **仅支持 STDIO transport**，远程连接需通过 `mcp-remote` 中转（见下方 Windows 配置），走 HTTPS。

各客户端配置文件位置：

| 客户端 | 配置文件 |
|--------|---------|
| Claude Desktop (macOS/Linux) | `~/.claude/claude_desktop_config.json` |
| Claude Desktop (Windows) | `%LOCALAPPDATA%\Packages\Claude_<随机字符串>\LocalCache\Roaming\Claude\claude_desktop_config.json` |
| OpenCode | `~/.opencode/config.json` 或 `--mcp-config` 参数 |
| Cursor | `~/.cursor/mcp_servers.json` |
| Codex CLI | `~/.codex/mcp_servers.json` |
| Hermes | `~/.hermes/config.yaml` → `mcp_servers` 段 |
| OpenClaw | `~/.openclaw/openclaw.json` → `mcp.servers` 段 |

#### Windows Claude Desktop（自签名证书 / TLS 跳过验证）

Windows 版 Claude Desktop 不支持直接在配置中设置 `ssl_verify: false`，需使用 `mcp-remote` 中转并设置环境变量绕过证书验证：

**前置依赖：安装 Node.js**

```powershell
# PowerShell（管理员）
winget install OpenJS.NodeJS.LTS
```

**Claude Desktop 配置（JSON 格式，`claude_desktop_config.json`）：**

> 配置文件路径示例：`C:\Users\<用户名>\AppData\Local\Packages\Claude_<随机字符串>\LocalCache\Roaming\Claude\`（Windows 商店版），可通过文件资源管理器地址栏输入 `%LOCALAPPDATA%\Packages\` 定位 `Claude_*` 目录。

```json
{
  "mcpServers": {
    "fortianalyzer": {
      "command": "npx",
      "args": [
        "-y",
        "mcp-remote",
        "https://<服务器IP>:8915/fortianalyzer-mcp",
        "--transport",
        "streamable-http",
        "--header",
        "Authorization:${FORTIANALYZER_AUTH}"
      ],
      "env": {
        "NODE_TLS_REJECT_UNAUTHORIZED": "0",
        "FORTIANALYZER_AUTH": "Bearer <your-shared-token>"
      }
    }
  },
  "coworkUserFilesPath": "C:\\Users\\<用户名>\\Claude",
  "preferences": { "...": "..." }
}
```

> 在已有的 `claude_desktop_config.json` 文件中，将 `mcpServers` 块合并进去即可，其余配置项保持不变。

> `NODE_TLS_REJECT_UNAUTHORIZED=0` 跳过 TLS 证书验证，适用于自签名证书环境。生产环境建议将证书导入系统受信任根。

#### 远程访问安全加固

`auth` 配置已在 [配置](#配置) 节完整给出（`config/config.json` → `auth.api_tokens`），此处补充操作说明：

**1. 生成 Token：**
```bash
python3 -c "import secrets; print(secrets.token_urlsafe(32))"
```

**2. 写入 `config/config.json` 的 `auth.api_tokens` 数组**（见上方完整配置示例）。

**3. 多客户端 Token 命名示例：**
```json
"auth": {
  "require_auth": true,
  "api_tokens": [
    {"name": "hermes-local", "token": "<token-1>"},
    {"name": "claude-win",    "token": "<token-2>"},
    {"name": "cursor-laptop", "token": "<token-3>"}
  ]
}
```

> 也兼容旧格式（裸字符串）：`"api_tokens": ["token1", "token2"]`，自动标记为 `(unnamed)`。

**4. 重启服务生效：** `systemctl --user restart fortianalyzer-mcp`

**5. Claude Desktop 客户端配置 — 见上方 [Windows Claude Desktop](#windows-claude-desktop自签名证书--tls-跳过验证) 节的完整 `claude_desktop_config.json` 示例。**

> `--header "Authorization:${FORTIANALYZER_AUTH}"` 中 `:` 和 `Bearer` 之间无空格，避免 Windows 版 Claude Desktop 的参数空格 bug。

Hermes Agent 配置（YAML 格式，`~/.hermes/config.yaml`）：

```yaml
mcp_servers:
  fortianalyzer:
    url: https://<服务器IP>:8915/fortianalyzer-mcp
    enabled: true
    ssl_verify: false
    connect_timeout: 30
    headers:
      Authorization: "Bearer <your-shared-token>"
```

> Hermes 的 HTTP 配置（无需证书）：将 `url` 改为 `http://<服务器IP>:8916/fortianalyzer-mcp`，删除 `ssl_verify` 行。

Codex CLI 配置（TOML 格式，`~/.codex/config.toml` 或项目 `.codex.toml`）：

```toml
[mcp_servers.fortianalyzer]
enabled = true
url = "http://<服务器IP>:8916/fortianalyzer-mcp"

[mcp_servers.fortianalyzer.http_headers]
Authorization = "Bearer <your-shared-token>"
Accept = "application/json, text/event-stream"
```

> ⚠️ Codex **必须使用 HTTP（8916 端口）**——Codex 不支持跳过自签名证书验证，HTTPS 连接会因证书错误失败。

Cursor / OpenCode / OpenClaw 等 JSON 格式客户端（**HTTPS**）：

Cursor / OpenCode：
```json
{
  "mcpServers": {
    "fortianalyzer": {
      "url": "https://<服务器IP>:8915/fortianalyzer-mcp",
      "transport": "streamable-http",
      "headers": {
        "Authorization": "Bearer <your-shared-token>"
      }
    }
  }
}
```

OpenClaw（需使用 `rejectUnauthorized` 字段，`mcp.servers` 块放在 `openclaw.json` 末尾）：
```json
{
  "mcp": {
    "servers": {
      "FortiAnalyzer": {
        "url": "https://<服务器IP>:8915/fortianalyzer-mcp",
        "transport": "streamable-http",
        "rejectUnauthorized": false,
        "headers": {
          "Authorization": "Bearer <your-shared-token>"
        }
      }
    }
  }
}
```

---

## MCP 工具列表（25）

### 设备管理 (5)
`list_devices` `get_device_status` `health_check` `test_device_connection` `get_server_info`

### ADOM 管理 (5)
`list_adoms` `create_adom` `delete_adom` `get_adom_detail` `list_adom_devices`

### 事件/告警 (4)
`list_events` `list_alerts` `acknowledge_alert` `get_event_detail`

### 日志查看 (3)
`search_logs` `get_log_stats` `list_log_devices`

### 报表 (3)
`list_reports` `generate_report` `list_report_schedules`

### 系统 (2)
`get_system_status` `get_license_info`

### FortiView / IOC (2)
`get_fortiview_data` `list_ioc_entries`

### 通用请求 (1)
`faz_request` — 直接调用 FortiAnalyzer JSON-RPC API 任意端点，覆盖 1190+ 方法

---

## 架构

```
fortianalyzer-mcp-server/
├── src/fortianalyzer_mcp/
│   ├── server_http.py            # HTTP MCP 服务器 (FastMCP)
│   ├── auth_middleware.py        # Bearer Token 认证中间件
│   ├── config/
│   │   ├── loader.py             # 配置文件加载
│   │   └── models.py             # Pydantic 配置模型
│   ├── core/
│   │   ├── faz_client.py         # 异步 JSON-RPC 客户端（会话管理）
│   │   └── logging.py            # 结构化日志
│   ├── tools/
│   │   ├── base.py               # 工具基类（错误处理、格式化）
│   │   ├── device.py             # 设备管理工具
│   │   └── modules.py            # ADOM/事件/日志/报表/系统工具
│   └── formatting/
├── config/
│   └── config.json               # 设备配置示例
├── certs/
│   ├── server.crt                # 自签名证书
│   └── server.key                # 私钥
├── contrib/
│   ├── fortianalyzer-mcp.service  # HTTPS systemd 服务
│   └── fortianalyzer-mcp-http.service  # HTTP systemd 服务
├── README.md
└── LICENSE
```

### 设计原则

- **全异步**：所有 API 调用使用 `httpx.AsyncClient`，每设备持久化连接池
- **安全优先**：SSL 验证默认开启，CORS 默认空（`allowed_origins: []`），强制 Bearer Token 认证
- **清晰分层**：配置模型、API 客户端、工具逻辑、格式化独立
- **JSON-RPC**：FortiAnalyzer 使用 JSON-RPC 协议，客户端自动管理会话和请求 ID

---

## 安全

| 设置 | 默认值 | 说明 |
|------|--------|------|
| `verify_ssl` | `true` | SSL 证书验证 |
| `allowed_origins` | `[]` | 无 CORS（显式按需开启） |
| `require_auth` | `true` | MCP 服务器强制认证（所有客户端必须提供 Bearer Token） |

**生产环境建议：**
- 使用 **API Token** 而非用户名密码
- 保持 `verify_ssl: true`（自签证书测试除外）
- HTTP 模式下设置明确的 `allowed_origins`
- 在可信网络内或反向代理后运行
- 敏感配置使用环境变量

---

## 常见问题

**连接被拒绝**
- 确认 FortiAnalyzer 设备可达且 API 已启用
- 检查端口 443 未被防火墙拦截

**认证失败 (401)**
- 验证 API Token 有效且权限足够
- 确认 `auth.api_tokens` 中已添加对应 Token

**SSL 证书错误**
- 实验环境自签证书：设置 `verify_ssl: false`
- 生产环境：在 FortiAnalyzer 上安装有效证书

**API 返回 -11 (No Permission)**
- 确认 API 用户权限足够（需 `rpc-permit read-write`）
- 检查用户类型为 `api`

**ADOM 未找到**
- 使用 `list_adoms` 查看可用 ADOM
- ADOM 名称大小写敏感

---

## CI/CD

每次 push 到 `main` 分支自动运行（`.github/workflows/ci.yml`）：

| Job | 说明 |
|-----|------|
| Lint | `ruff check src/` 代码风格检查 |
| Build | `python -m build` 验证包结构 |
| Docker | `docker build` 验证镜像构建 |

---

## 许可

MIT License. 详见 [LICENSE](LICENSE)

## 致谢

- [wzs8768/fortigate-mcp-server](https://github.com/wzs8768/fortigate-mcp-server) — 姊妹项目，FortiGate MCP Server
- [Model Context Protocol](https://modelcontextprotocol.io/) — 协议规范
- [FastMCP](https://gofastmcp.com/) — Python MCP 服务器框架
- [FortiAnalyzer 产品文档](https://docs.fortinet.com/) — FortiAnalyzer 官方文档
- [httpx](https://www.python-httpx.org/) — 异步 HTTP 客户端
