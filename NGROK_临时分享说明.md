# 使用 ngrok 临时分享网站

本文记录本项目已验证过的 ngrok 分享方式。命令适用于 Windows PowerShell，均在包含 `README.md` 的项目根目录执行。公网地址只在本机前端、后端和 ngrok 同时运行期间可用；不需要修改路由器设置，也不需要把后端端口开放到公网。

## 工作原理

```text
访问者浏览器 → ngrok HTTPS 公网地址 → 本机 Streamlit（127.0.0.1:8501）
                                             ↓ 本机请求
                                     FastAPI（127.0.0.1:8002）
                                             ↓
                                独立演示数据库与项目知识库
```

ngrok 只转发 **8501** 端口。Streamlit 在电脑上运行，会从本机访问 FastAPI 的 8002 端口，所以浏览器无需直接连接 8002。两个服务继续绑定 `127.0.0.1`。

## 准备

项目依赖和 ngrok 应先安装并配置。可在项目根目录检查：

```powershell
Test-Path .\.venv\Scripts\python.exe
ngrok version
ngrok config check
```

第一条应返回 `True`，最后一条应显示配置文件有效。ngrok 的账号令牌保存在本机 ngrok 配置中，不要写进本项目或分享给访问者。本机已验证的 ngrok 版本为 3.38.0。

## 启动临时演示

打开三个 PowerShell 窗口，均切换到项目根目录，并依次执行以下步骤。不要用 `start.bat` 启动对外演示：它会按原有 `.env` 使用本机日常数据库和真实模型配置。

### 窗口 1：启动后端

```powershell
$env:DATABASE_PATH = 'data/ngrok-demo/career_guidance.db'
$env:LLM_API_KEY = ''
$env:LLM_BASE_URL = ''
$env:LLM_MODEL = ''
$env:EMBEDDING_MODEL = ''
.\.venv\Scripts\python.exe -m uvicorn app.api:app --host 127.0.0.1 --port 8002
```
本次验证使用了 `data/ngrok-demo/career_guidance.db`。`DATABASE_PATH` 决定个人访问数据库的位置；演示时的访问记录位于同目录的 `sessions/` 中，与日常使用的 `data/career_guidance.db` 和 `data/sessions/` 分开。四个空的模型变量覆盖 `.env` 中的真实模型配置，使后端进入本地演示模式。若希望下次演示从全新记录开始，可把 `DATABASE_PATH` 改为新的目录，例如 `data/ngrok-demo-02/career_guidance.db`。

### 窗口 2：启动前端

```powershell
$env:CAREER_API_URL = 'http://127.0.0.1:8002'
.\.venv\Scripts\python.exe -m streamlit run app/ui.py --server.address 127.0.0.1 --server.port 8501 --server.headless true
```
先在本机打开 `http://127.0.0.1:8501/`，确认页面可以访问。

### 窗口 3：启动 ngrok

```powershell
ngrok http 127.0.0.1:8501
```

ngrok 窗口中的 `Forwarding` 或 `url=` 后会显示 `https://…ngrok-free.dev` 地址。把这个**不带 `visit` 等查询参数的首页地址**发给访问者即可。免费版首次访问可能显示 ngrok 提示页，访问者点击 **Visit Site** 后进入网站。每次重新启动时，以 ngrok 当次显示的地址为准。

## 验证

在另一个 PowerShell 窗口检查：

```powershell
Invoke-RestMethod http://127.0.0.1:8002/health
Invoke-RestMethod http://127.0.0.1:8002/status
Invoke-RestMethod http://127.0.0.1:8002/visits
Invoke-WebRequest http://127.0.0.1:8501/
```

预期 `/health` 返回 `status: ok`，`/status` 的 `mode` 为 `demo`，前端 HTTP 状态为 200。分享前检查 `/visits`：如果已有不想让别人看到的演示记录，请换用一个新的 `DATABASE_PATH` 目录并重启后端。

也可以用手机关闭 Wi-Fi、通过移动网络打开 ngrok 链接，确认外网访问。ngrok 的本机管理页 `http://127.0.0.1:4040/` 能查看当前地址与请求记录，仅供自己在本机使用。

## 结束分享

先在 ngrok 窗口按 `Ctrl+C`，公网地址随即停止转发。然后在 Streamlit 和 FastAPI 窗口分别按 `Ctrl+C`。关闭电脑或网络断开后，链接也会失效。ngrok 不会自动删除演示数据库；需要保留记录时可直接再次使用同一路径。

## 访问边界与常见问题

- 目前没有网站账号和多人权限管理。这个无密码公网链接的持有者可以访问网站，演示访问者之间也可能通过历史记录入口看到彼此保存的内容，因此只用虚构资料演示。
- 页面地址中的 `visit` 参数不是密码；分享首页地址时不要附带该参数。
- ngrok 显示 `502`：先确认 8501 前端仍在运行，并检查 `http://127.0.0.1:8501/`。
- 页面提示后端连接失败：检查窗口 1 是否仍在运行、`/health` 是否正常，以及窗口 2 的 `CAREER_API_URL` 是否指向 `http://127.0.0.1:8002`。
- 端口被占用：检查是否已经有一套前后端或 ngrok 在运行，避免重复启动。
