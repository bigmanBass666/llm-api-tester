"""
MiniMax M2.7 模型调用示例
普通聊天模型，输出在 content 字段
"""

import os
import httpx
from openai import OpenAI

# 设置 SSL 证书（Windows 需要）
os.environ.setdefault('SSL_CERT_FILE', r'D:\apps\python312\Lib\site-packages\certifi\cacert.pem')
os.environ.setdefault('REQUESTS_CA_BUNDLE', r'D:\apps\python312\Lib\site-packages\certifi\cacert.pem')


def test_minimax_m2_7():
    """测试 MiniMax M2.7 模型"""

    api_key = os.getenv("NVIDIA_API_KEY")

    client = OpenAI(
        base_url="https://integrate.api.nvidia.com/v1",
        api_key=api_key,
        http_client=httpx.Client(verify=True, timeout=120)
    )

    print("🤖 测试 MiniMax M2.7")
    print("=" * 50)

    try:
        response = client.chat.completions.create(
            model="minimaxai/minimax-m2.7",
            messages=[
                {"role": "system", "content": "你是一个有用的助手"},
                {"role": "user", "content": "请用一句话说明量子计算的基本原理"}
            ],
            max_tokens=200,
            temperature=0.7
        )

        message = response.choices[0].message
        usage = response.usage

        print(f"✅ 成功!")
        print(f"回复: {message.content}")
        print("-" * 50)
        print(f"Token 使用: prompt={usage.prompt_tokens}, completion={usage.completion_tokens}, total={usage.total_tokens}")
        print(f"TTFT: {response.nvext.timing.get('ttft_ms', 'N/A') if hasattr(response, 'nvext') else 'N/A'}ms")

        return True

    except Exception as e:
        print(f"❌ 错误: {type(e).__name__}: {e}")
        import traceback
        traceback.print_exc()
        return False
    finally:
        client.close()


def test_minimax_m2_7_stream():
    """流式测试 MiniMax M2.7"""

    api_key = os.getenv("NVIDIA_API_KEY")

    client = OpenAI(
        base_url="https://integrate.api.nvidia.com/v1",
        api_key=api_key,
        http_client=httpx.Client(verify=True, timeout=120)
    )

    print("🤖 测试 MiniMax M2.7（流式）")
    print("=" * 50)

    try:
        response = client.chat.completions.create(
            model="minimaxai/minimax-m2.7",
            messages=[{"role": "user", "content": "用一句话解释量子纠缠"}],
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
        test_minimax_m2_7_stream()
    else:
        test_minimax_m2_7()