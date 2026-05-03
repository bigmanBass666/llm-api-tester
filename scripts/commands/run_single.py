import time
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from src import registry
from src.models import ChatMessage


def get_api_key(platform: str) -> str:
    config = registry.get(platform)
    if config and config.api_key_env:
        key = os.getenv(config.api_key_env)
        if key:
            return key
    raise ValueError(f"未找到 {platform} 的 API Key，请设置环境变量")

def _ensure_platform_registered(platform: str):
    if registry.get(platform) is not None:
        return
    try:
        import importlib
        importlib.import_module(f"platforms.{platform}.client")
    except (ImportError, ModuleNotFoundError):
        pass


def run(model_id: str, platform: str = "nvidia", message: str = "请回复'OK'", verbose: bool = True) -> dict:
    _ensure_platform_registered(platform)
    api_key = get_api_key(platform)
    client = registry.create_client(platform, api_key=api_key)
    config = registry.get(platform)
    display_name = config.display_name if config else platform
    if verbose:
        print(f"\n{'='*60}")
        print(f"单模型测试")
        print(f"{'='*60}")
        print(f"  平台 : {display_name}")
        print(f"  模型 : {model_id}")
        print(f"  消息 : {message[:40]}...")
        print(f"{'-'*60}")
    start_time = time.time()
    try:
        response = client.chat(
            model_id,
            [ChatMessage(role="user", content=message)],
            max_tokens=50,
        )
        elapsed = time.time() - start_time
        if response and response.strip():
            if verbose:
                print(f"  成功 ({elapsed:.2f}s)")
                print(f"  回复: {response[:100]}")
            return {
                "model": model_id,
                "status": "success",
                "time": round(elapsed, 2),
                "response": response[:200],
            }
        else:
            if verbose:
                print(f"  空回复 ({elapsed:.2f}s)")
            return {
                "model": model_id,
                "status": "empty",
                "time": round(elapsed, 2),
            }
    except Exception as e:
        elapsed = time.time() - start_time
        if verbose:
            print(f"  失败 ({elapsed:.2f}s)")
            print(f"  错误: {type(e).__name__}: {str(e)[:100]}")
        return {
            "model": model_id,
            "status": "error",
            "time": round(elapsed, 2),
            "error": f"{type(e).__name__}: {str(e)[:100]}",
        }
    finally:
        client.close()
