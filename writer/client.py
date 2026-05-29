"""DeepSeek API 客户端"""

import json
from typing import Optional

from openai import OpenAI


class DeepSeekWriter:
    def __init__(self, config: dict):
        self.client = OpenAI(
            api_key=config["deepseek"]["api_key"],
            base_url=config["deepseek"].get("base_url", "https://api.deepseek.com"),
        )
        self.model = config["deepseek"].get("model", "deepseek-chat")

    def chat(self, system_prompt: str, user_prompt: str,
             temperature: float = 0.85, max_tokens: int = 4096) -> str:
        """发送对话请求，返回文本回复"""
        try:
            resp = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt},
                ],
                temperature=temperature,
                max_tokens=max_tokens,
            )
            return resp.choices[0].message.content or ""
        except Exception as e:
            print(f"[DeepSeek] API调用失败: {e}")
            return ""
