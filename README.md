# auto-actions

基于 GitHub Actions 的定时任务仓库，通过 Workflow 的 `schedule`（cron）触发，托管各类周期性任务。

## 任务

- [x] 每日定时向指定邮箱发送邮件（daily-mail）

## 目录结构

```
.github/workflows/   # GitHub Actions 工作流（定时任务定义）
lib/
  mailer.py          # 公共能力：SMTP 邮件发送（收件人解析/重试/SSL 自适应）
tasks/               # 具体任务，每个任务一个独立目录
  daily-mail/
    main.py          # 任务入口：组装配置与正文，调用 lib 发送
    content.md       # 默认邮件正文（改此文件即自定义内容，支持 {{date}}/{{weekday}}）
```

## daily-mail 配置说明

在仓库 `Settings → Secrets and variables → Actions` 中配置：

| 类型 | 名称 | 说明 | 示例 |
| --- | --- | --- | --- |
| Secret | SMTP_HOST | SMTP 服务器地址 | smtp.qq.com |
| Secret | SMTP_PORT | 端口（465 SSL / 587 STARTTLS） | 465 |
| Secret | SMTP_USER | 发件邮箱 | xxx@qq.com |
| Secret | SMTP_PASS | SMTP 授权码（非登录密码） | xxxx |
| Variable | MAIL_TO | 收件人，多个用逗号分隔 | a@x.com,b@y.com |
| Variable | MAIL_SUBJECT | 主题，可选，默认 `每日定时邮件 YYYY-MM-DD` | 每日签到提醒 |
| Variable | MAIL_HTML | 可选，设为 `1` 时正文按 HTML 发送 | 1 |

- 正文默认读取 `tasks/daily-mail/content.md`，支持模板变量 `{{date}}`（当日日期）、`{{weekday}}`（星期几）。
- 手动测试：Actions 页面 Run workflow，可临时覆盖收件人/主题/正文/HTML 开关。
- 本地测试（不发送）：`python tasks/daily-mail/main.py --dry-run`。
- QQ/163 等邮箱需先在网页邮箱设置中开启 SMTP 服务并生成授权码。

## 使用说明

1. 任务以 Workflow 形式添加到 `.github/workflows/` 下，使用 `schedule` 触发器配置 cron 表达式（UTC 时间）。
2. 涉及敏感信息（如邮箱账号密码）时，请配置在仓库的 `Settings → Secrets and variables → Actions` 中。
3. Actions 定时任务可能有数分钟级延迟，且默认分支空闲 60 天后会被自动禁用，需注意维护。

## License

MIT
