"""
Qwen 3.5 122B A10B 模型调用示例
阿里通义千问的 122B 大语言模型
"""

import os
import httpx
from openai import OpenAI

from src.ssl_config import setup_ssl_certificates
setup_ssl_certificates()


def test_qwen3_5_122b_a10b():
    """测试 Qwen 3.5 122B A10B 模型"""

    api_key = os.getenv("NVIDIA_API_KEY")

    client = OpenAI(
        base_url="https://integrate.api.nvidia.com/v1",
        api_key=api_key,
        http_client=httpx.Client(verify=False, timeout=120)  # 需要 verify=False 因 SSL 问题
    )

    print("🤖 测试 Qwen 3.5 122B A10B")
    print("=" * 50)

    try:
        response = client.chat.completions.create(
            model="qwen/qwen3.5-122b-a10b",
            messages=[
                {"role": "system", "content": "你是一个有用的助手"},
                {"role": "user", "content": "请回复'OK'"}
            ],
            max_tokens=100,
            temperature=0.7
        )

        message = response.choices[0].message
        usage = response.usage

        print(f"✅ 成功!")
        print(f"回复: {message.content}")
        print("-" * 50)
        if usage:
            print(f"Token 使用: prompt={usage.prompt_tokens}, completion={usage.completion_tokens}, total={usage.total_tokens}")

        if hasattr(response, 'nvext') and hasattr(response.nvext, 'timing'):
            print(f"TTFT: {response.nvext.timing.get('ttft_ms', 'N/A')}ms")

        return True

    except Exception as e:
        print(f"❌ 错误: {type(e).__name__}: {e}")
        return False
    finally:
        client.close()


def test_qwen3_5_122b_a10b_stream():
    """流式测试"""

    api_key = os.getenv("NVIDIA_API_KEY")

    client = OpenAI(
        base_url="https://integrate.api.nvidia.com/v1",
        api_key=api_key,
        http_client=httpx.Client(verify=False, timeout=120)
    )

    print("🤖 测试 Qwen 3.5 122B A10B（流式）")
    print("=" * 50)

    try:
        response = client.chat.completions.create(
            model="qwen/qwen3.5-122b-a10b",
            messages=[{"role": "user", "content": "请用一句话解释量子计算"}],
            max_tokens=150,
            temperature=0.7,
            stream=True
        )

        collected = []
        for chunk in response:
            if chunk.choices and chunk.choices[0].delta.content:
                content = chunk.choices[0].delta.content
                print(content, end="", flush=True)
                collected.append(content)

        print(f"\n✅ 流式完成!")
        print(f"最终回复: {''.join(collected)}")

        return True

    except Exception as e:
        print(f"❌ 错误: {type(e).__name__}: {e}")
        return False
    finally:
        client.close()


if __name__ == "__main__":
    import sys

    print("选择测试模式:")
    print("1. 普通模式")
    print("2. 流式模式")

    choice = input("输入选择 (1/2): ").strip()

    if choice == "2":
        test_qwen3_5_122b_a10b_stream()
    else:
        test_qwen3_5_122b_a10b()