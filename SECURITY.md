# Security

本项目仓库对外公开。

## 不应进入仓库的内容

- `.env` 和任何本地环境变量文件
- `memories/` 中的长期记忆和聊天相关数据
- `.obsidian/` 等编辑器私有配置
- 日志、数据库、缓存、运行快照
- 真实 Telegram bot token、OpenAI API key、chat id、Cookie、券商凭证

## 运行边界

- 当前只支持研究、摘要、提醒和模拟交易
- 不接入真实券商，不保存真实交易凭证
- 公开仓库中的配置示例必须使用占位值
- bot 启动必须显式限制 `TELEGRAM_ALLOWED_CHAT_IDS`
- `TELEGRAM_PUSH_CHAT_IDS` 不得超出允许聊天白名单

## 泄露处理

如果任何密钥、令牌或账户信息曾在公开渠道暴露，应立即轮换，不应继续复用。
