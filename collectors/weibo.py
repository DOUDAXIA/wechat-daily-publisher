"""微博热搜收集器"""

from typing import List

import requests

from .base import clean_topic_title, classify_topic


class WeiboCollector:
    name = "微博"
    url = "https://weibo.com/ajax/side/hotSearch"

    def fetch(self) -> List[dict]:
        """获取微博热搜榜"""
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/120.0.0.0 Safari/537.36",
            "Accept": "application/json, text/plain, */*",
            "Referer": "https://weibo.com/",
        }
        try:
            resp = requests.get(self.url, headers=headers, timeout=15)
            resp.raise_for_status()
            data = resp.json()
        except Exception as e:
            print(f"[微博] 请求失败: {e}")
            return []

        items = []
        raw_list = data.get("data", {}).get("realtime", [])
        for item in raw_list[:25]:
            word = item.get("word", "")
            if not word:
                continue
            title = clean_topic_title(word)
            if not title or len(title) < 2:
                continue

            rank = item.get("rank", 0)
            raw_hot = item.get("raw_hot", 0)
            items.append({
                "title": title,
                "source": "微博",
                "category": classify_topic(title),
                "rank": int(rank) if rank else 0,
                "heat": int(raw_hot) if raw_hot else 0,
                "url": f"https://s.weibo.com/weibo?q={title}",
            })
        print(f"[微博] 获取到 {len(items)} 条热搜")
        return items
