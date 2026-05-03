"""
统一平台配置管理系统
提供类型安全的配置数据结构和统一的配置加载接口
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Set
from pathlib import Path
import yaml


@dataclass
class ScraperConfig:
    """爬虫配置"""
    base_url: str = ""
    page_timeout_ms: int = 180000
    navigation_timeout_ms: int = 120000
    page_load_wait_ms: int = 3000
    pagination_wait_ms: int = 5000
    network_idle_timeout_ms: int = 10000
    max_page_turns: int = 10
    max_cards_per_page: int = 50
    api_timeout_s: float = 45.0
    api_connect_timeout_s: float = 15.0
    selectors: Dict[str, str] = field(default_factory=dict)
    text_model_categories: Set[str] = field(default_factory=set)
    non_text_keywords: List[str] = field(default_factory=list)
    known_models: List[Dict[str, object]] = field(default_factory=list)


@dataclass
class ClientConfig:
    """客户端配置"""
    quick_chat_models: Dict[str, str] = field(default_factory=dict)


@dataclass
class PlatformConfig:
    """平台完整配置"""
    name: str
    display_name: str = ""
    base_url: str = ""
    api_key_env: str = ""
    is_available: bool = True
    description: str = ""
    website: str = ""
    scraper: Optional[ScraperConfig] = None
    client: Optional[ClientConfig] = None


class PlatformConfigLoader:
    """平台配置加载器

    提供统一的配置访问接口，所有模块通过此类获取平台配置。
    支持配置缓存和热更新。
    """

    _configs: Dict[str, PlatformConfig] = {}
    _yaml_path: Path = Path(__file__).parent.parent / 'configs' / 'platforms.yaml'
    _loaded: bool = False

    @classmethod
    def load_all(cls) -> Dict[str, PlatformConfig]:
        """加载所有平台配置

        Returns:
            {平台名称: 平台配置} 的字典

        Raises:
            FileNotFoundError: 配置文件不存在
            yaml.YAMLError: YAML 格式错误
        """
        if cls._loaded and cls._configs:
            return cls._configs

        if not cls._yaml_path.exists():
            raise FileNotFoundError(f"配置文件不存在: {cls._yaml_path}")

        try:
            with open(cls._yaml_path, 'r', encoding='utf-8') as f:
                yaml_data = yaml.safe_load(f) or {}
        except yaml.YAMLError as e:
            raise yaml.YAMLError(f"YAML 配置文件格式错误: {e}")

        defaults = yaml_data.get('defaults', {})
        platforms_data = yaml_data.get('platforms', {})

        for platform_name, platform_data in platforms_data.items():
            config = cls._build_platform_config(platform_name, platform_data, defaults)
            cls._configs[platform_name] = config

        cls._loaded = True
        return cls._configs

    @classmethod
    def _build_platform_config(
        cls,
        name: str,
        platform_data: dict,
        defaults: dict
    ) -> PlatformConfig:
        """构建单个平台配置

        Args:
            name: 平台名称
            platform_data: 平台特定配置数据
            defaults: 全局默认配置

        Returns:
            PlatformConfig 实例
        """
        scraper_data = platform_data.get('scraper', {})
        client_data = platform_data.get('client', {})

        scraper_config = None
        if scraper_data:
            scraper_config = ScraperConfig(
                base_url=scraper_data.get('base_url', platform_data.get('base_url', '')),
                page_timeout_ms=scraper_data.get('page_timeout_ms', 180000),
                navigation_timeout_ms=scraper_data.get('navigation_timeout_ms', 120000),
                page_load_wait_ms=scraper_data.get('page_load_wait_ms', 3000),
                pagination_wait_ms=scraper_data.get('pagination_wait_ms', 5000),
                network_idle_timeout_ms=scraper_data.get('network_idle_timeout_ms', 10000),
                max_page_turns=scraper_data.get('max_page_turns', 10),
                max_cards_per_page=scraper_data.get('max_cards_per_page', 50),
                api_timeout_s=scraper_data.get('api_timeout_s', 45.0),
                api_connect_timeout_s=scraper_data.get('api_connect_timeout_s', 15.0),
                selectors=scraper_data.get('selectors', {}),
                text_model_categories=set(scraper_data.get('text_model_categories', [])),
                non_text_keywords=scraper_data.get('non_text_keywords', []),
                known_models=scraper_data.get('known_models', []),
            )

        client_config = None
        if client_data:
            client_config = ClientConfig(
                quick_chat_models=client_data.get('quick_chat_models', {}),
            )

        return PlatformConfig(
            name=name,
            display_name=platform_data.get('display_name', name),
            base_url=platform_data.get('base_url', ''),
            api_key_env=platform_data.get('api_key_env', ''),
            is_available=platform_data.get('is_available', True),
            description=platform_data.get('description', ''),
            website=platform_data.get('website', ''),
            scraper=scraper_config,
            client=client_config,
        )

    @classmethod
    def get_config(cls, platform_name: str) -> Optional[PlatformConfig]:
        """获取指定平台配置

        Args:
            platform_name: 平台名称（如 'nvidia', 'zhipu'）

        Returns:
            PlatformConfig 实例，如果未找到则返回 None
        """
        cls.load_all()
        return cls._configs.get(platform_name)

    @classmethod
    def get_scraper_config(cls, platform_name: str) -> Optional[ScraperConfig]:
        """获取爬虫配置（便捷方法）

        Args:
            platform_name: 平台名称

        Returns:
            ScraperConfig 实例，如果未找到则返回 None
        """
        config = cls.get_config(platform_name)
        return config.scraper if config else None

    @classmethod
    def get_client_config(cls, platform_name: str) -> Optional[ClientConfig]:
        """获取客户端配置（便捷方法）

        Args:
            platform_name: 平台名称

        Returns:
            ClientConfig 实例，如果未找到则返回 None
        """
        config = cls.get_config(platform_name)
        return config.client if config else None

    @classmethod
    def get_text_model_categories(cls, platform_name: str) -> Set[str]:
        """获取文字模型分类（便捷方法）

        Args:
            platform_name: 平台名称

        Returns:
            文字模型分类集合，如果未找到则返回空集合
        """
        scraper_config = cls.get_scraper_config(platform_name)
        return scraper_config.text_model_categories if scraper_config else set()

    @classmethod
    def get_non_text_keywords(cls, platform_name: str) -> List[str]:
        """获取非文字模型关键词（便捷方法）

        Args:
            platform_name: 平台名称

        Returns:
            非文字模型关键词列表，如果未找到则返回空列表
        """
        scraper_config = cls.get_scraper_config(platform_name)
        return scraper_config.non_text_keywords if scraper_config else []

    @classmethod
    def get_selectors(cls, platform_name: str) -> Dict[str, str]:
        """获取页面选择器配置（便捷方法）

        Args:
            platform_name: 平台名称

        Returns:
            选择器字典，如果未找到则返回空字典
        """
        scraper_config = cls.get_scraper_config(platform_name)
        return scraper_config.selectors if scraper_config else {}

    @classmethod
    def get_known_models(cls, platform_name: str) -> List[Dict[str, object]]:
        """获取预定义模型列表（便捷方法）

        Args:
            platform_name: 平台名称

        Returns:
            模型列表，如果未找到则返回空列表
        """
        scraper_config = cls.get_scraper_config(platform_name)
        return scraper_config.known_models if scraper_config else []

    @classmethod
    def get_available_platforms(cls) -> List[str]:
        """获取所有可用平台名称

        Returns:
            可用平台名称列表
        """
        cls.load_all()
        return [name for name, config in cls._configs.items() if config.is_available]

    @classmethod
    def get_all_platforms(cls) -> List[str]:
        """获取所有平台名称（包括不可用的）

        Returns:
            所有平台名称列表
        """
        cls.load_all()
        return list(cls._configs.keys())

    @classmethod
    def reload(cls):
        """重新加载配置（用于配置更新后）"""
        cls._configs.clear()
        cls._loaded = False
        return cls.load_all()

    @classmethod
    def is_loaded(cls) -> bool:
        """检查配置是否已加载"""
        return cls._loaded and bool(cls._configs)


__all__ = [
    'ScraperConfig',
    'ClientConfig',
    'PlatformConfig',
    'PlatformConfigLoader',
]
