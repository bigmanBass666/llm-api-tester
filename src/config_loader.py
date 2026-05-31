"""
统一配置加载器
安全地加载 API keys 和其他配置

所有 YAML 配置统一由 PlatformConfigLoader 加载，此类仅做薄封装。
"""

import os
from pathlib import Path
from typing import Optional, Dict, Any, List
from dotenv import load_dotenv

from .platform_config import PlatformConfigLoader


class ConfigLoader:
    """统一配置加载器 — 委托给 PlatformConfigLoader"""

    @classmethod
    def get_defaults(cls) -> Dict[str, Any]:
        """获取默认配置（从全局 defaults）"""
        configs = PlatformConfigLoader.load_all()
        for cfg in configs.values():
            if cfg.is_available:
                return {'concurrency': 5, 'timeout': 60, 'number': 20}
        return {}

    @classmethod
    def get_platform_defaults(cls, platform: str) -> Dict[str, Any]:
        """获取平台级默认配置"""
        configs = PlatformConfigLoader.load_all()
        defaults = {'concurrency': 5, 'timeout': 60, 'number': 20}
        for cfg in configs.values():
            if cfg.is_available and cfg.name == platform:
                break
        defaults['platform'] = platform
        return defaults

    @classmethod
    def setup_ssl_config(cls) -> None:
        from .ssl_config import setup_ssl_certificates

        cert_path = os.getenv('SSL_CERT_FILE') or os.getenv('REQUESTS_CA_BUNDLE')
        if not cert_path:
            configs = PlatformConfigLoader.load_all()
            first = next((c for c in configs.values() if c.is_available), None)
            if first and first.scraper:
                cert_path = None
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
        获取指定平台的 API key（委托给 platform_registry 统一实现）
        """
        from .platform_registry import get_api_key as _registry_get_api_key
        return _registry_get_api_key(platform)

    @classmethod
    def get_platform_config(cls, platform: str) -> Dict[str, Any]:
        """
        获取平台的完整配置（包括 base_url 等）
        """
        from .platform_registry import PlatformRegistry

        config_entry = PlatformRegistry().get(platform)
        if not config_entry:
            raise ValueError(f"未知平台: {platform}")

        return {
            'api_key': cls.get_api_key(platform),
            'base_url': config_entry.default_base_url,
            'name': config_entry.name,
            'display_name': config_entry.display_name,
        }

    @classmethod
    def validate_all(cls) -> Dict[str, bool]:
        """
        验证所有已启用平台的 API key 配置
        """
        configs = PlatformConfigLoader.load_all()
        results = {}
        for name, config in configs.items():
            if not config.is_available:
                continue
            try:
                cls.get_api_key(name)
                results[name] = True
            except ValueError:
                results[name] = False
        return results


def load_config() -> ConfigLoader:
    """快速加载配置（单例模式）"""
    ConfigLoader.load_env()
    return ConfigLoader


# ============================================
# 便捷函数（向后兼容）
# ============================================

def get_platform_scraper_config(platform: str):
    """获取爬虫配置（便捷函数）"""
    return PlatformConfigLoader.get_scraper_config(platform)


def get_platform_client_config(platform: str):
    """获取客户端配置（便捷函数）"""
    return PlatformConfigLoader.get_client_config(platform)


def get_available_platforms() -> List[str]:
    """获取所有可用平台名称列表"""
    return PlatformConfigLoader.get_available_platforms()


def get_api_key(platform: str) -> str:
    """快速获取 API key（委托给 platform_registry 统一实现）"""
    from .platform_registry import get_api_key as _registry_get_api_key
    return _registry_get_api_key(platform)


def require_api_key(platform: str) -> str:
    """强制要求 API key（用于需要认证的功能）"""
    return ConfigLoader.get_api_key(platform)
