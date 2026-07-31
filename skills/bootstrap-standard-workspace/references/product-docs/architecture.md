# 架构说明

## 源码仓库与嵌套 Skill

`std-workspace` 是独立 Git 源码仓库，不是某个已展开的标准工作区。仓库级文档、许可证、Specs、Schemas 和构建测试与 `skills/` 同级。标准协议面向不同 AI 平台，V0.1 的确定性引导脚本则以 POSIX `sh` 为宿主基线：

```text
std-workspace/
├── README.md
├── LICENSE
├── LICENSES/
├── docs/
├── specs/
├── schemas/
├── scripts/
├── tests/
└── skills/
    └── bootstrap-standard-workspace/
        ├── SKILL.md
        └── assets/workspace-v0.1/
            └── skills/   # 展开后工作区自己的运行时 Skills
```

外层 Bootstrap Skill 是分发与自举入口；内层 Skills 属于展开后的工作区。二者生命周期和职责不同。

## 总体结构

```text
Bootstrap 发行层
  -> 标准工作流内核
  -> 宿主环境事实层
  -> 通用技术适配器
  -> 项目插件
  -> 项目实例
  -> 项目能力插件
  -> 任务实例
```

## Bootstrap 发行层

负责 `create / validate / repair / upgrade`，稳定版本后再增加安全自更新。Bootstrap 是安装介质，不承担项目日常开发。

## 标准工作流内核

定义工作区和任务生命周期、证据模型、文件所有权、AI 上下文装配、安全约束和多代理协作边界。内核不得包含项目名称、服务器地址或业务规则。

## 宿主环境事实层

第一阶段只管理：已安装命令、工具链、环境变量、网络环境。事实必须记录来源、上下文、观测时间、可信度、敏感级别和过期信息。

## 通用技术适配器

承载 Git、Maven、Spring Boot、Node、SQL、Docker、Kubernetes 等跨项目能力。项目插件只声明组合和覆盖项。

## 项目插件与项目实例

项目插件保存稳定项目差异：仓库、模块、分支、构建、测试、风险和特化能力。项目实例保存本机绑定和实时状态：路径、远端、环境变量引用、镜像、工作区、dirty/ahead/behind。

## 项目能力插件

诊断是第一个正式能力插件。未来还可增加 Review、发布、迁移、性能和安全能力。能力插件由项目插件启用和配置，但遵循统一 API。

## 任务实例

需求、缺陷、诊断和 Review 都是任务。任务记录状态、计划、模块角色、风险、下一步、门禁、环境快照及证据。

## 文件所有权

```text
distribution：发行版维护
generated：事实编译结果
workspace：用户、项目和任务维护
```

升级只能替换 `distribution`，重新编译 `generated`，完整保留 `workspace`。

## 实践反馈与标准演进

工作区通过 `extract-standard-feedback` 从已授权材料提炼脱敏候选，并写入 `feedback/`；这不是标准变更，也不会自动联网回传。标准仓库的 `integrate-workspace-feedback` 只处理用户明确导入的候选，生成待审核提案。只有聚合独立证据、完成兼容性与所有权评估并得到用户确认后，才允许修改 Specs、Schemas、Skills、Assets 和版本。
