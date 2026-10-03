# 向前职业规划工作台 UI 改版实施计划

**Goal:** 将 content 草稿与 docs 已明确的工作台设计落实到五个真实 Streamlit 页面。
**Architecture:** 保留 FastAPI、SQLite 和全部业务接口；拆出独立 CSS 和展示组件，使用原生 Streamlit 控件实现交互。页面布局统一为侧边导航、页头、主要操作与内容区。
**Tech Stack:** Python、Streamlit 1.50、CSS、FastAPI。
**Spec:** ../specs/2026-10-03-career-guidance-ui-redesign-design.md

## 设计决策

- 延续草稿 A1 工作台，中文文案；浅灰白背景、白色面板、墨绿主色、橙色待确认提示。
- 采用 14–16px 正文、30px 页面标题、36px 首页重点标题，4–8px 圆角。移除层层卡片、微小正文、持续动效和默认红色控件。
- 原生输入与按钮可通过键盘操作；手机内容单列，侧边栏可折叠；减少动效偏好生效。
- 所有统计与状态使用真实接口数据，未知不等于不足。模型已配置不等于连接成功。
- 已有 content 草稿与更改规格提供设计依据，本轮用户已要求直接完成改造。

## 实施任务

- [x] 创建 app/ui_components.py、app/assets/workspace.css、.streamlit/config.toml，统一视觉变量、页头、状态和资料展示。
- [x] 改造 app/ui.py 的侧边栏与首页：真实下一步、画像摘要、时间预算、最近记录和岗位入口。
- [x] 重排画像与岗位探索：分区表单、三岗位整体卡片、独立可选体验区、清晰的选择与下一步操作。
- [x] 重排分析与咨询：岗位工具条、已知/待确认并列、行动建议、可展开依据和历史记录。
- [x] 重排行动计划：设置工具区、同岗位历史版本、周目标与任务、时间预算和真实学习资料链接、Markdown 导出。
- [x] 使用隔离的请求数据运行 Streamlit AppTest，覆盖空画像、部分画像、历史记录、岗位切换、表单保存、反馈、分析、咨询和计划导出。
- [x] 启动本地前后端，验证只读 API 和五个页面；浏览器检查桌面和窄屏，保存验收说明。

## 重点检查

用户长文本与 HTML 字符必须安全显示；岗位切换不能混入其他岗位的分析或聊天；历史计划不得误标当前岗位；无后端时避免堆叠错误；无资料或模型回退必须准确标注。用户现有数据库不用于写入测试。

## 验收结果

- 8 项 Streamlit AppTest 全部通过；测试请求被隔离，不写入用户数据库、不调用外部模型。
- `/health`、`/status`、`/profile`、`/jobs`、`/analyses`、`/plans`、`/conversations`、`/experience-feedback`、`/knowledge/status` 均返回 200，前端健康检查返回 200。
- 浏览器检查五页真实历史内容；1440px 桌面和 390px 手机下的首页、岗位和计划内容无横向溢出；手机导航已验证展开、切换与折叠。
- 浏览器未记录 JavaScript error。实际模型生成未通过验收浏览器新增调用；写入流程与回退模式由隔离交互测试覆盖。
- 截图保存在 `exports/ui-workspace-desktop.jpg` 和 `exports/ui-mobile-roles.jpg`。
