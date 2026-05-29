"""百度热搜收集器"""

from typing import List

import requests

from .base import clean_topic_title, classify_topic


class BaiduCollector:
    name = "百度"
    url = "https://top.baidu.com/board?tab=realtime"

    def fetch(self) -> List[dict]:
        """获取百度热搜榜（通过API接口）"""
        api_url = "https://top.baidu.com/api/board?tab=realtime"
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/120.0.0.0 Safari/537.36",
            "Accept": "application/json",
            "Referer": "https://top.baidu.com/",
        }
        try:
            resp = requests.get(api_url, headers=headers, timeout=15)
            resp.raise_for_status()
            data = resp.json()
        except Exception as e:
            print(f"[百度] 请求失败: {e}")
            return []

        items = []
        cards = data.get("data", {}).get("cards", [])
        for card in cards:
            content_list = card.get("content", [])
            for item in content_list:
                word = item.get("word", "")
                if not word:
                    continue
                title = clean_topic_title(word)
                if not title or len(title) < 2:
                    continue

                items.append({
                    "title": title,
                    "source": "百度",
                    "category": classify_topic(title),
                    "heat": item.get("hotScore", ""),
                    "url": item.get("url", ""),
                    "desc": item.get("desc", ""),
                })

        print(f"[百度] 获取到 {len(items)} 条热搜")
        return items
