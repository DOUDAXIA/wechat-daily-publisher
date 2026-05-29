"""微信公众号每日自动发文系统 - 主入口

每日荐书(一日一书)+毛选附文 → 配图 → 推送
"""

import json
import os
import random
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


def pick_category(data_dir: str) -> str:
    """轮替选取今日荐书类别"""
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
    return category


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
    today = datetime.now(beijing_tz).strftime("%Y年%m月%d日")

    print(f"\n{'='*50}")
    print(f"  微信公众号每日发文系统 - {today}")
    print(f"{'='*50}\n")

    config = load_config()
    script_dir = os.path.dirname(os.path.abspath(__file__))
    data_dir = os.path.join(script_dir, "mao_data")
    writer = DeepSeekWriter(config)

    # ① 选取荐书类别
    print("【步骤1/4】选取今日荐书类别...")
    category = pick_category(data_dir)

    # ② 写主文：每日荐书
    print("【步骤2/4】DeepSeek AI 撰写荐书文章...")
    main_content = writer.chat(
        system_prompt=MAIN_ARTICLE_SYSTEM,
        user_prompt=MAIN_ARTICLE_USER.format(category=category),
        temperature=0.85,
        max_tokens=4096,
    )
    if not main_content:
        print("❌ 主文生成失败")
        sys.exit(1)

    main_title = f"一日一书"
    for line in main_content.split("\n"):
        stripped = line.strip()
        if stripped.startswith("# "):
            main_title = stripped[2:].strip()
            break

    print(f"[主文] 标题: {main_title}")
    print(f"[主文] 长度: {len(main_content)} 字")

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

    # ④ 配图 + 推送
    print("\n【步骤4/4】配图并推送...")
    unsplash_key = config.get("unsplash", {}).get("api_key", "")
    if unsplash_key:
        fetcher = ImageFetcher(unsplash_key)
        main_images = fetcher.fetch_for_article(main_content, count=5)
        mao_images = fetcher.fetch_for_article(mao_content, count=3)
    else:
        print("[图片] 未配置 Unsplash API Key，跳过配图")
        main_images = []
        mao_images = []

    main_article = {
        "title": main_title,
        "content": main_content,
        "images": main_images,
        "date": today,
    }
    mao_article = {
        "title": mao_title,
        "content": mao_content,
        "images": mao_images,
        "date": today,
        "source_essay": mao_essay["title"],
    }

    notifier = Notifier(config)
    notifier.notify(main_article, mao_article)

    print(f"\n{'='*50}")
    print(f"  ✅ 任务完成！荐书+附文已推送")
    print(f"  主文：《{main_title}》")
    print(f"  附文：《{mao_title}》")
    print(f"{'='*50}\n")


if __name__ == "__main__":
    main()
