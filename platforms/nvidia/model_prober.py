"""
NVIDIA 模型可用性探测器
用最小 chat 请求验证哪些模型真正有托管端点
"""

import asyncio
import time
from typing import List, Tuple, Optional, Callable


class NvidiaModelProber:
    """快速探测模型是否真正有可用的 chat 端点"""

    def __init__(self, api_key: str, base_url: str = "https://integrate.api.nvidia.com/v1"):
        self.api_key = api_key
        self.base_url = base_url

    async def probe_single(self, model_id: str, timeout: int = 30) -> Tuple[bool, float, str]:
        start = time.time()
        try:
            from openai import AsyncOpenAI
            import httpx
            client = AsyncOpenAI(
                base_url=self.base_url,
                api_key=self.api_key,
                http_client=httpx.AsyncClient(verify=True, timeout=timeout),
            )
            response = await client.chat.completions.create(
                model=model_id,
                messages=[{"role": "user", "content": "hi"}],
                max_tokens=5,
            )
            elapsed = time.time() - start
            await client.close()
            return (True, round(elapsed, 2), "")
        except Exception as e:
            elapsed = time.time() - start
            return (False, round(elapsed, 2), str(e)[:200])

    async def probe_batch(
        self,
        model_ids: List[str],
        concurrency: int = 10,
        timeout: int = 30,
        progress_callback: Optional[Callable] = None,
    ) -> dict:
        semaphore = asyncio.Semaphore(concurrency)
        results = {}

        async def _probe_with_limit(mid, idx):
            async with semaphore:
                result = await self.probe_single(mid, timeout)
                results[mid] = result
                if progress_callback:
                    progress_callback(idx + 1, len(model_ids), mid, result[0])

        tasks = [_probe_with_limit(mid, i) for i, mid in enumerate(model_ids)]
        await asyncio.gather(*tasks, return_exceptions=True)
        return results
