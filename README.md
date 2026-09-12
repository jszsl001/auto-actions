# auto-actions

基于 GitHub Actions 的定时任务仓库，通过 Workflow 的 `schedule`（cron）触发，托管各类周期性任务。

## 任务

- [x] 每日提醒查看电价数据（price-reminder）

## 目录结构

```
.github/workflows/   # GitHub Actions 工作流（每个任务一个文件）
lib/
  mailer.py          # 公共能力：SMTP 邮件发送（收件人解析/重试/SSL 自适应/HTML 包装）
tasks/               # 具体任务，每个任务一个独立目录（按业务命名）
  price-reminder/
    main.py          # 任务入口：组装配置与正文，调用 lib 发送
    content.md       # 默认邮件正文（改此文件即自定义内容，支持 {{date}}/{{weekday}}）
```

## price-reminder 配置说明

在仓库 `Settings → Secrets and variables → Actions` 中配置：

| 类型 | 名称 | 说明 | 示例 |
| --- | --- | --- | --- |
| Secret | SMTP_HOST | SMTP 服务器地址 | smtp.qq.com |
| Secret | SMTP_PORT | 端口（465 SSL / 587 STARTTLS） | 465 |
| Secret | SMTP_USER | 发件邮箱 | xxx@qq.com |
| Secret | SMTP_PASS | SMTP 授权码（非登录密码） | xxxx |
| Variable | MAIL_TO | 收件人，多个用逗号分隔 | a@x.com,b@y.com |
| Variable | MAIL_SUBJECT | 主题，可选，默认 `电价数据提醒 YYYY-MM-DD` | 电价提醒 |
| Variable | MAIL_HTML | 可选，设为 `false` 时正文发纯文本（默认 HTML） | false |

- 正文默认读取 `tasks/price-reminder/content.md`，支持模板变量 `{{date}}`（当日日期）、`{{weekday}}`（星期几）。
- 手动测试：Actions 页面 Run workflow，可临时覆盖收件人/主题/正文/HTML 开关。
- 本地测试（不发送）：`python tasks/price-reminder/main.py --dry-run`。
- QQ/163 等邮箱需先在网页邮箱设置中开启 SMTP 服务并生成授权码。

## 新增任务指引

1. 在 `tasks/<任务名>/` 下创建 `main.py`（入口）与可选的 `content.md`，复用 `lib/mailer.py` 发送。
2. 复制任一现有 workflow 改名，指向新任务入口，按业务命名（如 `xxx-reminder.yml`）。
3. 任务命名用业务含义（不含 "mail" 字样），发邮件能力统一由 `lib` 提供。

## 使用说明

1. 任务以 Workflow 形式添加到 `.github/workflows/` 下，使用 `schedule` 触发器配置 cron 表达式（UTC 时间）。
2. 涉及敏感信息（如邮箱账号密码）时，请配置在仓库的 `Settings → Secrets and variables → Actions` 中。
3. Actions 定时任务可能有数分钟级延迟，且默认分支空闲 60 天后会被自动禁用，需注意维护。

## License

MIT
