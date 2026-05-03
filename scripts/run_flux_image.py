"""
运行 flux.2-klein-4b 图像生成模型测试
"""

import os
import sys
import base64
import time
import requests

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from src.config_loader import ConfigLoader


def run():
    ConfigLoader.load_env('.env.local')
    api_key = os.getenv('NVIDIA_API_KEY')

    if not api_key:
        print("❌ 请先配置 NVIDIA_API_KEY")
        return

    print("=" * 60)
    print("🖼️  测试 flux.2-klein-4b 图像生成模型")
    print("=" * 60)

    invoke_url = "https://ai.api.nvidia.com/v1/genai/black-forest-labs/flux.2-klein-4b"

    headers = {
        "Authorization": f"Bearer {api_key}",
        "Accept": "application/json",
    }

    payload = {
        "prompt": "a macro wildlife photo of a green frog in a rainforest pond, highly detailed, eye-level shot",
        "width": 1024,
        "height": 1024,
        "seed": 0,
        "steps": 4
    }

    start_time = time.time()

    try:
        print("\n📝 生成提示词: 'a macro wildlife photo of a green frog in a rainforest pond'")

        response = requests.post(invoke_url, headers=headers, json=payload, timeout=120)
        response.raise_for_status()

        elapsed = time.time() - start_time

        response_body = response.json()

        img_data = response_body['artifacts'][0]['base64']
        img_bytes = base64.b64decode(img_data)

        output_path = "flux_test_result.jpg"
        with open(output_path, "wb") as f:
            f.write(img_bytes)

        print(f"\n✅ 成功! 耗时: {elapsed:.2f}秒")
        print(f"📁 图片已保存: {output_path}")
        print(f"📐 图片大小: {len(img_bytes) / 1024:.1f} KB")

    except Exception as e:
        elapsed = time.time() - start_time
        print(f"\n❌ 失败: {e}")
        print(f"⏱️  耗时: {elapsed:.2f}秒")


if __name__ == "__main__":
    run()
