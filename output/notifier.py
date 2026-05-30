"""双通道通知：邮件 + PushPlus微信推送"""

import json
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from typing import Dict

import requests

from .formatter import OutputFormatter


class Notifier:
    def __init__(self, config: dict):
        self.email_cfg = config.get("email", {})
        self.wechat_cfg = config.get("wechat_notify", {})
        self.formatter = OutputFormatter()

    def send_email(self, main_article: dict, mao_article: dict) -> bool:
        """发送邮件"""
        if not self.email_cfg:
            print("[邮件] 未配置邮箱，跳过")
            return False

        html = self.formatter.to_html_email(main_article, mao_article)

        msg = MIMEMultipart("alternative")
        msg["Subject"] = f"📰 {main_article.get('title', '今日热点')} | 每日公众号文章"
        msg["From"] = self.email_cfg["sender"]
        msg["To"] = self.email_cfg["receiver"]
        msg.attach(MIMEText(html, "html", "utf-8"))

        try:
            with smtplib.SMTP(self.email_cfg["smtp_host"],
                              self.email_cfg["smtp_port"], timeout=15) as server:
                server.starttls()
                server.login(self.email_cfg["sender"], self.email_cfg["password"])
                server.sendmail(self.email_cfg["sender"],
                              self.email_cfg["receiver"], msg.as_string())
            print(f"[邮件] 已发送到 {self.email_cfg['receiver']}")
            return True
        except Exception as e:
            print(f"[邮件] 发送失败: {e}")
            return False

    def send_wechat(self, main_article: dict, mao_article: dict) -> bool:
        """通过PushPlus推送到微信"""
        if not self.wechat_cfg.get("enabled"):
            print("[微信] 未启用微信通知，跳过")
            return False

        wtype = self.wechat_cfg.get("type", "pushplus")
        token = self.wechat_cfg.get("token", "")

        if wtype == "pushplus":
            return self._send_pushplus(main_article, mao_article, token)
        else:
            print(f"[微信] 未知通知类型: {wtype}")
            return False

    def _send_pushplus(self, main_article: dict, mao_article: dict,
                       token: str) -> bool:
        """PushPlus 推送"""
        if not token:
            print("[PushPlus] Token 未配置，跳过")
            return False

        title = f"📰 {main_article.get('title', '今日热点')}"
        content = self.formatter.to_pushplus_text(main_article, mao_article)

        try:
            resp = requests.post(
                "https://www.pushplus.plus/send",
                json={
                    "token": token,
                    "title": title,
                    "content": content,
                    "template": "markdown",
                },
                timeout=15,
            )
            result = resp.json()
            if result.get("code") == 200:
                print("[PushPlus] 微信推送成功")
                return True
            else:
                print(f"[PushPlus] 推送失败: {result}")
                return False
        except Exception as e:
            print(f"[PushPlus] 推送异常: {e}")
            return False

    def notify(self, main_article: dict, mao_article: dict):
        """双通道通知"""
        print("\n========== 开始推送 ==========")
        email_ok = self.send_email(main_article, mao_article)
        wechat_ok = self.send_wechat(main_article, mao_article)
        if email_ok or wechat_ok:
            print("========== 推送完成 ==========\n")
        else:
            print("========== 推送失败！请检查配置 ==========\n")
