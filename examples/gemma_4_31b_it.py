"""
Google Gemma 4 31B IT 模型调用示例
推理模型，需要启用 thinking 模式
"""

import os
import requests
import time
import json

# 禁用 SSL 警告
import urllib3
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)


def test_gemma_4_31b_it():
    """测试 Gemma 4 31B IT 模型（官方示例格式）"""

    api_key = os.getenv("NVIDIA_API_KEY")
    invoke_url = "https://integrate.api.nvidia.com/v1/chat/completions"
    stream = True

    headers = {
        "Authorization": f"Bearer {api_key}",
        "Accept": "text/event-stream" if stream else "application/json"
    }

    payload = {
        "model": "google/gemma-4-31b-it",
        "messages": [{"role": "user", "content": "请回复'OK'"}],
        "max_tokens": 512,
        "temperature": 1.00,
        "top_p": 0.95,
        "stream": stream,
        "chat_template_kwargs": {"enable_thinking": True}
    }

    print("🧠 测试 Google Gemma 4 31B IT（推理模式）")
    print("=" * 50)

    start_time = time.time()

    try:
        response = requests.post(
            invoke_url,
            headers=headers,
            json=payload,
            stream=stream,
            timeout=120,
            verify=False  # 禁用 SSL 验证
        )

        reasoning_parts = []
        content_parts = []
        chunk_count = 0

        for line in response.iter_lines():
            if line:
                decoded_line = line.decode("utf-8")

                if decoded_line.startswith("data: "):
                    data_str = decoded_line[6:]

                    if data_str.strip() == "[DONE]":
                        break

                    try:
                        data = json.loads(data_str)

                        if "choices" in data and data["choices"]:
                            delta = data["choices"][0].get("delta", {})

                            reasoning = delta.get("reasoning_content")
                            content = delta.get("content")

                            if reasoning:
                                reasoning_parts.append(reasoning)
                                print(f"[推理] {reasoning}", end="", flush=True)

                            if content:
                                content_parts.append(content)
                                print(f"[内容] {content}", end="", flush=True)

                            chunk_count += 1

                    except json.JSONDecodeError:
                        continue

        elapsed = time.time() - start_time

        print(f"\n" + "=" * 50)
        print(f"✅ 测试完成!")
        print(f"耗时: {elapsed:.1f}s")
        print(f"总chunk数: {chunk_count}")

        full_reasoning = "".join(reasoning_parts)
        full_content = "".join(content_parts)

        if full_reasoning:
            print(f"推理内容: {full_reasoning}")
        if full_content:
            print(f"最终回复: {full_content}")

        return True

    except Exception as e:
        print(f"❌ 错误: {type(e).__name__}: {e}")
        return False


def test_gemma_simple():
    """简单测试 Gemma（非推理模式）"""

    api_key = os.getenv("NVIDIA_API_KEY")
    invoke_url = "https://integrate.api.nvidia.com/v1/chat/completions"

    headers = {
        "Authorization": f"Bearer {api_key}",
        "Accept": "application/json"
    }

    payload = {
        "model": "google/gemma-4-31b-it",
        "messages": [{"role": "user", "content": "请回复'OK'"}],
        "max_tokens": 100,
        "temperature": 0.7,
        "stream": False
    }

    print("🧠 测试 Google Gemma 4 31B IT（简单模式）")
    print("=" * 50)

    try:
        response = requests.post(
            invoke_url,
            headers=headers,
            json=payload,
            timeout=60,
            verify=False
        )

        if response.status_code == 200:
            result = response.json()
            message = result["choices"][0]["message"]

            print(f"✅ 成功!")
            print(f"回复: {message.get('content', '无内容')}")
            print(f"推理: {message.get('reasoning_content', '无推理')}")

            return True
        else:
            print(f"❌ HTTP {response.status_code}: {response.text}")
            return False

    except Exception as e:
        print(f"❌ 错误: {type(e).__name__}: {e}")
        return False


if __name__ == "__main__":
    print("选择测试模式:")
    print("1. 推理模式（流式）")
    print("2. 简单模式（非流式）")

    choice = input("输入选择 (1/2): ").strip()

    if choice == "1":
        test_gemma_4_31b_it()
    elif choice == "2":
        test_gemma_simple()
    else:
        print("默认测试推理模式...")
        test_gemma_4_31b_it()