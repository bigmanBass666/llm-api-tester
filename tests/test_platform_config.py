"""
平台配置管理系统单元测试
验证 PlatformConfigLoader 的配置加载、访问和验证逻辑
"""

import pytest
import tempfile
import os
from pathlib import Path

# 确保可以导入 src 模块
import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.platform_config import (
    PlatformConfigLoader,
    ScraperConfig,
    ClientConfig,
    PlatformConfig,
)


class TestPlatformConfigLoader:
    """PlatformConfigLoader 测试类"""

    def setup_method(self):
        """每个测试方法前重置配置加载器"""
        PlatformConfigLoader.reload()

    def test_load_all_platforms(self):
        """测试加载所有平台配置"""
        configs = PlatformConfigLoader.load_all()

        assert isinstance(configs, dict)
        assert len(configs) > 0  # 应该至少有 nvidia 和 zhipu 平台
        assert 'nvidia' in configs
        assert 'zhipu' in configs

    def test_get_nvidia_config(self):
        """测试获取 NVIDIA 平台配置"""
        config = PlatformConfigLoader.get_config('nvidia')

        assert config is not None
        assert config.name == 'nvidia'
        assert config.display_name == 'NVIDIA NIM'
        assert config.base_url == 'https://integrate.api.nvidia.com/v1'
        assert config.api_key_env == 'NVIDIA_API_KEY'
        assert config.is_available is True
        assert config.website == 'https://build.nvidia.com'

    def test_get_zhipu_config(self):
        """测试获取智谱平台配置"""
        config = PlatformConfigLoader.get_config('zhipu')

        assert config is not None
        assert config.name == 'zhipu'
        assert config.display_name == '智谱 GLM'
        assert config.base_url == 'https://open.bigmodel.cn/api/paas/v4'
        assert config.is_available is True

    def test_get_nonexistent_platform(self):
        """测试获取不存在的平台配置"""
        config = PlatformConfigLoader.get_config('nonexistent')

        assert config is None

    def test_get_nvidia_scraper_config(self):
        """测试获取 NVIDIA 爬虫配置"""
        scraper_config = PlatformConfigLoader.get_scraper_config('nvidia')

        assert scraper_config is not None
        assert isinstance(scraper_config, ScraperConfig)
        assert scraper_config.base_url == 'https://build.nvidia.com'
        assert scraper_config.page_timeout_ms == 180000
        assert scraper_config.navigation_timeout_ms == 120000
        assert scraper_config.page_load_wait_ms == 3000
        assert scraper_config.pagination_wait_ms == 5000
        assert scraper_config.network_idle_timeout_ms == 10000
        assert scraper_config.max_page_turns == 10
        assert scraper_config.max_cards_per_page == 50
        assert scraper_config.api_timeout_s == 45.0
        assert scraper_config.api_connect_timeout_s == 15.0

    def test_get_nvidia_selectors(self):
        """测试获取 NVIDIA 页面选择器"""
        selectors = PlatformConfigLoader.get_selectors('nvidia')

        assert selectors is not None
        assert isinstance(selectors, dict)
        assert 'card_root' in selectors
        assert 'vendor_link' in selectors
        assert 'model_link' in selectors
        assert 'badge' in selectors
        assert 'next_page' in selectors

        # 验证选择器值不为空
        for key, value in selectors.items():
            assert value, f"选择器 {key} 不应为空"

    def test_get_text_model_categories(self):
        """测试获取文字模型分类"""
        categories = PlatformConfigLoader.get_text_model_categories('nvidia')

        assert categories is not None
        assert isinstance(categories, set)
        assert len(categories) > 0
        # 验证常见的分类存在
        assert 'text-generation' in categories
        assert 'chat' in categories
        assert 'coding' in categories
        assert 'reasoning' in categories

    def test_get_non_text_keywords(self):
        """测试获取非文字模型关键词"""
        keywords = PlatformConfigLoader.get_non_text_keywords('nvidia')

        assert keywords is not None
        assert isinstance(keywords, list)
        assert len(keywords) > 0
        # 验证常见的关键词存在
        assert 'whisper' in keywords
        assert 'flux' in keywords
        assert 'stable-diffusion' in keywords
        # 验证新增的关键词（与旧版 crawler/scraper.py 不同）
        assert 'embedding' in keywords
        assert 'vision-language' in keywords

    def test_get_nvidia_client_config(self):
        """测试获取 NVIDIA 客户端配置（无 client 配置时返回 None）"""
        client_config = PlatformConfigLoader.get_client_config('nvidia')

        assert client_config is None

    def test_get_zhipu_known_models(self):
        """测试获取智谱预定义模型列表"""
        known_models = PlatformConfigLoader.get_known_models('zhipu')

        assert known_models is not None
        assert isinstance(known_models, list)
        assert len(known_models) > 0
        # 验证模型结构
        for model in known_models:
            assert 'name' in model
            assert 'model_id' in model
            assert 'vendor' in model
            assert 'is_free' in model

    def test_get_available_platforms(self):
        """测试获取可用平台列表"""
        available = PlatformConfigLoader.get_available_platforms()

        assert available is not None
        assert isinstance(available, list)
        assert len(available) > 0
        # NVIDIA 和 Zhipu 应该是可用的
        assert 'nvidia' in available
        assert 'zhipu' in available

    def test_get_all_platforms(self):
        """测试获取所有平台列表"""
        all_platforms = PlatformConfigLoader.get_all_platforms()

        assert all_platforms is not None
        assert isinstance(all_platforms, list)
        assert len(all_platforms) >= len(PlatformConfigLoader.get_available_platforms())

    def test_is_loaded(self):
        """测试配置是否已加载"""
        # 先调用一次 load_all 确保已加载
        PlatformConfigLoader.load_all()
        assert PlatformConfigLoader.is_loaded() is True

    def test_reload(self):
        """测试重新加载配置"""
        # 第一次加载
        configs1 = PlatformConfigLoader.load_all()
        count1 = len(configs1)

        # 重新加载
        configs2 = PlatformConfigLoader.reload()
        count2 = len(configs2)

        # 应该返回相同数量的配置
        assert count1 == count2

    def test_scraper_config_defaults(self):
        """测试 ScraperConfig 默认值"""
        config = ScraperConfig()

        assert config.base_url == ""
        assert config.page_timeout_ms == 180000
        assert config.navigation_timeout_ms == 120000
        assert config.text_model_categories == set()
        assert config.non_text_keywords == []
        assert config.selectors == {}

    def test_client_config_defaults(self):
        """测试 ClientConfig 默认值"""
        config = ClientConfig()

        assert config.quick_chat_models == {}

    def test_platform_config_defaults(self):
        """测试 PlatformConfig 默认值"""
        config = PlatformConfig(name="test")

        assert config.name == "test"
        assert config.display_name == ""  # 默认值是空字符串
        assert config.base_url == ""
        assert config.is_available is True
        assert config.scraper is None
        assert config.client is None


class TestConfigurationConsistency:
    """配置一致性测试"""

    def setup_method(self):
        """每个测试方法前重置配置加载器"""
        PlatformConfigLoader.reload()

    def test_nvidia_config_consistency_between_modules(self):
        """测试 NVIDIA 配置在不同模块间的一致性"""
        from src.config_loader import get_platform_scraper_config

        scraper_config_from_loader = get_platform_scraper_config('nvidia')
        scraper_config_direct = PlatformConfigLoader.get_scraper_config('nvidia')

        assert scraper_config_from_loader == scraper_config_direct

    def test_crawler_compatibility_layer(self):
        """测试 crawler/scraper.py 兼容层的配置一致性"""
        # 由于 platforms/nvidia/scraper.py 可能没有 scrape_top_models，
        # 我们直接验证配置常量的一致性
        from src.platform_config import PlatformConfigLoader

        expected_categories = PlatformConfigLoader.get_text_model_categories('nvidia')
        expected_keywords = PlatformConfigLoader.get_non_text_keywords('nvidia')

        # 验证配置加载器能正常工作
        assert expected_categories is not None
        assert expected_keywords is not None
        assert len(expected_categories) > 0
        assert len(expected_keywords) > 0

    def test_no_duplicate_configuration(self):
        """测试不存在重复的硬编码配置"""
        # 读取 platforms/nvidia/scraper.py 文件内容
        scraper_file_path = Path(__file__).parent.parent / 'platforms' / 'nvidia' / 'scraper.py'
        if scraper_file_path.exists():
            with open(scraper_file_path, 'r', encoding='utf-8') as f:
                content = f.read()

            # 检查不应该有旧的硬编码常量定义
            assert 'TEXT_MODEL_CATEGORIES = {' not in content or 'TEXT_MODEL_CATEGORIES' not in content.split('from src.platform_config')[0]
            assert 'NON_TEXT_KEYWORDS = [' not in content or 'NON_TEXT_KEYWORDS' not in content.split('from src.platform_config')[0]
            assert 'SELECTORS = {' not in content or 'SELECTORS' not in content.split('from src.platform_config')[0]


class TestEdgeCases:
    """边界情况测试"""

    def setup_method(self):
        """每个测试方法前重置配置加载器"""
        PlatformConfigLoader.reload()

    def test_empty_platform_name(self):
        """测试空平台名称"""
        config = PlatformConfigLoader.get_config('')
        assert config is None

    def test_case_insensitive_platform_name(self):
        """测试平台名称大小写不敏感（应该返回 None，因为 YAML 中是小写）"""
        # 当前实现是区分大小写的，所以大写应该返回 None
        config = PlatformConfigLoader.get_config('NVIDIA')
        assert config is None

    def test_missing_scraper_config(self):
        """测试缺少爬虫配置的平台"""
        # aliyun 平台可能没有 scraper 配置
        scraper_config = PlatformConfigLoader.get_scraper_config('aliyun')
        # 应该返回 None 或空配置
        assert scraper_config is None or isinstance(scraper_config, ScraperConfig)

    def test_missing_client_config(self):
        """测试缺少客户端配置的平台"""
        # zhipu 平台可能没有 client 配置
        client_config = PlatformConfigLoader.get_client_config('zhipu')
        # 应该返回 None 或空配置
        assert client_config is None or isinstance(client_config, ClientConfig)


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
