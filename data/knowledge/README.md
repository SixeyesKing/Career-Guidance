# 知识资料目录

原始材料保存在项目根目录 `知识库/`；自动整理后的 RAG 语料位于 `generated/`。运行 `python scripts/prepare_knowledge.py` 可重新生成，原件不会被修改。

生成文件带 YAML 元数据，包括岗位类别、资料类型、来源、更新时间、复核状态和稳定 ID。复核状态含义：`verified` 仅表示原始台账标为“已核实”，`pending_review` 表示待复核，`not_reviewed` 表示没有可确认的复核标记。通用团队指南默认未复核，不会被显示为已核验的外部事实。

配置 Embedding 后调用 `POST /knowledge/index` 建立或更新 Chroma 的 `career_knowledge_v2` 分块索引。没有可用 Embedding 时仍可通过关键词检索。新增手工 Markdown 时请使用与生成语料相同的 YAML 字段，不要填写虚构来源。

公开学习资料入口整理在 `learning_resources/`，按后端、前端和测试开发方向分别标注用途。文件中的“链接检查日期”只说明当日页面可访问，不代表项目组认证了课程质量、完整性或学习效果；英语页面会单独标注。资料接入后，推荐应结合具体任务筛选，而不是默认要求用户完成全部资源。
