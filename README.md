# my-cron

基于 GitHub Actions 的定时任务仓库，通过 Workflow 的 `schedule`（cron）触发，托管各类周期性任务。

## 计划中的任务

- [ ] 每日定时向指定邮箱发送邮件

## 目录结构

```
.github/workflows/   # GitHub Actions 工作流（定时任务定义）
```

## 使用说明

1. 任务以 Workflow 形式添加到 `.github/workflows/` 下，使用 `schedule` 触发器配置 cron 表达式（UTC 时间）。
2. 涉及敏感信息（如邮箱账号密码）时，请配置在仓库的 `Settings → Secrets and variables → Actions` 中。
3. Actions 定时任务可能有数分钟级延迟，且默认分支空闲 60 天后会被自动禁用，需注意维护。

## License

MIT
