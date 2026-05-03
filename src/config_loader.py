"""
统一配置加载器
安全地加载 API keys 和其他配置

已集成 PlatformConfigLoader，提供统一的平台配置管理。
"""

import os
from pathlib import Path
from typing import Optional, Dict, Any, List
from dotenv import load_dotenv
import yaml


class ConfigLoader:
    """统一配置加载器"""

    ENV_VAR_MAP = {
        'nvidia': 'NVIDIA_API_KEY',
        'zhipu': 'ZHIPU_API_KEY',
        'aliyun': 'DASHSCOPE_API_KEY',
        'tencent': 'TENCENTCLOUD_SECRET_ID',
    }

    _yaml_config: Optional[Dict[str, Any]] = None

    @classmethod
    def _load_yaml(cls) -> Dict[str, Any]:
        if cls._yaml_config is None:
            config_path = Path(__file__).parent.parent / 'configs' / 'platforms.yaml'
            if config_path.exists():
                with open(config_path, 'r', encoding='utf-8') as f:
                    cls._yaml_config = yaml.safe_load(f) or {}
            else:
                cls._yaml_config = {}
        return cls._yaml_config

    @classmethod
    def get_defaults(cls) -> Dict[str, Any]:
        return cls._load_yaml().get('defaults', {})

    @classmethod
    def get_platform_defaults(cls, platform: str) -> Dict[str, Any]:
        yaml_config = cls._load_yaml()
        defaults = dict(yaml_config.get('defaults', {}))
        platform_overrides = yaml_config.get('platforms', {}).get(platform, {})
        for key in ('concurrency', 'timeout', 'number'):
            if key in platform_overrides:
                defaults[key] = platform_overrides[key]
        return defaults

    @classmethod
    def setup_ssl_config(cls) -> None:
        from .ssl_config import setup_ssl_certificates

        cert_path = os.getenv('SSL_CERT_FILE') or os.getenv('REQUESTS_CA_BUNDLE')

        if not cert_path:
            yaml_config = cls._load_yaml()
            cert_path = yaml_config.get('ssl_cert_path')

        setup_ssl_certificates(cert_path=cert_path)

    @classmethod
    def load_env(cls, env_file: Optional[str] = None) -> None:
        if env_file:
            if Path(env_file).exists():
                load_dotenv(env_file, override=True)
                print(f"✅ 已加载环境配置文件: {env_file}")
            else:
                print(f"⚠️  环境配置文件不存在: {env_file}")
        else:
            for candidate in ['.env.local', '.env.development', '.env']:
                if Path(candidate).exists():
                    load_dotenv(candidate, override=True)
                    print(f"✅ 已自动加载: {candidate}")
                    break
            else:
                print("ℹ️  未找到 .env 文件，将使用系统环境变量")

        cls.setup_ssl_config()

    @classmethod
    def get_api_key(cls, platform: str) -> str:
        """
        获取指定平台的 API key

        Args:
            platform: 平台名称，如 'nvidia', 'zhipu', 'aliyun'

        Returns:
            API key 字符串

        Raises:
            ValueError: 如果未找到 API key
        """
        platform = platform.lower()

        if platform not in cls.ENV_VAR_MAP:
            available = ', '.join(cls.ENV_VAR_MAP.keys())
            raise ValueError(
                f"未知平台: {platform}\n"
                f"可用平台: {available}"
            )

        env_var_name = cls.ENV_VAR_MAP[platform]
        key = os.getenv(env_var_name)

        if not key:
            raise ValueError(
                f"❌ 缺少 {platform} 的 API Key\n"
                f"请设置环境变量: {env_var_name}\n"
                f"或在 .env.local 文件中配置\n"
                f"\n"
                f"配置方法：\n"
                f"  1. 复制 .env.example 为 .env.local\n"
                f"  2. 编辑 .env.local 填入真实 {env_var_name}\n"
                f"  3. 或直接在系统环境变量中设置"
            )

        return key

    @classmethod
    def get_platform_config(cls, platform: str) -> Dict[str, Any]:
        """
        获取平台的完整配置（包括 base_url 等）

        Args:
            platform: 平台名称

        Returns:
            配置字典，包含 api_key, base_url 等
        """
        from .platform_registry import PlatformRegistry

        registry = PlatformRegistry()
        platform_info = registry.get_platform_info(platform)

        if not platform_info:
            raise ValueError(f"未知平台: {platform}")

        config = {
            'api_key': cls.get_api_key(platform),
            'base_url': platform_info.get('default_base_url'),
            'name': platform_info.get('name'),
            'display_name': platform_info.get('display_name'),
        }

        return config

    @classmethod
    def validate_all(cls) -> Dict[str, bool]:
        """
        验证所有已启用平台的 API key 配置

        Returns:
            {平台: 是否配置成功} 的字典
        """
        from .platform_registry import PlatformRegistry

        # PlatformRegistry 使用 __new__ 实现单例，直接调用即可
        registry = PlatformRegistry()
        results = {}

        for platform, config in registry._platforms.items():
            if not config.is_available:
                continue

            try:
                cls.get_api_key(platform)
                results[platform] = True
            except ValueError:
                results[platform] = False

        return results


def load_config() -> ConfigLoader:
    """
    快速加载配置（单例模式）
    在应用启动时调用一次即可
    """
    ConfigLoader.load_env()
    return ConfigLoader


# ============================================
# 平台配置集成（使用 PlatformConfigLoader）
# ============================================

def get_platform_scraper_config(platform: str):
    """获取爬虫配置（便捷函数）

    Args:
        platform: 平台名称（如 'nvidia', 'zhipu'）

    Returns:
        ScraperConfig 实例或 None
    """
    from .platform_config import PlatformConfigLoader
    return PlatformConfigLoader.get_scraper_config(platform)


def get_platform_client_config(platform: str):
    """获取客户端配置（便捷函数）

    Args:
        platform: 平台名称（如 'nvidia', 'zhipu'）

    Returns:
        ClientConfig 实例或 None
    """
    from .platform_config import PlatformConfigLoader
    return PlatformConfigLoader.get_client_config(platform)


def get_available_platforms() -> List[str]:
    """获取所有可用平台名称列表"""
    from .platform_config import PlatformConfigLoader
    return PlatformConfigLoader.get_available_platforms()


# ============================================
# 便捷函数（向后兼容）
# ============================================

def get_api_key(platform: str) -> str:
    """快速获取 API key"""
    return ConfigLoader.get_api_key(platform)


def require_api_key(platform: str) -> str:
    """强制要求 API key（用于需要认证的功能）"""
    return ConfigLoader.get_api_key(platform)


__all__ = [
    'ConfigLoader',
    'load_config',
    'get_api_key',
    'require_api_key',
    'get_platform_scraper_config',
    'get_platform_client_config',
    'get_available_platforms',
]
