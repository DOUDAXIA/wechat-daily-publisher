"""微信公众号每日自动发文系统 - 主入口

每日荐书(一日一书)+毛选附文 → 配图 → 双通道推送
"""

import json
import os
import random
import re
import sys
from datetime import datetime, timezone, timedelta

from writer import DeepSeekWriter
from writer.prompts import (
    MAIN_ARTICLE_SYSTEM,
    MAIN_ARTICLE_USER,
    MAO_ESSAY_SYSTEM,
    MAO_ESSAY_USER,
)
from images import ImageFetcher
from output import Notifier


def load_config() -> dict:
    """加载配置文件"""
    script_dir = os.path.dirname(os.path.abspath(__file__))
    config_path = os.path.join(script_dir, "config.json")
    if not os.path.exists(config_path):
        print("❌ 未找到 config.json，请参考 config.example.json 创建配置文件")
        sys.exit(1)
    with open(config_path, "r", encoding="utf-8") as f:
        return json.load(f)


def check_today_event(data_dir: str, today: datetime) -> dict | None:
    """检查今天是否有特殊节日或事件，支持 MM-DD 和 YYYY-MM-DD 两种格式"""
    path = os.path.join(data_dir, "events_calendar.json")
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)

    today_mmdd = today.strftime("%m-%d")
    today_full = today.strftime("%Y-%m-%d")

    for event in data.get("events", []):
        event_date = event["date"]
        if event_date == today_mmdd or event_date == today_full:
            print(f"[事件] 今天是{event['name']}！主题：{event['theme']}")
            return event
    return None


def pick_category(data_dir: str, event: dict | None = None) -> tuple:
    """选取今日荐书类别。如有特殊事件则联动推荐，返回 (类别, 事件提示)"""
    if event:
        category = event.get("suggest_category", "文学小说")
        hint = event.get("hint", "")
        print(f"[荐书] 联动事件「{event['name']}」-> 类别: {category}")
        return category, hint

    path = os.path.join(data_dir, "book_categories.json")
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)

    categories = data["categories"]
    used = data.get("_used_indices", [])

    available = [i for i in range(len(categories)) if i not in used]
    if not available:
        print("[荐书] 所有类别已轮完一遍，重置")
        data["_used_indices"] = []
        available = list(range(len(categories)))

    idx = random.choice(available)
    data["_used_indices"] = used + [idx]

    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

    category = categories[idx]
    print(f"[荐书] 今日类别: {category}（第{len(data['_used_indices'])}/10轮）")
    return category, ""


def pick_mao_essay(essays_path: str) -> dict:
    """随机选取一篇未用过的毛选篇章"""
    with open(essays_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    essays = data["essays"]
    used_ids = set(data.get("_used_ids", []))
    available = [e for e in essays if e["id"] not in used_ids]

    if not available:
        print("[毛选] 所有篇章已轮完一遍，重置列表")
        data["_used_ids"] = []
        used_ids = set()
        available = essays

    chosen = random.choice(available)
    data["_used_ids"] = list(used_ids) + [chosen["id"]]

    with open(essays_path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

    print(f"[毛选] 选中: {chosen['title']}（第{data['_used_ids'].index(chosen['id']) + 1}/25篇）")
    return chosen


def load_book_history(data_dir: str) -> list:
    """加载已推荐书籍列表"""
    path = os.path.join(data_dir, "book_history.json")
    if not os.path.exists(path):
        return []
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)
    return data.get("books", [])


def save_book_history(data_dir: str, title: str):
    """保存已推荐的书名，保留最近50条"""
    path = os.path.join(data_dir, "book_history.json")
    books = load_book_history(data_dir)
    books.append({"title": title, "date": datetime.now(timezone(timedelta(hours=8))).strftime("%Y-%m-%d")})
    if len(books) > 50:
        books = books[-50:]
    with open(path, "w", encoding="utf-8") as f:
        json.dump({"books": books}, f, ensure_ascii=False, indent=2)


def extract_book_title(content: str) -> str:
    """从文章内容尝试提取书名"""
    # 匹配《书名》格式
    matches = re.findall(r"《(.+?)》", content)
    if matches:
        # 取第一个，优先选择包含「一日一书」标题行中的
        for m in matches:
            if "一日一书" not in m and len(m) > 1:
                return m
        return matches[0]
    return ""


def save_history_file(history_dir: str, filename: str, content: str):
    """保存文章到历史存档目录"""
    os.makedirs(history_dir, exist_ok=True)
    path = os.path.join(history_dir, filename)
    with open(path, "w", encoding="utf-8") as f:
        f.write(content)


def check_already_sent(data_dir: str, today_file: str) -> bool:
    """检查今天是否已发送过（通过GitHub API写入标记文件，持久化到仓库）"""
    sent_flag = os.path.join(data_dir, f"{today_file}_sent.txt")
    return os.path.exists(sent_flag)


def mark_sent(data_dir: str, today_file: str):
    """标记今天已发送（持久化到仓库，下次运行可检测）"""
    sent_flag = os.path.join(data_dir, f"{today_file}_sent.txt")
    with open(sent_flag, "w") as f:
        f.write("done")


def main():
    beijing_tz = timezone(timedelta(hours=8))
    now = datetime.now(beijing_tz)
    today_str = now.strftime("%Y年%m月%d日")
    today_file = now.strftime("%Y%m%d")

    current_hour = now.hour
    current_minute = now.minute

    print(f"\n{'='*50}")
    print(f"  微信公众号每日发文系统 - {today_str}")
    print(f"  北京时间: {current_hour:02d}:{current_minute:02d}")
    print(f"{'='*50}\n")

    config = load_config()
    script_dir = os.path.dirname(os.path.abspath(__file__))
    data_dir = os.path.join(script_dir, "mao_data")
    history_dir = os.path.join(script_dir, "history")

    # 防重复：今天已经发过了就跳过（标记文件在 mao_data/ 目录，会持久化到仓库）
    if check_already_sent(data_dir, today_file):
        print(f"[跳过] 今天({today_str})已经发送过了")
        sys.exit(0)

    # 时间窗口逻辑：
    # - 9:00-9:15：准时发送
    # - 9:15之后且今天未发：迟到补发
    # - 手动触发：不限时间
    event_name = os.environ.get("GITHUB_EVENT_NAME", "")
    is_manual = event_name in ("workflow_dispatch", "repository_dispatch")
    is_ontime = (current_hour == 9 and current_minute <= 15)
    is_late = (current_hour >= 9 and current_minute > 15) or current_hour > 9
    late_notice = ""

    if not is_ontime and not is_late and not is_manual:
        print(f"[跳过] 当前时间 {current_hour:02d}:{current_minute:02d}，未到发送时间")
        sys.exit(0)

    if is_late and not is_manual:
        late_notice = "\n（注：GitHub Actions 调度延迟，今日发送时间推迟，见谅）"
        print(f"[补发] 已过9:15，执行迟到补发")
    writer = DeepSeekWriter(config)

    # ① 检测特殊日期 + 选取荐书类别
    print("【步骤1/4】检测特殊日期并选取荐书类别...")
    event = check_today_event(data_dir, now)
    category, event_hint = pick_category(data_dir, event)

    # 构建推荐历史文本以辅助去重
    recent_books = load_book_history(data_dir)
    history_text = ""
    if recent_books:
        recent_titles = [b["title"] for b in recent_books[-10:]]
        history_text = f"\n⚠️ 以下书籍近期已推荐过，请务必避免重复：{', '.join(recent_titles)}"

    # ② 写主文：每日荐书
    print("【步骤2/4】DeepSeek AI 撰写荐书文章...")
    style = config.get("style", "sharp")  # sharp / warm / concise
    style_map = {
        "sharp": "保持你一贯犀利而不失幽默的评论风格",
        "warm": "今天的语调温和一些，像一个贴心的朋友在聊天，少讽刺多鼓励",
        "concise": "今天简洁一些，控制在800字以内，每段不超过三行",
    }
    style_hint = style_map.get(style, style_map["sharp"])

    if event:
        event_context = f"\n今日是{event['name']}，主题：{event['theme']}。{event_hint}\n请务必让推荐的书与这个节日或事件有一定关联。"
    else:
        event_context = ""

    user_prompt = MAIN_ARTICLE_USER.format(
        category=category,
        event_context=event_context,
        style_hint=style_hint,
        history_text=history_text,
    )

    main_content = writer.chat(
        system_prompt=MAIN_ARTICLE_SYSTEM,
        user_prompt=user_prompt,
        temperature=0.85,
        max_tokens=16384,
    )
    if not main_content:
        print("❌ 主文生成失败")
        sys.exit(1)

    main_title = "一日一书"
    for line in main_content.split("\n"):
        stripped = line.strip()
        if stripped.startswith("# "):
            main_title = stripped[2:].strip()
            break

    print(f"[主文] 标题: {main_title}")
    print(f"[主文] 长度: {len(main_content)} 字")

    # 记录推荐的书名
    book_title = extract_book_title(main_content)
    if book_title:
        save_book_history(data_dir, book_title)
        print(f"[记录] 已记录推荐书籍: 《{book_title}》")

    # ③ 写附文：毛选见解
    print("\n【步骤3/4】撰写毛选附文...")
    essays_path = os.path.join(data_dir, "essays.json")
    mao_essay = pick_mao_essay(essays_path)

    mao_content = writer.chat(
        system_prompt=MAO_ESSAY_SYSTEM,
        user_prompt=MAO_ESSAY_USER.format(
            title=mao_essay["title"],
            volume=mao_essay["volume"],
            theme=mao_essay["theme"],
        ),
        temperature=0.8,
        max_tokens=8192,
    )
    if not mao_content:
        print("❌ 附文生成失败")
        sys.exit(1)

    mao_title = "翻毛选"
    for line in mao_content.split("\n"):
        stripped = line.strip()
        if stripped.startswith("# "):
            mao_title = stripped[2:].strip()
            break

    print(f"[附文] 标题: {mao_title}")
    print(f"[附文] 长度: {len(mao_content)} 字")

    # ④ 配图
    print("\n【步骤4/4】配图并推送...")
    unsplash_key = config.get("unsplash", {}).get("api_key", "")
    pexels_key = config.get("pexels", {}).get("api_key", "")

    main_images = []
    mao_images = []

    if unsplash_key:
        fetcher = ImageFetcher(unsplash_key)
        main_images = fetcher.fetch_for_article(main_content, count=5)
        mao_images = fetcher.fetch_for_article(mao_content, count=3)

    # 备用图源：Unsplash 没拿到图就用 Pexels
    if (not main_images or not mao_images) and pexels_key:
        print("[图片] Unsplash 图片不足，启用 Pexels 备用图源...")
        pexels_images_dir = data_dir  # dummy, we create a new fetcher
        pexels_fetcher = ImageFetcher(pexels_key, source="pexels")
        if not main_images:
            main_images = pexels_fetcher.fetch_for_article(main_content, count=5)
        if not mao_images:
            mao_images = pexels_fetcher.fetch_for_article(mao_content, count=3)

    if not unsplash_key and not pexels_key:
        print("[图片] 未配置任何图源 API Key，跳过配图")

    # ⑤ 推送
    main_article = {
        "title": main_title,
        "content": main_content + late_notice,
        "images": main_images,
        "date": today_str,
    }
    mao_article = {
        "title": mao_title,
        "content": mao_content,
        "images": mao_images,
        "date": today_str,
        "source_essay": mao_essay["title"],
    }

    notifier = Notifier(config)
    notifier.notify(main_article, mao_article)

    # ⑥ 保存历史存档
    full_text = f"# {main_title}\n\n{main_content}\n\n---\n\n# {mao_title}\n\n{mao_content}"
    save_history_file(history_dir, f"{today_file}_主文.md", main_content)
    save_history_file(history_dir, f"{today_file}_附文.md", mao_content)
    save_history_file(history_dir, f"{today_file}_全文.md", full_text)
    print(f"[存档] 已保存至 {history_dir}/")

    mark_sent(data_dir, today_file)

    print(f"\n{'='*50}")
    print(f"  ✅ 任务完成！荐书+附文已推送")
    print(f"  主文：《{main_title}》")
    print(f"  附文：《{mao_title}》")
    print(f"  文风：{style}")
    print(f"{'='*50}\n")


if __name__ == "__main__":
    main()
