"""今日头条热榜收集器"""

from typing import List

import requests

from .base import clean_topic_title, classify_topic


class ToutiaoCollector:
    name = "头条"
    url = "https://www.toutiao.com/hot-event/hot-board/?origin=toutiao_pc"

    def fetch(self) -> List[dict]:
        """获取今日头条热榜"""
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/120.0.0.0 Safari/537.36",
            "Accept": "application/json",
            "Referer": "https://www.toutiao.com/",
        }
        try:
            resp = requests.get(self.url, headers=headers, timeout=15)
            resp.raise_for_status()
            data = resp.json()
        except Exception as e:
            print(f"[头条] 请求失败: {e}")
            return []

        items = []
        raw_list = data.get("data", [])
        for item in raw_list[:25]:
            title = item.get("Title", "")
            if not title:
                continue
            title = clean_topic_title(title)
            if not title or len(title) < 2:
                continue

            items.append({
                "title": title,
                "source": "今日头条",
                "category": classify_topic(title),
                "heat": item.get("HotValue", ""),
                "url": item.get("Url", f"https://www.toutiao.com/trending/{item.get('ClusterId', '')}"),
            })
        print(f"[头条] 获取到 {len(items)} 条热搜")
        return items
