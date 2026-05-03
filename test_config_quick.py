"""快速测试配置系统"""
from src.platform_config import PlatformConfigLoader

print('=' * 60)
print('🧪 测试配置加载系统')
print('=' * 60)

# 1. 加载所有平台
configs = PlatformConfigLoader.load_all()
print(f'\n✅ 已加载 {len(configs)} 个平台:')
for name in configs:
    print(f'  - {name}')

# 2. 获取NVIDIA配置
nvidia = PlatformConfigLoader.get_config('nvidia')
print(f'\n✅ NVIDIA 配置:')
print(f'  显示名称: {nvidia.display_name}')
print(f'  API地址: {nvidia.base_url}')
print(f'  官网: {nvidia.website}')

# 3. 获取爬虫配置
scraper_cfg = PlatformConfigLoader.get_scraper_config('nvidia')
print(f'\n✅ NVIDIA 爬虫配置:')
print(f'  目标网址: {scraper_cfg.base_url}')
print(f'  页面超时: {scraper_cfg.page_timeout_ms/1000:.0f}秒')
print(f'  最大翻页: {scraper_cfg.max_page_turns}页')

# 4. 获取选择器
selectors = PlatformConfigLoader.get_selectors('nvidia')
print(f'\n✅ CSS选择器 ({len(selectors)}个):')
for key, value in selectors.items():
    print(f'  {key}: {value[:50]}...')

# 5. 获取过滤规则
categories = PlatformConfigLoader.get_text_model_categories('nvidia')
keywords = PlatformConfigLoader.get_non_text_keywords('nvidia')
print(f'\n✅ 模型过滤规则:')
print(f'  文字模型分类: {len(categories)}个')
print(f'  非文字关键词: {len(keywords)}个 (前5个: {keywords[:5]})')

print('\n' + '=' * 60)
print('🎉 所有配置加载测试通过!')
print('=' * 60)
