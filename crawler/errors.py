"""统一错误类型定义

提供细粒度的 API 错误分类，替代裸 except 捕获。
"""

from abc import ABC


class APIError(Exception):
    """API 调用基础异常"""

    def __init__(self, message: str, status_code: int = None, details: dict = None):
        self.message = message
        self.status_code = status_code
        self.details = details or {}
        super().__init__(self.message)


class AuthenticationError(APIError):
    """认证失败 (401)"""

    def __init__(self, message: str = "认证失败，请检查 API Key 是否正确", details: dict = None):
        super().__init__(message, status_code=401, details=details)


class RateLimitError(APIError):
    """请求频率超限 (429)"""

    def __init__(self, message: str = "请求频率超限，请稍后重试", details: dict = None):
        super().__init__(message, status_code=429, details=details)


class ModelNotFoundError(APIError):
    """模型不存在 (404)"""

    def __init__(self, model_id: str = None, message: str = None, details: dict = None):
        msg = message or (f"模型不存在: {model_id}" if model_id else "模型不存在")
        super().__init__(msg, status_code=404, details=details)


class ServerError(APIError):
    """服务器错误 (5xx)"""

    def __init__(self, status_code: int = None, message: str = "服务器错误", details: dict = None):
        super().__init__(message, status_code=status_code, details=details)


class TimeoutError(APIError):
    """请求超时"""

    def __init__(self, message: str = "请求超时", details: dict = None):
        super().__init__(message, status_code=None, details=details)


class ScrapingError(Exception):
    """页面爬取异常"""

    def __init__(self, message: str, selector: str = None, page_url: str = None):
        self.selector = selector
        self.page_url = page_url
        details = {"selector": selector, "page_url": page_url}
        super().__init__(message)
        self.details = details
