"""
统一SSL证书配置模块
自动查找证书路径，支持环境变量覆盖
"""

import os
from pathlib import Path
from typing import Optional


def get_certifi_bundle_path() -> Optional[str]:
    try:
        import certifi
        return certifi.where()
    except ImportError:
        return None


def setup_ssl_certificates(cert_path: Optional[str] = None, force: bool = False) -> None:
    if not force and os.getenv('SSL_CERT_FILE'):
        return

    if cert_path:
        final_path = cert_path
    else:
        final_path = os.getenv('SSL_CERT_FILE') or os.getenv('REQUESTS_CA_BUNDLE')

    if not final_path:
        final_path = get_certifi_bundle_path()

    if final_path:
        os.environ['SSL_CERT_FILE'] = final_path
        os.environ['REQUESTS_CA_BUNDLE'] = final_path


def get_ssl_cert_path() -> Optional[str]:
    return os.getenv('SSL_CERT_FILE') or os.getenv('REQUESTS_CA_BUNDLE')


__all__ = ['setup_ssl_certificates', 'get_ssl_cert_path', 'get_certifi_bundle_path']
