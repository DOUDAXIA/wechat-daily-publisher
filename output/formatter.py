"""文章格式化——将Markdown文章转为邮件HTML和微信推送文本"""

from typing import List

import markdown


class OutputFormatter:
    @staticmethod
    def _img_tag(img_info: dict, width: int = 600) -> str:
        url = img_info.get("medium_url") or img_info.get("url", "")
        alt = img_info.get("alt", "配图")
        credit = img_info.get("photographer", "")
        if url:
            credit_line = f"<p style='color:#999;font-size:12px;margin:2px 0 10px 0'>📷 Photo by {credit}</p>" if credit else ""
            return (
                f"<img src='{url}' alt='{alt}' "
                f"style='max-width:{width}px;width:100%;border-radius:8px;margin:10px 0' />"
                f"{credit_line}"
            )
        return f"<p>[图片：{alt}]</p>"

    @classmethod
    def to_html_email(cls, main_article: dict, mao_article: dict) -> str:
        """生成邮件HTML，包含主文和附文"""
        md = markdown.Markdown(extensions=["extra", "nl2br"])

        date_str = main_article.get("date", "")
        main_html = md.convert(main_article["content"])
        mao_html = md.convert(mao_article["content"])
        md.reset()
        md.reset()

        main_imgs = ""
        for img in main_article.get("images", [])[:5]:
            main_imgs += cls._img_tag(img)

        mao_imgs = ""
        for img in mao_article.get("images", [])[:3]:
            mao_imgs += cls._img_tag(img)

        return f"""<!DOCTYPE html>
<html lang="zh-CN">
<head><meta charset="utf-8"></head>
<body style="font-family:'Microsoft YaHei','PingFang SC',sans-serif;max-width:680px;margin:0 auto;padding:20px;background:#f5f5f5">
<div style="background:#fff;padding:30px;border-radius:12px;margin-bottom:20px">
  <div style="text-align:center;padding:20px 0;border-bottom:2px solid #e8e8e8;margin-bottom:20px">
    <h1 style="color:#c00;margin:0">📰 今日杂谈 · 每日热点</h1>
    <p style="color:#999;margin:5px 0 0 0">{date_str}</p>
  </div>
  {main_imgs}
  <div style="line-height:1.8;color:#333;font-size:15px">{main_html}</div>
</div>

<div style="background:#fff;padding:30px;border-radius:12px">
  <div style="text-align:center;padding:20px 0;border-bottom:2px solid #e8e8e8;margin-bottom:20px">
    <h2 style="color:#b8860b;margin:0">📖 翻毛选 · 附文</h2>
  </div>
  {mao_imgs}
  <div style="line-height:1.8;color:#333;font-size:15px">{mao_html}</div>
</div>

<div style="text-align:center;color:#999;font-size:12px;margin-top:20px">
  <p>本邮件由AI自动生成 · 每日推送 · 请手动发布至公众号</p>
</div>
</body></html>"""

    @classmethod
    def to_pushplus_text(cls, main_article: dict, mao_article: dict) -> str:
        """生成PushPlus推送的Markdown文本（PushPlus支持Markdown）"""
        date = main_article.get("date", "")
        main_title = main_article.get("title", "今日热点")
        mao_title = mao_article.get("title", "翻毛选")

        text = f"# 📰 {main_title}\n\n"
        text += f"> {date} · 自动生成\n\n"
        text += main_article["content"]
        text += "\n\n---\n\n"
        text += f"# 📖 {mao_title}\n\n"
        text += mao_article["content"]
        text += "\n\n---\n\n"
        text += "> ⚠️ 本文由AI自动生成，仅供参考。请手动复制到公众号后台发布。"
        return text

    @classmethod
    def format_for_wechat(cls, main_article: dict, mao_article: dict) -> str:
        """生成适合直接粘贴到微信公众号编辑器的纯文本格式"""
        main_imgs_note = ""
        if main_article.get("images"):
            main_imgs_note = "\n\n【配图建议】\n"
            for i, img in enumerate(main_article["images"][:5], 1):
                main_imgs_note += f"  图{i}：{img.get('medium_url', img.get('url', ''))}\n"

        mao_imgs_note = ""
        if mao_article.get("images"):
            mao_imgs_note = "\n\n【配图建议】\n"
            for i, img in enumerate(mao_article["images"][:3], 1):
                mao_imgs_note += f"  图{i}：{img.get('medium_url', img.get('url', ''))}\n"

        return f"""==================== 主文 ====================

{main_article['content']}
{main_imgs_note}

==================== 附文 ====================

{mao_article['content']}
{mao_imgs_note}
"""
