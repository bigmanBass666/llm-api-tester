"""
Kimi (月之暗面) 平台模块
使用 Anthropic Messages API 协议
"""

SPEC = {
    "name": "kimi",
    "display_name": "Kimi (月之暗面)",
    "scraper_cls": None,
    "tester_cls": "KimiTester",
    "legacy_mode": False,
    "capabilities": [],
}

_LAZY_IMPORTS = {
    "KimiClient": (".client", "KimiClient"),
    "KimiTester": (".tester", "KimiTester"),
}


def __getattr__(name):
    if name in _LAZY_IMPORTS:
        module_path, attr = _LAZY_IMPORTS[name]
        import importlib
        module = importlib.import_module(module_path, package=__name__)
        return getattr(module, attr)
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


__all__ = ['KimiClient', 'KimiTester']
