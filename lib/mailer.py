"""通用邮件发送能力(纯 Python 标准库,零依赖)。

与具体任务解耦:本模块只负责 SMTP 发送,
收件人/主题/正文由调用方组装后传入。
"""

from __future__ import annotations

import re
import smtplib
import ssl
import time
from dataclasses import dataclass, field
from email.header import Header
from email.mime.text import MIMEText
from email.utils import formataddr


def split_addresses(raw: str | None) -> list:
    """把逗号/分号/空白分隔的地址串解析为去重后的地址列表。"""
    if not raw:
        return []
    items = re.split(r"[,;\s]+", raw.strip())
    return list(dict.fromkeys(item for item in items if item))


def mask_addr(addr: str) -> str:
    """日志脱敏:u***r@example.com。"""
    if not addr:
        return ""
    if "@" not in addr:
        return addr[:1] + "***"
    name, domain = addr.split("@", 1)
    return f"{name[:1]}***@{domain}"


@dataclass
class MailMessage:
    """一封待发送的邮件。"""

    to: list  # 收件人地址列表(必填)
    subject: str  # 主题(必填)
    body: str  # 正文(必填)
    html: bool = False  # True 时正文按 HTML 发送,否则纯文本
    cc: list = field(default_factory=list)  # 抄送(可选)
    from_name: str = ""  # 发件人显示名(可选)


class Mailer:
    """SMTP 发送器:465 端口自动走 SSL,其余走 STARTTLS,失败自动重试。"""

    def __init__(
        self,
        host: str,
        port: int = 465,
        user: str = "",
        password: str = "",
        use_ssl: bool | None = None,  # None=按端口自动判断
        retries: int = 2,
        retry_delay: float = 3.0,
        timeout: float = 30.0,
    ) -> None:
        if not host:
            raise ValueError("缺少 SMTP 服务器地址(SMTP_HOST)")
        self.host = host
        self.port = port
        self.user = user
        self.password = password
        self.use_ssl = (port == 465) if use_ssl is None else use_ssl
        self.retries = retries
        self.retry_delay = retry_delay
        self.timeout = timeout

    def log(self, message: str) -> None:
        print(f"[mailer] {message}", flush=True)

    def _connect(self) -> smtplib.SMTP:
        if self.use_ssl:
            server = smtplib.SMTP_SSL(self.host, self.port, timeout=self.timeout)
        else:
            server = smtplib.SMTP(self.host, self.port, timeout=self.timeout)
            server.starttls(context=ssl.create_default_context())
        if self.user:
            server.login(self.user, self.password)
        return server

    def _build_mime(self, message: MailMessage) -> MIMEText:
        mime = MIMEText(message.body, "html" if message.html else "plain", "utf-8")
        mime["Subject"] = str(Header(message.subject, "utf-8"))  # 非中文 ASCII 主题自动 RFC2047 编码
        sender = self.user or "my-cron@localhost"
        mime["From"] = formataddr((message.from_name, sender)) if message.from_name else sender
        mime["To"] = ", ".join(message.to)
        if message.cc:
            mime["Cc"] = ", ".join(message.cc)
        return mime

    def send(self, message: MailMessage) -> None:
        """发送邮件;失败自动重试,最终失败抛 RuntimeError。"""
        if not message.to:
            raise ValueError("收件人为空")
        if not message.subject:
            raise ValueError("邮件主题为空")

        mime = self._build_mime(message)
        all_recipients = list(message.to) + list(message.cc)
        last_error = None

        for attempt in range(1, self.retries + 2):  # 首次 + 重试次数
            try:
                self.log(
                    f"第 {attempt} 次尝试:{mask_addr(self.user)} -> {len(all_recipients)} 个收件人"
                    f"({'HTML' if message.html else '纯文本'},正文 {len(message.body)} 字符)"
                )
                with self._connect() as server:
                    server.sendmail(self.user, all_recipients, mime.as_string())
                self.log("发送成功")
                return
            except Exception as error:  # noqa: BLE001 任何发送异常统一重试
                last_error = error
                self.log(f"发送失败:{error.__class__.__name__}: {error}")
                if attempt <= self.retries:
                    time.sleep(self.retry_delay * attempt)

        raise RuntimeError(f"邮件发送失败(已重试 {self.retries} 次):{last_error}") from last_error
