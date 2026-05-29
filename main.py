"""微信公众号每日自动发文系统 - 主入口

每天早上收集昨日全网热点 → AI写主文(回顾+前瞻)+毛选附文 → 配图 → 推送
"""

import json
import os
import random
import sys
from datetime import datetime, timezone, timedelta

from collectors import WeiboCollector, ZhihuCollector, BaiduCollector, ToutiaoCollector
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


def collect_hotspots() -> list:
    """并行抓取四个平台热搜，合并去重，按分类均衡筛选"""
    collectors = [
        WeiboCollector(),
        ZhihuCollector(),
        BaiduCollector(),
        ToutiaoCollector(),
    ]

    all_items = []
    for collector in collectors:
        print(f"[收集] 正在抓取 {collector.name}...")
        items = collector.fetch()
        all_items.extend(items)

    seen_titles = set()
    deduped = []
    for item in all_items:
        key = item["title"][:10]
        if key not in seen_titles:
            seen_titles.add(key)
            deduped.append(item)

    categories = {}
    for item in deduped:
        cat = item.get("category", "其他")
        if cat not in categories:
            categories[cat] = []
        categories[cat].append(item)

    target_categories = ["娱乐", "国际", "游戏", "运动", "科技", "社会", "财经"]
    selected = []
    for cat in target_categories:
        if cat in categories:
            items = sorted(
                categories[cat],
                key=lambda x: x.get("rank", 999) if isinstance(x.get("rank"), (int, float)) else 999,
            )[:3]
            selected.extend(items)

    for cat, items in categories.items():
        if cat not in target_categories and len(selected) < 20:
            selected.extend(items[:2])

    print(f"[收集] 共获取 {len(deduped)} 条，筛选后 {len(selected)} 条")
    print(f"[收集] 覆盖类别: {set(i.get('category') for i in selected)}")
    return selected


def format_hotspots_text(hotspots: list) -> str:
    """将热点列表格式化为Prompt用的文本"""
    lines = []
    for item in hotspots:
        cat = item.get("category", "其他")
        title = item["title"]
        source = item["source"]
        heat = item.get("heat", "")
        heat_str = f" | 热度:{heat}" if heat else ""
        lines.append(f"- [{cat}] {title}（来源：{source}{heat_str}）")
    return "\n".join(lines)


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


def main():
    beijing_tz = timezone(timedelta(hours=8))
    now = datetime.now(beijing_tz)
    yesterday = now - timedelta(days=1)
    date_display = yesterday.strftime("%Y年%m月%d日")

    print(f"\n{'='*50}")
    print(f"  微信公众号每日发文系统 - 回顾{date_display}")
    print(f"{'='*50}\n")

    config = load_config()

    # ① 收集热点
    print("【步骤1/5】收集全网热点...")
    hotspots = collect_hotspots()
    if not hotspots:
        print("❌ 未获取到任何热点，程序终止")
        sys.exit(1)

    hotspots_text = format_hotspots_text(hotspots)
    print(f"\n--- 热点预览 ---\n{hotspots_text[:500]}...\n")

    # ② AI写作
    print("【步骤2/5】DeepSeek AI 撰写主文...")
    writer = DeepSeekWriter(config)

    main_content = writer.chat(
        system_prompt=MAIN_ARTICLE_SYSTEM,
        user_prompt=MAIN_ARTICLE_USER.format(hotspots_text=hotspots_text),
        temperature=0.85,
        max_tokens=4096,
    )
    if not main_content:
        print("❌ 主文生成失败")
        sys.exit(1)

    main_title = f"{date_display} 热点杂谈"
    for line in main_content.split("\n"):
        stripped = line.strip()
        if stripped.startswith("# "):
            main_title = stripped[2:].strip()
            break

    print(f"[主文] 标题: {main_title}")
    print(f"[主文] 长度: {len(main_content)} 字")

    # ③ 毛选附文
    print("\n【步骤3/5】撰写毛选附文...")
    script_dir = os.path.dirname(os.path.abspath(__file__))
    essays_path = os.path.join(script_dir, "mao_data", "essays.json")
    mao_essay = pick_mao_essay(essays_path)

    mao_content = writer.chat(
        system_prompt=MAO_ESSAY_SYSTEM,
        user_prompt=MAO_ESSAY_USER.format(
            title=mao_essay["title"],
            volume=mao_essay["volume"],
            theme=mao_essay["theme"],
        ),
        temperature=0.8,
        max_tokens=3072,
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

    # ④ 配图 (Unsplash)
    print("\n【步骤4/5】匹配插图...")
    unsplash_key = config.get("unsplash", {}).get("api_key", "")
    if unsplash_key:
        fetcher = ImageFetcher(unsplash_key)
        main_images = fetcher.fetch_for_article(main_content, count=5)
        mao_images = fetcher.fetch_for_article(mao_content, count=3)
    else:
        print("[图片] 未配置 Unsplash API Key，跳过配图")
        main_images = []
        mao_images = []

    # ⑤ 推送
    print("\n【步骤5/5】推送文章...")
    main_article = {
        "title": main_title,
        "content": main_content,
        "images": main_images,
        "date": date_display,
    }
    mao_article = {
        "title": mao_title,
        "content": mao_content,
        "images": mao_images,
        "date": date_display,
        "source_essay": mao_essay["title"],
    }

    notifier = Notifier(config)
    notifier.notify(main_article, mao_article)

    print(f"\n{'='*50}")
    print(f"  ✅ 任务完成！主文+附文已推送")
    print(f"  主文：《{main_title}》")
    print(f"  附文：《{mao_title}》")
    print(f"{'='*50}\n")


if __name__ == "__main__":
    main()
