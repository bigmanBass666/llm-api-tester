"""
NVIDIA NIM API 基础调用示例
适用于所有支持 OpenAI 兼容格式的模型
"""

import os
import httpx
from openai import OpenAI

from src.ssl_config import setup_ssl_certificates
setup_ssl_certificates()


def test_model_simple(model_id: str, api_key: str = None):
    """简单测试模型 - 非流式"""
    if api_key is None:
        api_key = os.getenv("NVIDIA_API_KEY")

    client = OpenAI(
        base_url="https://integrate.api.nvidia.com/v1",
        api_key=api_key,
        http_client=httpx.Client(verify=True, timeout=120)
    )

    print(f"测试模型: {model_id}")
    print("-" * 50)

    try:
        response = client.chat.completions.create(
            model=model_id,
            messages=[{"role": "user", "content": "请回复'OK'"}],
            max_tokens=100,
            temperature=0.7
        )

        message = response.choices[0].message

        print(f"✅ 成功!")
        print(f"内容: {message.content}")
        print(f"推理内容: {getattr(message, 'reasoning_content', '无')}")
        print(f"完成原因: {response.choices[0].finish_reason}")

        return True

    except Exception as e:
        print(f"❌ 错误: {type(e).__name__}: {e}")
        return False
    finally:
        client.close()


def test_model_streaming(model_id: str, api_key: str = None, enable_thinking: bool = False):
    """流式测试模型"""
    if api_key is None:
        api_key = os.getenv("NVIDIA_API_KEY")

    client = OpenAI(
        base_url="https://integrate.api.nvidia.com/v1",
        api_key=api_key,
        http_client=httpx.Client(verify=True, timeout=120)
    )

    print(f"测试模型（流式）: {model_id}")
    print(f"启用推理: {enable_thinking}")
    print("-" * 50)

    try:
        extra_body = {"chat_template_kwargs": {"enable_thinking": enable_thinking}} if enable_thinking else None

        response = client.chat.completions.create(
            model=model_id,
            messages=[{"role": "user", "content": "请回复'OK'"}],
            max_tokens=100,
            temperature=0.7,
            stream=True,
            extra_body=extra_body
        )

        collected_content = ""
        collected_reasoning = ""
        chunk_count = 0

        for chunk in response:
            if chunk.choices and chunk.choices[0].delta:
                delta = chunk.choices[0].delta

                if delta.content:
                    collected_content += delta.content
                    print(f"[内容] {delta.content}", end="", flush=True)

                reasoning = getattr(delta, 'reasoning_content', None)
                if reasoning:
                    collected_reasoning += reasoning
                    print(f"[推理] {reasoning}", end="", flush=True)

                chunk_count += 1

        print(f"\n✅ 流式完成!")
        print(f"总chunk数: {chunk_count}")
        print(f"最终内容: {collected_content}")
        if collected_reasoning:
            print(f"推理内容: {collected_reasoning}")

        return True

    except Exception as e:
        print(f"❌ 错误: {type(e).__name__}: {e}")
        return False
    finally:
        client.close()


if __name__ == "__main__":
    # 示例：测试一个普通模型
    test_model_simple("minimaxai/minimax-m2.7")

    # 示例：测试推理模型
    test_model_streaming("google/gemma-4-31b-it", enable_thinking=True)
