"""
Kimi API 客户端
使用 Anthropic Messages API 协议
"""

import os
import yaml
from pathlib import Path
from typing import List
from platforms.common.openai_compatible_client import KimiClient as BaseKimiClient
from src.models import ModelInfo
from src.platform_registry import register_platform


class KimiClientWithConfig(BaseKimiClient):
    """Kimi 客户端，支持从 platforms.yaml 读取模型列表"""

    def list_models(self) -> List[ModelInfo]:
        """获取模型列表，优先使用 API 返回，如果只有一个模型则从配置文件读取"""
        # 先尝试从 API 获取
        api_models = super().list_models()

        # 如果 API 返回多个模型，直接使用
        if len(api_models) > 1:
            return api_models

        # 否则从配置文件读取
        try:
            config_path = Path(__file__).parent.parent.parent / 'configs' / 'platforms.yaml'
            with open(config_path, 'r', encoding='utf-8') as f:
                config = yaml.safe_load(f)

            kimi_config = config.get('platforms', {}).get('kimi', {})
            models_config = kimi_config.get('models', {}).get('free', [])

            if models_config:
                return [
                    ModelInfo(
                        id=m['id'],
                        name=m.get('name', m['id']),
                        vendor='kimi',
                        is_free_endpoint=True,
                        is_available=True,
                    )
                    for m in models_config
                ]
        except Exception as e:
            print(f"从配置文件读取模型列表失败: {e}")

        # 如果配置文件也失败，返回 API 返回的模型
        return api_models


# 注册平台
KimiClient = register_platform(
    name="kimi",
    display_name="Kimi (月之暗面)",
    client_class=KimiClientWithConfig,
    default_base_url="https://api.kimi.com/coding/",
    api_key_env="KIMI_API_KEY",  # pragma: allowlist secret
    description="月之暗面 Kimi 大语言模型 API（Anthropic 协议）",
    website="https://platform.kimi.com"
)(KimiClientWithConfig)

__all__ = ['KimiClient']
