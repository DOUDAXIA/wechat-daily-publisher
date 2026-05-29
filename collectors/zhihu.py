"""知乎热榜收集器"""

from typing import List

import requests

from .base import clean_topic_title, classify_topic


class ZhihuCollector:
    name = "知乎"
    url = "https://www.zhihu.com/api/v3/feed/topstory/hot-lists/total"

    def fetch(self) -> List[dict]:
        """获取知乎热榜"""
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/120.0.0.0 Safari/537.36",
            "Accept": "application/json",
        }
        try:
            resp = requests.get(self.url, headers=headers, timeout=15)
            resp.raise_for_status()
            data = resp.json()
        except Exception as e:
            print(f"[知乎] 请求失败: {e}")
            return []

        items = []
        raw_list = data.get("data", [])
        for item in raw_list[:25]:
            target = item.get("target", {})
            title = target.get("title", "")
            if not title:
                continue
            title = clean_topic_title(title)
            if not title or len(title) < 2:
                continue

            detail = target.get("excerpt", "")
            items.append({
                "title": title,
                "source": "知乎",
                "category": classify_topic(title),
                "heat": item.get("detail_text", ""),
                "url": target.get("url", ""),
                "detail": detail,
            })
        print(f"[知乎] 获取到 {len(items)} 条热榜")
        return items
