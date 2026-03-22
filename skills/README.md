# skills

本目录存放当前项目自有的 `DeepAgent skills`。

可执行的 Python 逻辑位于 `core/`；这里保留的是给 `DeepAgent` 读取的 skill 定义和使用约束。

设计原则：

- 只放固定、可重复、输入输出明确的工作流
- 不在 skill 中保存长期状态
- 不在 skill 中创建长期任务或主动推送
- 不把用户偏好、长期记忆或业务边界写死进单个 skill

当前首批 skills：

- `blog-fetch`
  - 获取技术博客正文并做基础清洗
  - 默认跟踪：
    - `https://blog.langchain.com`
    - `https://karpathy.bearblog.dev/blog/`
    - `https://baoyu.io`
- `news-normalize`
  - 将新闻内容整理成结构化候选结果
- `briefing-compose`
  - 将候选内容整理成简报草稿

这些 skill 只负责完成具体步骤，不负责决定何时执行或推送给谁。
