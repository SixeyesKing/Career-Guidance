# 向前 · AI 职业规划助手

面向软件工程及相关专业学生的职业探索工作台。通过个人画像、岗位比较、资料检索、职业咨询和行动计划，帮助用户把就业方向的疑问整理成可执行的准备步骤。

当前是本地课程项目 MVP，采用 **Streamlit + FastAPI + SQLite + Chroma**。支持后端开发、前端开发、测试开发三个方向；没有模型密钥也可以体验本地演示流程。

**首次进入只展示欢迎引导。** 点击“开始填写个人画像”后进入表单；刷新会保留当前记录。右上角“新建”可以开启独立探索，侧栏“导入历史记录”可以恢复本机已有结果。

## 目录

- [功能与使用边界](#功能与使用边界)
- [快速开始](#快速开始)
- [模型和环境配置](#模型和环境配置)
- [完整使用流程](#完整使用流程)
- [访问会话与数据保存](#访问会话与数据保存)
- [知识库维护](#知识库维护)
- [项目结构与实现](#项目结构与实现)
- [API 使用说明](#api-使用说明)
- [开发与测试](#开发与测试)
- [常见问题](#常见问题)
- [仓库内容与协作](#仓库内容与协作)

## 功能与使用边界

| 页面 / 模块 | 当前能力 |
| --- | --- |
| 今日概览 | 空白欢迎入口；填写画像后显示本次探索的下一步和最近记录 |
| 个人画像 | 年级、专业、接触过的技术、项目经历、兴趣、意向城市、每周准备时间 |
| 岗位探索 | 比较三类岗位的工作内容和常见技能；自主选择方向 |
| 可选体验 | 小任务体验、跳过、记录兴趣 / 难度 / 继续意愿及文字反馈 |
| 职业分析 | 分开呈现已知基础、待确认信息、建议行动和资料来源 |
| 职业咨询 | 围绕当前岗位提问、连续对话、查看本次访问的历史对话 |
| 行动计划 | 生成 1–12 周计划，支持 1 / 2 / 4 / 8 周快捷选择和每周时间预算 |
| 计划导出 | 查看同岗位历史版本、任务说明、完成标准、学习资料，下载 Markdown |
| 历史导入与新建 | 从本机已保存记录恢复画像、分析、咨询和计划；新建空白探索；刷新保留当前进度 |
| 资料检索 | 关键词检索；配置 Embedding 并建立索引后可使用 Chroma 向量检索 |

系统提供职业探索信息，不输出岗位匹配百分比或录用概率。未填写的经历会被视为待确认信息，不代表能力不足。岗位台账和指南不是实时招聘抓取结果，具体岗位、要求和时间以来源页面为准。

当前没有账号登录、跨访问自动恢复、公共服务鉴权或多人权限管理。默认只监听本机地址，适合个人使用、开发和课程演示。

## 快速开始

### 1. 准备环境并获取代码

推荐使用 **64 位 Python 3.10 或 3.11** 和 Git。项目已有 Python 3.9.10 下的运行记录，但新环境建议使用较新版本，避免依赖兼容问题。以下命令以 Windows PowerShell 为主。

```powershell
git clone https://github.com/SixeyesKing/Career-Guidance.git
cd Career-Guidance
python --version
```

也可以通过 GitHub 的 **Code → Download ZIP** 下载，解压后在含有 `README.md` 的项目根目录打开终端。

### 2. 安装依赖

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install --upgrade pip
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
```

本文直接使用虚拟环境内的 Python，不需要执行 `Activate.ps1`，也不需要修改 PowerShell 执行策略。

### 3. 创建本地配置

```powershell
if (-not (Test-Path .env)) { Copy-Item .env.example .env }
```

第一次体验可以保持模型配置为空，直接进入本地演示模式。需要真实模型回答时，再按下一节配置。已有 `.env` 不要被示例文件覆盖。

### 4. 启动后端

在项目根目录打开第一个 PowerShell 窗口：

```powershell
.\.venv\Scripts\python.exe -m uvicorn app.api:app --host 127.0.0.1 --port 8002
```

看到 `Uvicorn running on http://127.0.0.1:8002` 后保持这个窗口运行。开发时可额外加 `--reload`，文件修改后后端会自动重启。

### 5. 启动前端

在同一项目根目录打开第二个 PowerShell 窗口：

```powershell
.\.venv\Scripts\python.exe -m streamlit run app/ui.py --server.address 127.0.0.1 --server.port 8501 --server.headless true
```

| 地址 | 用途 |
| --- | --- |
| [http://127.0.0.1:8501/](http://127.0.0.1:8501/) | 用户界面，从这里开始使用 |
| [http://127.0.0.1:8002/health](http://127.0.0.1:8002/health) | 后端健康检查，正常返回 `{"status":"ok"}` |
| [http://127.0.0.1:8002/docs](http://127.0.0.1:8002/docs) | FastAPI 交互式接口文档 |

两个终端都要保持运行。停止项目时分别按 `Ctrl+C`；之后使用只需重复启动后端和前端，不必重新安装依赖。

### macOS / Linux 命令参考

尚未在本项目中完成这两个平台的整体验收，可按相同架构运行：

```bash
python3 -m venv .venv
.venv/bin/python -m pip install -r requirements.txt
test -f .env || cp .env.example .env
# 终端 1
.venv/bin/python -m uvicorn app.api:app --host 127.0.0.1 --port 8002
# 终端 2：切换到同一项目根目录后执行
.venv/bin/python -m streamlit run app/ui.py --server.address 127.0.0.1 --server.port 8501 --server.headless true
```

## 模型和环境配置

配置文件位于根目录 `.env`，模板为 [.env.example](.env.example)。更改后重启前后端进程；已设置的系统环境变量优先于 `.env`。

| 变量 | 默认 / 示例 | 用途 |
| --- | --- | --- |
| `LLM_API_KEY` | 空 | OpenAI 兼容服务的 API 密钥，仅在本地填写 |
| `LLM_BASE_URL` | 空；如 `https://api.openai.com/v1` | 服务基础地址，不要填完整聊天接口路径 |
| `LLM_MODEL` | 空 | 服务提供方实际支持的聊天模型名 |
| `EMBEDDING_MODEL` | 空 | 可选，用于向量化的模型名 |
| `DATABASE_PATH` | `data/career_guidance.db` | 未携带访问标识的 API 调用使用的数据库 |
| `CHROMA_PATH` | `data/chroma` | 本地向量索引目录 |
| `API_HOST` | `127.0.0.1` | 模板中的主机约定；启动地址以 Uvicorn `--host` 为准 |
| `API_PORT` | `8002` | 前端默认连接的后端端口；Uvicorn 仍需指定相同 `--port` |
| `CAREER_API_URL` | 未设置 | 可选，覆盖前端的后端地址，如 `http://127.0.0.1:8002` |

数据库和索引的相对路径以项目根目录为基准。前端 8501 端口由 Streamlit 启动参数指定，不受 `API_PORT` 控制。

### 三种运行方式

| 方式 | 配置和准备 | 预期行为 |
| --- | --- | --- |
| 本地演示 | 聊天模型配置留空 | 使用规则生成的演示回答和计划，界面标注演示状态 |
| 真实模型 + 关键词检索 | 填写 `LLM_API_KEY`、`LLM_BASE_URL`、`LLM_MODEL` | 检索本地 Markdown 资料并交给模型生成回答 |
| 真实模型 + 向量检索 | 再填 `EMBEDDING_MODEL`，执行知识库入库 | 使用 Chroma 索引；向量请求失败时可回退到关键词检索 |

聊天和 Embedding 共用密钥和基础地址，目前不支持为二者分别配置服务商。代码会在基础地址末尾补 `/v1`（已有则不再补），再请求 `/chat/completions` 或 `/embeddings`。分析和计划使用 JSON 输出，服务需要兼容 `response_format: {"type":"json_object"}`。

模型未配置或请求失败时，可回退为本地演示内容；请以每次结果的状态提示为准。`GET /status` 的“模型已配置”只说明配置存在，不是连通性或额度验证。

使用真实模型时，相关画像、问题、部分对话历史及检索资料会发送到你配置的模型服务；向量入库会将资料文本发送给 Embedding 服务。不配置模型也能完成基础演示。

## 完整使用流程

### 第一步：从欢迎页开始

首次打开 8501 页面，欢迎页展示“开始填写个人画像”入口。已有记录可在左侧“导入历史记录”选择恢复；再次刷新当前页面会保留当前记录和页面。

### 第二步：填写并保存个人画像

1. 填写年级、专业；年级可以选择“暂不填写”。
2. 选择接触过的技术，未列出的技术用逗号填写在“其他技术”中。
3. 描述课程项目、个人练习或实习经历：做了什么、负责哪部分、遇到了什么问题。
4. 选择兴趣、填写意向城市和每周准备时间。
5. 点击“保存个人画像”，再点击“去比较岗位方向”。

不要求一次填完整，也不要求技能已达到熟练水平。**每周时间是职业探索、学习和求职准备的预算，不含上课及课程作业**，可填写 1–40 小时，默认 5 小时。表单需要主动保存；跳转页面前先保存输入。

### 第三步：比较岗位，可选做一次体验

在“岗位探索”中比较后端、前端和测试开发的日常工作及常见技能。“画像中已提到”只表示填写过相关信息，不是熟练度评分；“目前还待了解”也不等于能力不足。

可展开体验任务，选择开始、完成后记录感受，或直接跳过。兴趣、难度和继续意愿分别记录，不作为综合能力分。选择想深入了解的方向后进入职业分析。

### 第四步：生成分析并咨询

在“职业分析”中确认岗位，点击“更新职业分析”。查看已有基础、待确认信息、行动建议以及引用来源；如果补充了画像，需要再次更新分析。

下方可以输入问题或使用快捷提问。历史分析和对话按本次访问、当前岗位查看。切换岗位会切换咨询上下文；需要查看已有对话时使用“打开历史对话”。

### 第五步：制定和下载计划

1. 点击“用这份分析制定行动计划”，或进入侧栏“行动计划”。
2. 选择岗位、1–12 周准备周期和每周 1–40 小时时间预算。
3. 点击“生成新计划”，等待生成结果。
4. 按周查看目标、任务、预计时间、完成标准和相关学习资料。
5. 点击“下载 Markdown 计划”，在本机保存结果。

计划页调整时间不会修改个人画像。每次生成会保存新版本；调整参数本身不会改写旧计划。历史计划仅显示本次访问、所选岗位的记录。学习资料按任务提供，不需要把所有资料全部学完。

### 第六步：新建或恢复探索

需要换一组个人信息时，点击右上角“新建”。页面返回欢迎入口并创建空白记录，原记录仍可从左侧“导入历史记录”恢复。导入后，画像、历史分析、咨询与计划都重新关联到所选记录。

## 访问会话与数据保存

| 操作 | 数据行为 |
| --- | --- |
| 同次访问切换侧栏页面、点击按钮 | 继续使用同一个访问标识，已保存进度保留 |
| 刷新当前页面 | 从页面地址中的访问标识恢复同一记录与页面 |
| 打开不含访问标识的新地址 | 自动打开本机最近保存的记录；没有历史记录时才创建空白访问 |
| 点击“新建” | 创建新的空白访问标识，旧记录仍保留 |
| 点击“导入历史记录” | 从本机已有内容的访问中选择并恢复完整记录 |
| 查看历史分析、对话或计划 | 只展示当前访问的数据 |
| 关闭网页 | 不自动删除已写入磁盘的数据；可从原页面地址或历史列表恢复 |

前端使用随机 32 位十六进制访问标识，保存在页面地址的 `visit` 参数中，并通过 `X-Career-Session` 请求头传给后端。个人数据保存在 `DATABASE_PATH` 同目录的 `sessions/<访问标识>.db` 中；默认即 `data/sessions/`。知识库、向量索引和模型配置由所有访问共享。访问标识不是密码；使用本机时请勿将含 `visit` 的页面地址发给别人。

未携带访问标识的 API 调用继续使用 `DATABASE_PATH` 指定的旧数据库。因此，直接在 `/docs` 调用个人数据接口，默认不会读取浏览器本次访问的数据。

“新建”不删除旧数据库。若要备份，先停止前后端，再复制数据库、`sessions/` 目录和需要的索引；这些文件不上传 GitHub。当前没有自动清理旧会话的功能。访问标识只用于本地数据隔离，**不是身份认证或访问权限验证**。

## 知识库维护

### 资料放在哪里

| 目录 / 文件 | 作用 |
| --- | --- |
| `知识库/岗位招聘汇总_300版.xlsx` | 整理脚本实际读取的岗位台账 |
| `知识库/01_岗位能力/` 至 `05_面试准备/` | 原始岗位能力、招聘流程、时间安排、学习路径和面试指南 |
| `data/knowledge/generated/` | 从原件生成的 RAG Markdown 和生成文件清单 |
| `data/knowledge/learning_resources/` | 手工维护的课程、官方文档和学习入口 |
| `data/chroma/` | 本机生成的向量索引，不随仓库上传 |

仓库带有整理后的 Markdown，可以直接用关键词检索，不必先调用收费模型建立索引。根目录其他岗位汇总 Excel 是参考资料，整理脚本不会自动读取它们。

### 更新岗位与指南

修改 `知识库/` 中原始文件后，在项目根目录执行：

```powershell
.\.venv\Scripts\python.exe scripts/prepare_knowledge.py
```

脚本读取工作簿的“岗位台账”和“原始资料”工作表，只整理后端开发、前端开发、测试开发三个方向，并生成适用的指南副本。原始 Excel 和 Markdown 不被改写；生成目录中清单记录的过期资料会随整理更新，请不要手工编辑生成文件。

### 添加学习资料

在 `data/knowledge/learning_resources/` 新建 UTF-8 Markdown。下面是格式示例，链接需替换成实际资料地址：

```markdown
---
id: learning-example
title: 资料标题
job_category: backend
document_type: learning_resource
source_name: 官方文档或平台名称
source_url: https://example.com/course
recommendation_hint: 这份资料适合完成哪类任务
language: 简体中文
access_note: 免费阅读
updated_at: "填写实际检查日期"
review_status: not_reviewed
freshness: general
is_placeholder: false
---

资料内容、适用范围和学习建议。
```

`id` 在全部资料中应唯一；`job_category` 使用 `backend`、`frontend`、`testing` 或 `all`。标题和正文不能为空。新增这类手工文件不需要运行整理脚本；关键词检索读取文件，向量检索则需要更新索引。

### 建立或更新向量索引

确认后端已启动，服务地址、密钥和 `EMBEDDING_MODEL` 已正确配置：

```powershell
Invoke-RestMethod -Uri http://127.0.0.1:8002/knowledge/index -Method Post
Invoke-RestMethod -Uri http://127.0.0.1:8002/knowledge/status
```

首次索引会调用 Embedding API，耗时和费用取决于资料量与服务商。当前集合名为 `career_knowledge_v2`，按约 1,800 字符分块；再次入库会更新变化内容、同步元数据并移除过期片段。`source_documents` 是资料数，`indexed_chunks` 是片段数，两者不必相等。

切换 Embedding 模型时建议同时设置新的 `CHROMA_PATH` 并重新入库，避免不同模型的向量或维度混用。保留旧目录即可保留旧索引。

### 如何理解来源状态

- `verified`：原始台账标记为“已核实”，不表示系统实时重新核验。
- `pending_review`：原表注明待复核。
- `not_reviewed`：没有明确复核标记，不能视为已确认事实。

课程链接检查只说明检查当时可访问，不代表课程质量认证；通用团队指南默认未复核。新增内容应填写真实来源和实际检查日期，不能把示例链接作为可靠引用。

## 项目结构与实现

```text
Career-Guidance/
├── app/
│   ├── ui.py                    # Streamlit 页面、导航、访问会话
│   ├── ui_components.py         # 通用展示组件、来源与资源展示
│   ├── assets/workspace.css     # 工作台样式
│   ├── api.py                   # FastAPI 路由、校验、访问隔离
│   ├── db.py                    # SQLite 数据读写与访问数据库上下文
│   ├── services.py              # 模型请求、分析、咨询、计划与导出
│   ├── rag.py                   # Markdown 读取、分块、索引、检索
│   ├── catalog.py               # 三岗位定义、体验任务与示例资料
│   ├── dashboard.py             # 首页状态和体验反馈摘要
│   └── settings.py              # 环境变量与路径配置
├── .streamlit/config.toml       # Streamlit 主题及使用统计设置
├── .env.example                 # 无密钥配置模板
├── requirements.txt             # 运行依赖
├── requirements-dev.txt         # 测试依赖（包含运行依赖）
├── scripts/
│   ├── prepare_knowledge.py     # 整理原始知识库
│   ├── test_ui.py               # 界面回归测试
│   └── test_visit_sessions.py   # API、聊天和会话隔离测试
├── data/knowledge/
│   ├── generated/              # 已整理语料
│   └── learning_resources/     # 手工学习资料
├── 知识库/                      # 原始 Excel 与 Markdown
├── content/                     # 页面设计 HTML 草稿
├── docs/superpowers/
│   ├── specs/                  # 设计规格与更改说明
│   └── plans/                  # 实施与验收记录
├── .superpowers/brainstorm/     # 早期设计预览；运行状态文件不提交
├── 2026-09-29/                  # 早期项目计划存档
├── exports/                    # 本地产物，仓库仅保留空目录占位
├── 项目计划书.md                 # 项目背景与方案
└── 程序员工作内容说明.md          # 岗位参考说明
```

请求流程为：浏览器 → Streamlit → FastAPI → 业务服务 → SQLite / 知识检索 / 可选模型 API。Streamlit 控制页面与访问状态，FastAPI 负责数据和业务操作，SQLite 存储个人记录，Chroma 只保存知识向量索引。

`content/` 中的 HTML 是设计参考，不是应用入口；实际界面从 `app/ui.py` 启动。历史规格中可能包含尚未实现或已调整的方案，当前功能以代码及本 README 为准。欢迎页与会话更改参见 [访问行为说明](docs/superpowers/plans/2026-10-03-welcome-per-visit.md)，UI 改版参见 [设计规格](docs/superpowers/specs/2026-10-03-career-guidance-ui-redesign-design.md)。

## API 使用说明

后端默认基础地址为 `http://127.0.0.1:8002`，完整请求与响应结构见 `/docs`。岗位参数使用 `backend`、`frontend`、`testing`。

| 方法 | 路径 | 用途 |
| --- | --- | --- |
| GET | `/health`、`/status` | 健康、模型配置与检索状态 |
| GET | `/jobs` | 岗位及体验任务目录 |
| GET / PUT | `/profile` | 读取 / 保存画像 |
| POST | `/analysis/{job_category}` | 生成并保存分析 |
| GET | `/analyses` | 已保存分析列表 |
| POST | `/chat` | 咨询，传问题、岗位及可选对话 ID |
| GET | `/conversations` | 对话列表 |
| GET | `/conversations/{conversation_id}/messages` | 对话消息 |
| GET / POST | `/experience-feedback` | 读取 / 保存体验反馈 |
| POST | `/plans/{job_category}` | 生成计划，支持周期与周预算 |
| GET | `/plans` | 计划列表 |
| GET | `/plans/{plan_id}/markdown` | 返回包含 `markdown` 字段的 JSON |
| GET | `/knowledge/status` | 知识资料与索引数量 |
| POST | `/knowledge/index` | 建立 / 更新向量索引 |

### 使用独立 API 测试会话

以下命令在本地创建独立的测试画像，不写入旧数据库。后续请求复用同一个 `$careerHeaders`，才会访问同一份记录：

```powershell
$careerSession = [guid]::NewGuid().ToString('N')
$careerHeaders = @{ 'X-Career-Session' = $careerSession }
$careerProfile = @{ major = '软件工程'; skills = @('Python'); weekly_hours = 5 } | ConvertTo-Json
Invoke-RestMethod -Uri http://127.0.0.1:8002/profile -Method Put -Headers $careerHeaders -ContentType 'application/json; charset=utf-8' -Body ([System.Text.Encoding]::UTF8.GetBytes($careerProfile))
Invoke-RestMethod -Uri http://127.0.0.1:8002/profile -Headers $careerHeaders
```

访问标识必须是 32 位小写十六进制字符，否则返回 HTTP 400。参数不符合接口定义通常返回 422；当前访问下不存在的计划导出返回 404。知识库索引缺少 Embedding 配置时可能返回 409，服务或索引失败时可能返回 503。

## 开发与测试

在根目录安装测试依赖并运行：

```powershell
.\.venv\Scripts\python.exe -m pip install -r requirements-dev.txt
.\.venv\Scripts\python.exe -m unittest discover -s scripts -p 'test_*.py' -v
.\.venv\Scripts\python.exe -m compileall -q app scripts
```

测试采用 Streamlit AppTest 和 FastAPI TestClient，使用模拟模型 / API 与临时数据库，不需要启动 8002 或 8501 服务，也不调用外部模型。覆盖欢迎入口、画像、岗位切换、计划、导出入口、访问隔离、聊天隔离、并发访问、刷新恢复、历史导入和新建。

自动化测试不能证明真实模型或 Embedding 服务可用。接入实际配置后，可以按“填写画像 → 选择岗位 → 更新分析 → 提问 → 生成计划 → 下载 → 刷新 → 新建 → 导入历史”的顺序做一次人工验收，并检查来源及模式提示。

## 常见问题

| 现象 | 处理方式 |
| --- | --- |
| 找不到 `.venv\Scripts\python.exe` | 确认终端位于项目根目录，先执行 `python -m venv .venv` |
| `ModuleNotFoundError` | 使用虚拟环境 Python 重新安装 `requirements.txt`；测试缺 `httpx` 时安装 `requirements-dev.txt` |
| Streamlit 按钮或容器参数报错 | 需要 Streamlit 1.50 或更新的 1.x，重新安装依赖；不要误用全局旧版本 |
| 打开 8002 只看到 JSON | 8002 是后端；用户界面在 8501 |
| 页面提示“工作台正在等待连接” | 确认后端仍运行，用 `/health` 检查；核对 `API_PORT` 或 `CAREER_API_URL` 后重启前端 |
| 端口被占用 | 选择其他空闲端口；改后端端口时同步修改前端 `.env` 的 `API_PORT` |
| 一直显示本地演示 | 检查三项聊天配置、服务余额、模型名和兼容接口；修改 `.env` 后重启进程 |
| 分析或计划较慢 | 真实服务请求需要时间；计划模型请求最长等待约 90 秒，失败时查看警告，不要连续重复点击 |
| 有资料却显示关键词检索 | 检查 `EMBEDDING_MODEL`、索引是否建立和模型服务；关键词检索本身可正常使用 |
| 向量维度不匹配 | 可能更换了 Embedding 模型；换新 `CHROMA_PATH`，重启后端并重新入库 |
| 更新原件后页面仍是旧内容 | 先执行整理脚本，向量检索还需更新索引；已有分析 / 计划需要重新生成 |
| 刷新后找不到之前的计划 | 检查地址中是否保留 `visit` 参数；也可以在左侧“导入历史记录”选择原记录 |
| API 看不到网页里的记录 | API 未携带同一 `X-Career-Session` 时，访问的是不同数据库 |
| 启动时询问 Email | 是 Streamlit 自身提示，不是项目登录；可以留空按回车，配置已关闭使用统计 |
| 测试出现 `missing ScriptRunContext` / Pydantic 弃用提示 | 测试环境可能输出这些警告；判断通过看结尾 `OK`、失败列表及退出码 |

更改后端端口的例子：在 `.env` 设置 `API_PORT=8010`，后端命令改为 `--port 8010`。如果设置了 `CAREER_API_URL`，它的优先级更高，也要同步修改。前端仍可以使用 8501。

## 仓库内容与协作

仓库保留应用源码、依赖说明、测试、设计草稿、实施文档、原始知识库与已整理语料。安装依赖后可在新电脑重建运行环境。

以下内容只保存在本地，由 [.gitignore](.gitignore) 排除：真实 `.env`、Streamlit secrets、虚拟环境、Python 缓存、用户 SQLite 数据库及辅助文件、会话记录、Chroma 索引、日志、导出文件和预览服务运行状态。`.env.example` 只包含配置名称和非敏感默认值。

更新代码前先保存本地修改，再执行 `git pull`；依赖变化后重新安装 requirements。更改原始知识资料时，同步运行整理脚本并提交相应语料变化；新增功能时补充说明和适当测试。

本项目尚未附加开源许可证。公开可见不等于已授予任意使用许可；第三方招聘与学习资料仍遵循各自来源的使用条件。
