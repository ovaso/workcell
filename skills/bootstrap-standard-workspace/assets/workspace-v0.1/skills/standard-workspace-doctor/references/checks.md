# Doctor 检查目录

## 严重级别

- `ERROR`：结构或真相源无效、安全策略放行、权限越界、所有权冲突，或者进入当前生命周期所需条件缺失。阻止 `READY`。
- `WARN`：工作区仍可只读使用，但存在缺少证据、可选元数据、过期风险或维护问题。
- `INFO`：已确认的正常事实。

## 确定性结构检查

- 必需入口存在且非空：`AI_WORKSPACE.md`、`AGENTS.md`、`.ai-workspace/workspace.toml`、`.ai-workspace/versions.lock`、`skills/`。
- 标准目录存在：`environment`、`project`、`mirror`、`remotes`、`requirements`、`workspaces`、`diagnostics`、`tools`、`knowledge`、`docs`、`memory`。
- TOML 与 JSON 真相源可解析；路径为安全的工作区相对路径。
- 工作区状态属于规范状态；不得通过跳写 `READY` 掩盖缺失门禁。
- 运行时 Skill 的目录名、frontmatter 名称和描述有效，不能保留模板 TODO。
- `agents/openai.yaml` 等平台适配元数据不是通用工作区运行时健康条件；其发行完整性由对应平台或产品仓库级测试负责，Doctor 不因缺少某个平台适配器而告警。
- `.ai-workspace/ownership.toml` 的规则必须唯一、路径安全，owner 属于 `distribution/generated/workspace`；`.ai-workspace/distribution.manifest` 中的路径必须存在、不能逃出工作区，并且每个路径都要有完全同名的 `distribution` 规则，不能只依赖 `/**` 等泛化规则。

## JSON Schema 一致性检查

- Doctor 必须直接使用展开工作区随包的 `.ai-workspace/schemas/environment-facts.schema.json` 与 `.ai-workspace/schemas/project-plugin.schema.json`，不能依赖本机另装的 Schema 库或仓库外副本。
- 环境事实 Schema 必须同时接受 `.ai-workspace/templates/host-facts.json` 与 `environment/current/host-facts.json`。
- 项目插件 Schema 必须接受 `.ai-workspace/templates/project-plugin.json`；`project/plugin/project-plugin.json` 存在时也必须接受同一 Schema 校验。
- V0.1 校验子集覆盖 `$ref`、`allOf`、`not`、`const`、`enum`、`type`、`required`、`properties`、`additionalProperties`、`items`、`minItems`、`uniqueItems`、`minLength`、`maxLength`、`pattern`、`format: date-time`、`propertyNames` 与 `minimum`。
- `$ref` 只允许指向当前 Schema 文档的 JSON Pointer。Schema 缺失、JSON 不合法、对象键重复、引用无法解析、约束参数非法或出现未支持的关键字均报告 `ERROR`，避免升级后的新约束被旧 Doctor 静默忽略。
- 模板与实例任一字段不符合随包 Schema 均报告 `schema.instance-invalid`；错误信息必须保留实例与 Schema 的 JSON Pointer，便于区分 Schema 漂移、模板漂移和运行时事实漂移。
- 校验过程必须只读，不联网、不写缓存、不自动修复或改写 JSON。

## 安装 Release 收据检查

- `.ai-workspace/release-manifest.json` 是展开工作区的必需自托管收据，必须接受 `.ai-workspace/schemas/release-manifest.schema.json` 校验。
- 收据 `release_version` 必须与 `.ai-workspace/versions.lock` 的 `versions.product` 完全一致。
- 对 `files[].owner = "distribution"` 的每个普通文件，Doctor 必须拒绝缺失路径、任一路径组件符号链接、目录或其他非普通文件，并流式核对当前 SHA-256。收据自身不参与自哈希。
- `generated` 与 `workspace` 条目只记录安装基线，允许运行时生成、修改或删除，Doctor 不把其哈希变化报告为发行漂移。
- 哈希校验期间若文件对象被替换或元数据发生变化，按竞态错误失败关闭；Doctor 不自动恢复发行文件。

## 任务检查

- `requirements/<task-id>/task.toml` 可解析，任务 ID 与目录一致，状态只属于：`INBOX`、`SCOPED`、`PLANNED`、`READY`、`IMPLEMENTING`、`VERIFYING`、`DEV_FEEDBACK`、`TEST_FEEDBACK`、`QC_READY`、`RELEASE_READY`、`DONE`、`PAUSED`、`ARCHIVED`。
- 模块角色只使用 `scope.edit/verify/reference/excluded`，同一模块不得重复出现。
- `task.project_plugin_ref` 必须精确指向标准真相源 `project/plugin/project-plugin.json`；路径任一组件不得是符号链接，JSON 必须通过严格解析与项目插件 Schema 校验。
- 任务角色不得宽于项目插件 `modules[].role`：`reference < verify < edit`。
- 任务范围、授权、风险、门禁和证据路径应为机器可读；缺失时报告警告或按当前状态升级为错误。
- `READY` 之后的任务必须已有确认范围和计划；`DONE` 必须已有验证证据；`ARCHIVED` 必须保留最终摘要和可追溯提交信息。

## 诊断检查

- `unconfigured` 时只允许本地代码和已有文件分析，远端动作必须关闭。
- `verified` 必须由交互问询配置，并使用 `default_action = "deny"`；凭证只能是引用。
- 目标、Provider、授权和事实过期条件完整；引用文件存在且路径安全。
- 诊断硬约束已进入实际生效的 AI 适配规则。
- Provider 可用性、端点连通性和当前授权是三类事实，不能互相替代。

## 只读人工检查

脚本无法独立证明以下事项，应在需要时补查：

- `AGENTS.md` 等生成适配器是否与结构化策略同源、是否已过期；
- 项目模块、默认分支、构建、测试和高风险链路是否仍与代码一致；
- Git 工作树、ahead/behind、远端 URL 和当前分支是否符合项目策略；
- 环境事实是否在适用上下文和有效期内；
- 升级候选是否来自不可变 Release，哈希或签名是否验证；
- 任务证据是否真实对应当前提交和环境。

任何需要联网、刷新远端引用、运行服务或查询外部平台的验证都先说明动作并取得授权。

## 修复优先级

1. 先修安全默认值、解析失败、路径逃逸和角色越权。
2. 再修生命周期门禁、所有权与生成文件漂移。
3. 再补缺失事实、任务证据和 UI 元数据。
4. 最后处理格式、说明性警告和可选维护项。

每次修复后重新执行全部检查，避免局部通过掩盖其他错误。
