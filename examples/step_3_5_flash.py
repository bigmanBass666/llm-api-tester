"""
Step 3.5 Flash 模型调用示例
StepFun 的推理模型
注意：复杂问题可能只输出推理内容，不输出最终答案
"""

import os
import httpx
from openai import OpenAI

# 设置 SSL 证书（Windows 需要）
os.environ.setdefault('SSL_CERT_FILE', r'D:\apps\python312\Lib\site-packages\certifi\cacert.pem')
os.environ.setdefault('REQUESTS_CA_BUNDLE', r'D:\apps\python312\Lib\site-packages\certifi\cacert.pem')


def test_step_3_5_flash():
    """测试 Step 3.5 Flash 模型"""

    api_key = os.getenv("NVIDIA_API_KEY")

    client = OpenAI(
        base_url="https://integrate.api.nvidia.com/v1",
        api_key=api_key,
        http_client=httpx.Client(verify=True, timeout=120)
    )

    print("🧠 测试 Step 3.5 Flash")
    print("=" * 50)

    try:
        payload = {
            "model": "stepfun-ai/step-3.5-flash",
            "messages": [
                {"role": "system", "content": "你是有用的助手"},
                {"role": "user", "content": "请回复'OK'"}
            ],
            "max_tokens": 100,
            "stream": False,
            "chat_template_kwargs": {"enable_thinking": True}
        }

        response = client.chat.completions.create(
            model=payload["model"],
            messages=payload["messages"],
            max_tokens=payload["max_tokens"],
            stream=payload["stream"],
            extra_body={"chat_template_kwargs": {"enable_thinking": True}}
        )

        message = response.choices[0].message

        print(f"✅ 成功!")
        print(f"内容: {message.content}")
        print(f"推理内容: {getattr(message, 'reasoning_content', '无')}")
        print(f"完成原因: {response.choices[0].finish_reason}")

        # 检查是否只输出了推理
        if message.content is None and getattr(message, 'reasoning_content', None):
            print("⚠️ 警告: 只输出了推理内容，没有最终答案")

        return True

    except Exception as e:
        print(f"❌ 错误: {type(e).__name__}: {e}")
        import traceback
        traceback.print_exc()
        return False
    finally:
        client.close()


def test_step_3_5_flash_stream():
    """流式测试 Step 3.5 Flash"""

    api_key = os.getenv("NVIDIA_API_KEY")

    client = OpenAI(
        base_url="https://integrate.api.nvidia.com/v1",
        api_key=api_key,
        http_client=httpx.Client(verify=True, timeout=120)
    )

    print("🧠 测试 Step 3.5 Flash（流式）")
    print("=" * 50)

    try:
        response = client.chat.completions.create(
            model="stepfun-ai/step-3.5-flash",
            messages=[{"role": "user", "content": "请回复'OK'"}],
            max_tokens=200,
            stream=True,
            extra_body={"chat_template_kwargs": {"enable_thinking": True}}
        )

        collected_content = []
        collected_reasoning = []

        for chunk in response:
            if chunk.choices and chunk.choices[0].delta:
                delta = chunk.choices[0].delta

                content = delta.content
                reasoning = getattr(delta, 'reasoning_content', None)

                if content:
                    collected_content.append(content)
                    print(content, end="", flush=True)

                if reasoning:
                    collected_reasoning.append(reasoning)

        print(f"\n✅ 流式完成!")
        print(f"最终内容: {''.join(collected_content)}")
        print(f"推理内容: {''.join(collected_reasoning)}")

        if not collected_content:
            print("⚠️ 警告: 模型只输出了推理")

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
        test_step_3_5_flash_stream()
    else:
        test_step_3_5_flash()