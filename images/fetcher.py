"""图片搜索下载 - 支持 Unsplash / Pexels 双图源"""

import os
import re
import hashlib
from typing import List

import requests


class ImageFetcher:
    def __init__(self, api_key: str, source: str = "unsplash"):
        self.api_key = api_key
        self.source = source
        self.cache_dir = os.path.join(
            os.path.dirname(__file__), "..", "output", "img_cache"
        )
        os.makedirs(self.cache_dir, exist_ok=True)

    def extract_keywords(self, text: str, count: int = 6) -> List[str]:
        """从文章中提取搜索关键词"""
        chinese_words = re.findall(r"[一-鿿]{2,4}", text)
        stop_words = {
            "一个", "这个", "可以", "他们", "我们", "自己", "什么", "没有",
            "因为", "所以", "但是", "如果", "虽然", "已经", "还是", "不是",
            "就是", "可能", "应该", "这些", "那些", "一些", "很多", "非常",
            "不过", "而且", "然后", "这样", "那样", "怎么", "这么", "那么",
        }
        word_freq = {}
        for w in chinese_words:
            if w in stop_words:
                continue
            word_freq[w] = word_freq.get(w, 0) + 1

        sorted_words = sorted(word_freq.items(), key=lambda x: x[1], reverse=True)
        keywords = []
        for word, _ in sorted_words:
            if word not in keywords:
                keywords.append(word)
            if len(keywords) >= count:
                break

        visual_keywords = {
            "游戏": "gaming", "运动": "sports", "足球": "football",
            "篮球": "basketball", "娱乐": "entertainment", "电影": "cinema",
            "科技": "technology", "国际": "world", "社会": "city life",
            "经济": "business", "环境": "nature", "城市": "city",
            "航天": "space", "海洋": "ocean", "自然": "nature landscape",
            "手机": "smartphone", "阅读": "reading book",
            "春节": "chinese new year", "节日": "festival celebration",
        }
        for cn, en in visual_keywords.items():
            if cn in text and en not in keywords:
                keywords.append(en)

        return keywords if keywords else ["book", "reading", "knowledge"]

    def _search_unsplash(self, keyword: str, per_page: int = 3) -> List[dict]:
        """Unsplash 搜索"""
        headers = {"Authorization": f"Client-ID {self.api_key}"}
        params = {
            "query": keyword, "per_page": per_page,
            "orientation": "landscape", "order_by": "relevant",
        }
        try:
            resp = requests.get(
                "https://api.unsplash.com/search/photos",
                headers=headers, params=params, timeout=15,
            )
            resp.raise_for_status()
            data = resp.json()
        except Exception as e:
            print(f"[Unsplash] 搜索失败: {e}")
            return []

        results = []
        for photo in data.get("results", []):
            urls = photo.get("urls", {})
            user = photo.get("user", {})
            results.append({
                "url": urls.get("regular", ""),
                "small_url": urls.get("small", ""),
                "photographer": user.get("name", ""),
                "photographer_url": f"https://unsplash.com/@{user.get('username', '')}",
                "alt": photo.get("alt_description", keyword),
                "color": photo.get("color", "#333"),
            })
        return results

    def _search_pexels(self, keyword: str, per_page: int = 3) -> List[dict]:
        """Pexels 搜索（备用图源）"""
        headers = {"Authorization": self.api_key}
        params = {
            "query": keyword, "per_page": per_page,
            "orientation": "landscape", "locale": "zh-CN",
        }
        try:
            resp = requests.get(
                "https://api.pexels.com/v1/search",
                headers=headers, params=params, timeout=15,
            )
            resp.raise_for_status()
            data = resp.json()
        except Exception as e:
            print(f"[Pexels] 搜索失败: {e}")
            return []

        results = []
        for photo in data.get("photos", []):
            results.append({
                "url": photo["src"]["large"],
                "small_url": photo["src"]["medium"],
                "photographer": photo["photographer"],
                "photographer_url": photo["photographer_url"],
                "alt": photo.get("alt", keyword),
                "color": photo.get("avg_color", "#333"),
            })
        return results

    def download(self, url: str, filename: str) -> str:
        """下载图片到本地缓存"""
        filepath = os.path.join(self.cache_dir, filename)
        if os.path.exists(filepath):
            return filepath
        try:
            resp = requests.get(url, timeout=30)
            resp.raise_for_status()
            with open(filepath, "wb") as f:
                f.write(resp.content)
            return filepath
        except Exception as e:
            print(f"[图片] 下载失败: {e}")
            return ""

    def fetch_for_article(self, text: str, count: int = 5) -> List[dict]:
        """为文章匹配图片"""
        keywords = self.extract_keywords(text, count=8)
        all_images = []
        seen_urls = set()

        search_fn = self._search_unsplash if self.source == "unsplash" else self._search_pexels

        for kw in keywords[:6]:
            photos = search_fn(kw, per_page=2)
            for photo in photos:
                url = photo["url"]
                if url in seen_urls:
                    continue
                seen_urls.add(url)

                url_hash = hashlib.md5(url.encode()).hexdigest()[:12]
                filename = f"{url_hash}.jpg"
                local_path = self.download(url, filename)

                all_images.append({
                    "keyword": kw,
                    "url": url,
                    "small_url": photo.get("small_url", url),
                    "local_path": local_path,
                    "photographer": photo["photographer"],
                    "photographer_url": photo.get("photographer_url", ""),
                    "alt": photo["alt"],
                    "color": photo.get("color", "#333"),
                })
                if len(all_images) >= count:
                    break
            if len(all_images) >= count:
                break

        tag = "[Unsplash]" if self.source == "unsplash" else "[Pexels]"
        print(f"{tag} 为文章匹配了 {len(all_images)} 张图片")
        return all_images
