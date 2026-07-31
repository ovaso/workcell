# Changelog

本文件记录 AI Native Standard Workspace 产品仓库的发行级变化。设计讨论过程保存在 `docs/session-summary.md`，不在此重复。

## [Unreleased]

- 等待确定唯一公开仓库、正式许可证和首个不可变 Release。
- 增加工作区实践反馈与标准演进协议：反馈先脱敏导出、再导入为待审核提案，禁止自动回传、采纳和升级。

## [0.1.0] - 2026-07-31

- 建立独立标准 Git 源码仓库。
- 定义工作区、序列化、环境事实、项目插件、诊断、任务、AI 指令和升级规范。
- 提供自包含 `bootstrap-standard-workspace` Skill 与 V0.1 工作区资产。
- 提供环境初始化、环境扫描、项目适配、诊断配置、Doctor、任务启动和升级运行时 Skills。
- 提供 Bootstrap 创建、校验、修复计划、Schema 校验、打包与黑盒测试。
- 增加安装 Release 完整性收据、first-match 所有权哈希和升级末步收据替换协议。
- 加固 Bundle 元数据、祖先符号链接、非空目标与创建竞态的失败关闭测试。
- 让 Doctor 使用无第三方依赖的 JSON Schema 子集校验环境事实、模板和项目插件。
- 将会话溯源保留在源码仓库，发行 Skill 只携带通用文档、决策和工具能力种子知识。
- 明确 AI 平台中立与宿主平台支持是独立维度；V0.1 引导脚本基线为 POSIX `sh`。
