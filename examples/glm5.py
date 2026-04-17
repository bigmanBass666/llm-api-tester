"""
Z.ai GLM 5 模型调用示例
⚠️ CAUTION: 此模型目前处于不可用状态
状态：出现在模型列表但 API 请求无响应（超时）
"""

import os
import httpx
from openai import OpenAI

# 设置 SSL 证书（Windows 需要）
os.environ.setdefault('SSL_CERT_FILE', r'D:\apps\python312\Lib\site-packages\certifi\cacert.pem')
os.environ.setdefault('REQUESTS_CA_BUNDLE', r'D:\apps\python312\Lib\site-packages\certifi\cacert.pem')


def test_glm5():
    """测试 GLM 5 模型（当前不可用）"""

    api_key = os.getenv("NVIDIA_API_KEY")
    if not api_key:
        raise ValueError("请设置 NVIDIA_API_KEY 环境变量")

    client = OpenAI(
        base_url="https://integrate.api.nvidia.com/v1",
        api_key=api_key,
        http_client=httpx.Client(verify=True, timeout=30)
    )

    print("⚠️ 测试 Z.ai GLM 5（已知不可用）")
    print("=" * 50)
    print("预计结果：连接超时，服务器无响应")
    print("参考日期：2026-04-14")
    print("-" * 50)

    try:
        response = client.chat.completions.create(
            model="z-ai/glm5",
            messages=[{"role": "user", "content": "请回复'OK'"}],
            max_tokens=50,
            stream=False
        )

        message = response.choices[0].message
        print(f"✅ 奇迹！模型开始响应了！")
        print(f"内容: {message.content}")
        print(f"推理内容: {getattr(message, 'reasoning_content', '无')}")
        return True

    except Exception as e:
        print(f"❌ 连接失败（正常现象）")
        print(f"错误类型: {type(e).__name__}")
        print(f"详情: {e}")
        return False
    finally:
        client.close()


def check_glm5_status():
    """检查 GLM 5 当前状态"""
    import subprocess

    print("🔍 检查 GLM 5 状态...")

    # 调用 nvidia_client.py 的 list_models 查看
    try:
        result = subprocess.run(
            ["python", "-c", """
import os
os.environ.setdefault('SSL_CERT_FILE', r'D:\\apps\\python312\\Lib\\site-packages\\certifi\\cacert.pem')
from src.nvidia_client import NvidiaClient
c = NvidiaClient(api_key=os.getenv("NVIDIA_API_KEY"))
models = c.list_models()
zai_models = [m for m in models if 'z-ai' in m.id.lower()]
for m in zai_models:
    print(f'模型: {m.id}')
    print(f'  平台: {m.platform}')
c.close()
"""],
            capture_output=True,
            text=True,
            timeout=30
        )

        print(result.stdout)
        if result.stderr:
            print("错误:", result.stderr)

    except Exception as e:
        print(f"无法检查: {e}")


if __name__ == "__main__":
    import sys

    if len(sys.argv) > 1 and sys.argv[1] == "--status":
        check_glm5_status()
    else:
        test_glm5()