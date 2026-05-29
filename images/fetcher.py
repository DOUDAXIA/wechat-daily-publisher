"""Pexels 图库搜图下载"""

import os
import re
import hashlib
from typing import List

import requests


class ImageFetcher:
    base_url = "https://api.pexels.com/v1/search"

    def __init__(self, api_key: str):
        self.api_key = api_key
        self.cache_dir = os.path.join(os.path.dirname(__file__), "..", "output", "img_cache")
        os.makedirs(self.cache_dir, exist_ok=True)

    def extract_keywords(self, text: str, count: int = 5) -> List[str]:
        """从文章中提取搜索关键词"""
        # 提取中文词汇（2-4字词语）
        chinese_words = re.findall(r"[一-鿿]{2,4}", text)
        # 按频率排序，去停用词
        stop_words = {
            "一个", "这个", "可以", "他们", "我们", "自己", "什么", "没有",
            "因为", "所以", "但是", "如果", "虽然", "已经", "还是", "不是",
            "就是", "可能", "应该", "这些", "那些", "一些", "很多", "非常",
        }
        word_freq = {}
        for w in chinese_words:
            if w in stop_words:
                continue
            word_freq[w] = word_freq.get(w, 0) + 1

        sorted_words = sorted(word_freq.items(), key=lambda x: x[1], reverse=True)
        # 取排名靠前的不同词汇
        keywords = []
        for word, _ in sorted_words:
            if word not in keywords:
                keywords.append(word)
            if len(keywords) >= count:
                break
        return keywords if keywords else ["新闻", "社会", "生活"]

    def search(self, keyword: str, per_page: int = 3) -> List[dict]:
        """搜索图片"""
        headers = {"Authorization": self.api_key}
        params = {
            "query": keyword,
            "per_page": per_page,
            "locale": "zh-CN",
            "orientation": "landscape",
        }
        try:
            resp = requests.get(self.base_url, headers=headers, params=params, timeout=15)
            resp.raise_for_status()
            data = resp.json()
        except Exception as e:
            print(f"[Pexels] 搜索 '{keyword}' 失败: {e}")
            return []

        results = []
        for photo in data.get("photos", []):
            results.append({
                "url": photo["src"]["large"],
                "medium_url": photo["src"]["medium"],
                "photographer": photo["photographer"],
                "photographer_url": photo["photographer_url"],
                "alt": photo.get("alt", keyword),
            })
        return results

    def download(self, url: str, filename: str) -> str:
        """下载图片到本地缓存并返回路径"""
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
            print(f"[图片] 下载失败 {url}: {e}")
            return ""

    def fetch_for_article(self, text: str, count: int = 5) -> List[dict]:
        """为文章匹配图片，返回图片信息列表"""
        keywords = self.extract_keywords(text, count=8)
        all_images = []
        seen_urls = set()

        for kw in keywords[:5]:
            photos = self.search(kw, per_page=2)
            for photo in photos:
                url = photo["url"]
                if url in seen_urls:
                    continue
                seen_urls.add(url)

                url_hash = hashlib.md5(url.encode()).hexdigest()[:12]
                ext = ".jpg"
                filename = f"{url_hash}{ext}"
                local_path = self.download(url, filename)

                all_images.append({
                    "keyword": kw,
                    "url": url,
                    "medium_url": photo["medium_url"],
                    "local_path": local_path,
                    "photographer": photo["photographer"],
                    "alt": photo["alt"],
                })
                if len(all_images) >= count:
                    break
            if len(all_images) >= count:
                break

        print(f"[图片] 为文章匹配了 {len(all_images)} 张图片")
        return all_images
