"""
Z.ai GLM 4.7 模型调用示例
推理模型，需要启用 thinking 模式
输出主要在 reasoning_content 中
"""

import os
import httpx
from openai import OpenAI

from src.ssl_config import setup_ssl_certificates
setup_ssl_certificates()


def test_glm4_7(enable_thinking: bool = True):
    """测试 GLM 4.7 模型"""

    api_key = os.getenv("NVIDIA_API_KEY")

    client = OpenAI(
        base_url="https://integrate.api.nvidia.com/v1",
        api_key=api_key,
        http_client=httpx.Client(verify=True, timeout=120)
    )

    print("🧠 测试 Z.ai GLM 4.7")
    print("=" * 50)
    print(f"推理模式: {enable_thinking}")
    print("-" * 50)

    try:
        extra_body = None
        if enable_thinking:
            extra_body = {"chat_template_kwargs": {"enable_thinking": True}}

        response = client.chat.completions.create(
            model="z-ai/glm4.7",
            messages=[{"role": "user", "content": "请回复'OK'"}],
            max_tokens=100,
            temperature=0.7,
            stream=False,
            extra_body=extra_body
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


def test_glm4_7_stream(enable_thinking: bool = True):
    """流式测试 GLM 4.7"""

    api_key = os.getenv("NVIDIA_API_KEY")

    client = OpenAI(
        base_url="https://integrate.api.nvidia.com/v1",
        api_key=api_key,
        http_client=httpx.Client(verify=True, timeout=120)
    )

    print("🧠 测试 Z.ai GLM 4.7（流式）")
    print("=" * 50)

    try:
        extra_body = None
        if enable_thinking:
            extra_body = {"chat_template_kwargs": {"enable_thinking": True}}

        response = client.chat.completions.create(
            model="z-ai/glm4.7",
            messages=[{"role": "user", "content": "请回复'OK'"}],
            max_tokens=100,
            temperature=0.7,
            stream=True,
            extra_body=extra_body
        )

        collected = []
        for chunk in response:
            if chunk.choices and chunk.choices[0].delta:
                delta = chunk.choices[0].delta

                # GLM 4.7 的推理内容在 reasoning_content 中
                content = delta.content
                reasoning = getattr(delta, 'reasoning_content', None)

                if content:
                    print(f"[内容] {content}", end="", flush=True)
                    collected.append(content)

                if reasoning:
                    print(f"[推理] {reasoning}", end="", flush=True)
        print("\n✅ 流式完成!")
        print(f"最终内容: {''.join(collected)}")

        return True

    except Exception as e:
        print(f"❌ 错误: {type(e).__name__}: {e}")
        return False
    finally:
        client.close()


if __name__ == "__main__":
    import sys

    if len(sys.argv) > 1 and sys.argv[1] == "--stream":
        test_glm4_7_stream()
    else:
        test_glm4_7()
