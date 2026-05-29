"""文章格式化 - 现代简洁排版"""

import markdown


class OutputFormatter:
    @staticmethod
    def _img_tag(img_info: dict) -> str:
        url = img_info.get("small_url") or img_info.get("url", "")
        alt = img_info.get("alt", "配图")
        credit = img_info.get("photographer", "")
        color = img_info.get("color", "#f0f0f0")
        if url:
            credit_line = (
                f"<span style='color:#bbb;font-size:11px'>Photo by {credit}</span>"
                if credit else ""
            )
            return f"""
            <div style="margin:24px 0;border-radius:10px;overflow:hidden;background:{color}">
              <img src="{url}" alt="{alt}" style="width:100%;display:block" />
            </div>
            {credit_line}
            """
        return f"<p style='color:#999;font-style:italic'>[图片：{alt}]</p>"

    @classmethod
    def to_html_email(cls, main_article: dict, mao_article: dict) -> str:
        """现代简洁风邮件 HTML"""
        date_str = main_article.get("date", "")
        main_title = main_article.get("title", "今日热点")

        md = markdown.Markdown(extensions=["extra", "nl2br"])
        main_html = md.convert(main_article["content"])
        mao_html = md.convert(mao_article["content"])

        main_imgs_html = ""
        for img in main_article.get("images", [])[:5]:
            main_imgs_html += cls._img_tag(img)

        mao_imgs_html = ""
        for img in mao_article.get("images", [])[:3]:
            mao_imgs_html += cls._img_tag(img)

        return f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
</head>
<body style="margin:0;padding:0;background:#f7f6f4;font-family:-apple-system,BlinkMacSystemFont,'Segoe UI','PingFang SC','Microsoft YaHei',sans-serif">

<div style="max-width:640px;margin:0 auto;padding:24px 16px">

  <!-- 顶部 -->
  <div style="text-align:center;padding:32px 0 20px 0">
    <div style="font-size:13px;color:#b0a89c;letter-spacing:2px;margin-bottom:8px">DAILY BOOK</div>
    <h1 style="margin:0;font-size:24px;font-weight:700;color:#1a1a1a;line-height:1.4">{main_title}</h1>
    <div style="margin-top:10px;font-size:13px;color:#999">{date_str}</div>
  </div>

  <!-- 主文卡片 -->
  <div style="background:#fff;border-radius:14px;padding:32px 28px;box-shadow:0 1px 3px rgba(0,0,0,0.04)">
    {main_imgs_html}
    <div style="font-size:15px;line-height:1.9;color:#2c2c2c">
      {main_html}
    </div>
  </div>

  <!-- 分隔 -->
  <div style="text-align:center;padding:28px 0;color:#ccc;font-size:20px;letter-spacing:8px">&middot; &middot; &middot;</div>

  <!-- 附文卡片 -->
  <div style="background:#fff;border-radius:14px;padding:32px 28px;box-shadow:0 1px 3px rgba(0,0,0,0.04)">
    <div style="border-left:3px solid #b8860b;padding-left:14px;margin-bottom:20px">
      <div style="font-size:12px;color:#b8860b;letter-spacing:2px">FROM MAO'S WORKS</div>
      <h2 style="margin:6px 0 0 0;font-size:18px;font-weight:700;color:#333">翻毛选</h2>
    </div>
    {mao_imgs_html}
    <div style="font-size:15px;line-height:1.9;color:#2c2c2c">
      {mao_html}
    </div>
  </div>

  <!-- 页脚 -->
  <div style="text-align:center;padding:24px 0;font-size:12px;color:#bbb">
    <p>由 DeepSeek AI 自动生成 &middot; 每日推送 &middot; 请手动发布至公众号</p>
  </div>

</div>
</body>
</html>"""

    @classmethod
    def to_pushplus_text(cls, main_article: dict, mao_article: dict) -> str:
        """PushPlus 推送文本（Markdown）"""
        date = main_article.get("date", "")
        main_title = main_article.get("title", "今日热点")
        mao_title = mao_article.get("title", "翻毛选")

        text = f"# {main_title}\n\n"
        text += f"> {date} · 自动生成\n\n"
        text += main_article["content"]
        text += "\n\n---\n\n"
        text += f"# {mao_title}\n\n"
        text += mao_article["content"]
        text += "\n\n---\n\n"
        text += "> 本文由AI自动生成，请手动复制到公众号后台发布。"
        return text

    @classmethod
    def format_for_wechat(cls, main_article: dict, mao_article: dict) -> str:
        """公众号编辑器纯文本格式"""
        main_imgs_note = ""
        if main_article.get("images"):
            main_imgs_note = "\n\n【配图建议】\n"
            for i, img in enumerate(main_article["images"][:5], 1):
                url = img.get("small_url") or img.get("url", "")
                main_imgs_note += f"  图{i}：{url}\n"

        mao_imgs_note = ""
        if mao_article.get("images"):
            mao_imgs_note = "\n\n【配图建议】\n"
            for i, img in enumerate(mao_article["images"][:3], 1):
                url = img.get("small_url") or img.get("url", "")
                mao_imgs_note += f"  图{i}：{url}\n"

        sep = "=" * 20
        return f"""{sep} 主文 {sep}

{main_article['content']}
{main_imgs_note}

{sep} 附文 {sep}

{mao_article['content']}
{mao_imgs_note}
"""
