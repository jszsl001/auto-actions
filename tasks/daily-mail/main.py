"""每日定时邮件任务。

每天 09:10(北京时间)向多个收件人发送一封内容可自定义的邮件,
由 GitHub Actions 的 schedule 触发,也可手动触发测试。

配置来源(优先级从高到低):
  1. 命令行参数(--to / --subject / --file)
  2. workflow_dispatch 手动输入(INPUT_TO / INPUT_SUBJECT / INPUT_BODY / INPUT_HTML)
  3. 仓库 Variables/Secrets(MAIL_TO / MAIL_SUBJECT / MAIL_HTML + SMTP_*)
  4. 默认值(正文读本目录 content.md,主题 "每日定时邮件 YYYY-MM-DD")

正文支持模板变量:{{date}}(当日日期)、{{weekday}}(星期几),按北京时间解析。

用法:
  python tasks/daily-mail/main.py [--dry-run] [--to a@x.com,b@x.com] [--subject S] [--file body.md]
"""

from __future__ import annotations

import argparse
import os
import re
import sys
from datetime import datetime, timedelta, timezone
from html import escape
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from lib.mailer import Mailer, MailMessage, mask_addr, split_addresses  # noqa: E402

CONTENT_FILE = Path(__file__).resolve().parent / "content.md"
BJT = timezone(timedelta(hours=8))  # 北京时间
TRUTHY = {"1", "true", "yes", "on", "y"}
FALSY = {"0", "false", "no", "off", "n"}
URL_RE = re.compile(r"(https?://[^\s<>\"']+)")


def first_of(*values) -> str:
    """返回第一个非空值。"""
    for value in values:
        if value:
            return value
    return ""


def env(name: str) -> str:
    return (os.environ.get(name, "") or "").strip()


def dispatch_input(name: str) -> str:
    """workflow_dispatch 手动输入(GitHub 注入为 INPUT_<NAME> 环境变量)。"""
    return env(f"INPUT_{name}")


def fill_template(text: str) -> str:
    """替换模板变量 {{date}} / {{weekday}}(按北京时间)。"""
    now = datetime.now(BJT)
    weekday = "星期" + "一二三四五六日"[now.weekday()]
    return text.replace("{{date}}", now.strftime("%Y-%m-%d")).replace("{{weekday}}", weekday)


def resolve_html() -> bool:
    """HTML 开关:INPUT_HTML / MAIL_HTML 显式设置时生效,默认开。"""
    raw = first_of(dispatch_input("HTML"), env("MAIL_HTML")).lower()
    if raw in TRUTHY:
        return True
    if raw in FALSY:
        return False
    return True  # 默认使用 HTML,保证样式


def wrap_html(text: str) -> str:
    """把纯文本正文包装成内联样式的 HTML 邮件(零依赖,兼容各邮箱客户端)。"""
    escaped = escape(text)
    escaped = URL_RE.sub(r'<a href="\1" style="color:#1a73e8;">\1</a>', escaped)
    paragraphs = [p.strip() for p in escaped.split("\n\n") if p.strip()]
    body_html = "".join(
        f'<p style="margin:0 0 14px;line-height:1.8;">{p.replace(chr(10), "<br>")}</p>'
        for p in paragraphs
    )
    return (
        '<div style="font-family:-apple-system,\'Segoe UI\',\'Microsoft YaHei\',sans-serif;'
        'max-width:560px;margin:0 auto;padding:24px;color:#333;">'
        '<div style="background:#f0f6ff;border-left:4px solid #1a73e8;border-radius:6px;'
        f'padding:18px 20px;font-size:15px;">{body_html}</div>'
        '<p style="margin:14px 0 0;font-size:12px;color:#999;">'
        '本邮件由 auto-actions 定时任务自动发送,请勿回复。</p>'
        "</div>"
    )


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="每日定时邮件任务")
    parser.add_argument("--to", help="收件人,逗号分隔(覆盖 MAIL_TO)")
    parser.add_argument("--subject", help="邮件主题(覆盖 MAIL_SUBJECT)")
    parser.add_argument("--file", help="正文文件路径(默认 tasks/daily-mail/content.md)")
    parser.add_argument("--dry-run", action="store_true", help="只构造邮件并打印摘要,不实际发送")
    return parser.parse_args()


def load_body(args: argparse.Namespace) -> tuple:
    """返回 (正文内容, 来源说明)。"""
    if args.file:
        path = Path(args.file)
        if not path.is_file():
            raise FileNotFoundError(f"正文文件不存在:{path}")
        return path.read_text(encoding="utf-8"), str(path)
    manual = dispatch_input("BODY")
    if manual:
        return manual, "workflow_dispatch 输入"
    if not CONTENT_FILE.is_file():
        raise FileNotFoundError(f"默认正文不存在:{CONTENT_FILE}")
    return CONTENT_FILE.read_text(encoding="utf-8"), str(CONTENT_FILE)


def print_dry_run_summary(message: MailMessage, body_source: str) -> None:
    print("[task] --dry-run:邮件已构造,未发送")
    print(f"[task] 收件人({len(message.to)}):{', '.join(message.to)}")
    print(f"[task] 主题:{message.subject}")
    print(f"[task] 格式:{'HTML' if message.html else '纯文本'}")
    print(f"[task] 正文来源:{body_source},长度 {len(message.body)} 字符")
    print(f"[task] SMTP:{env('SMTP_HOST') or '(未配置)'}:{env('SMTP_PORT') or 465},"
          f"账号 {mask_addr(env('SMTP_USER')) or '(未配置)'}")
    preview = message.body if len(message.body) <= 300 else message.body[:300] + "…"
    print("[task] 正文预览:")
    print(preview)


def main() -> int:
    args = parse_args()

    recipients = split_addresses(first_of(args.to, dispatch_input("TO"), env("MAIL_TO")))
    if not recipients:
        print("[task] 错误:未配置收件人(命令行 --to / 手动输入 / 仓库变量 MAIL_TO)", file=sys.stderr)
        return 2

    try:
        body, body_source = load_body(args)
    except OSError as error:
        print(f"[task] 错误:{error}", file=sys.stderr)
        return 1

    use_html = resolve_html()
    if use_html and not body.lstrip().startswith("<"):  # 已是 HTML 的正文不再包装
        body = wrap_html(body)

    message = MailMessage(
        to=recipients,
        subject=fill_template(first_of(args.subject, dispatch_input("SUBJECT"), env("MAIL_SUBJECT"),
                                       "每日定时邮件 {{date}}")),
        body=fill_template(body),
        html=use_html,
    )

    if args.dry_run:
        print_dry_run_summary(message, body_source)
        return 0

    host = env("SMTP_HOST")
    port = int(env("SMTP_PORT") or "465")
    user = env("SMTP_USER")
    password = os.environ.get("SMTP_PASS", "")
    missing = [name for name, value in
               (("SMTP_HOST", host), ("SMTP_USER", user), ("SMTP_PASS", password)) if not value]
    if missing:
        print(f"[task] 错误:缺少 SMTP 配置 {missing}(仓库 Settings → Secrets and variables → Actions)",
              file=sys.stderr)
        return 2

    Mailer(host=host, port=port, user=user, password=password).send(message)
    return 0


if __name__ == "__main__":
    sys.exit(main())
