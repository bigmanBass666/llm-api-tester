"""
NVIDIA 平台模块
"""

SPEC = {
    "name": "nvidia",
    "display_name": "NVIDIA NIM",
    "scraper_cls": "NvidiaScraper",
    "tester_cls": "NvidiaTester",
    "legacy_mode": True,
    "capabilities": ["reasoning", "resume", "pagination", "image_generation"],
}

_LAZY_IMPORTS = {
    "NvidiaScraper": (".scraper", "NvidiaScraper"),
    "NvidiaTester": (".tester", "NvidiaTester"),
}


def __getattr__(name):
    if name in _LAZY_IMPORTS:
        module_path, attr = _LAZY_IMPORTS[name]
        import importlib
        module = importlib.import_module(module_path, package=__name__)
        return getattr(module, attr)
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


__all__ = ['NvidiaScraper', 'NvidiaTester']
