import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from crawler.errors import (
    APIError,
    AuthenticationError,
    RateLimitError,
    ModelNotFoundError,
    ServerError,
    TimeoutError,
    ScrapingError,
)


def test_api_error_base():
    err = APIError("test error", status_code=500, details={"key": "val"})
    assert err.message == "test error"
    assert err.status_code == 500
    assert err.details == {"key": "val"}
    assert str(err) == "test error"


def test_authentication_error_default():
    err = AuthenticationError()
    assert err.status_code == 401
    assert "认证失败" in err.message


def test_authentication_error_custom():
    err = AuthenticationError("custom auth fail", details={"url": "/v1/chat"})
    assert err.message == "custom auth fail"
    assert err.details["url"] == "/v1/chat"


def test_rate_limit_error():
    err = RateLimitError()
    assert err.status_code == 429
    assert "频率超限" in err.message


def test_model_not_found_error_with_id():
    err = ModelNotFoundError(model_id="deepseek-v4")
    assert err.status_code == 404
    assert "deepseek-v4" in err.message


def test_model_not_found_error_custom():
    err = ModelNotFoundError(message="custom 404")
    assert err.message == "custom 404"


def test_server_error_with_code():
    err = ServerError(status_code=503)
    assert err.status_code == 503
    assert "服务器错误" in err.message


def test_server_error_custom():
    err = ServerError(status_code=502, message="Bad Gateway")
    assert err.status_code == 502
    assert err.message == "Bad Gateway"


def test_timeout_error():
    err = TimeoutError()
    assert err.status_code is None
    assert "超时" in err.message


def test_scraping_error_full():
    err = ScrapingError("selector failed", selector=".card-root", page_url="https://example.com")
    assert err.selector == ".card-root"
    assert err.page_url == "https://example.com"
    assert err.details["selector"] == ".card-root"
    assert err.details["page_url"] == "https://example.com"


def test_scraping_error_minimal():
    err = ScrapingError("simple")
    assert err.selector is None
    assert err.page_url is None


def test_all_errors_are_api_error_subclass():
    assert issubclass(AuthenticationError, APIError)
    assert issubclass(RateLimitError, APIError)
    assert issubclass(ModelNotFoundError, APIError)
    assert issubclass(ServerError, APIError)
    assert issubclass(TimeoutError, APIError)


def test_scraping_error_is_not_api_error():
    assert not issubclass(ScrapingError, APIError)
    assert issubclass(ScrapingError, Exception)
