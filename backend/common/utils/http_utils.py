from typing import Tuple
import requests
from urllib.parse import urlparse
from requests.exceptions import RequestException, Timeout

def verify_url(url: str, timeout: int = 5) -> Tuple[bool, str]:
    try:
        parsed = urlparse(url)
        if not all([parsed.scheme, parsed.netloc]):
            return False, "无效的 URL 格式"

        if parsed.scheme not in ['http', 'https']:
            return False, "URL 必须以 http 或 https 开头"

        response = requests.get(
            url,
            timeout=timeout,
            verify=False  # 忽略 SSL 证书验证
        )
        
        if response.status_code < 400:
            return True, "URL 可达"
        else:
            return False, f"服务器返回错误状态码: {response.status_code}"
            
    except Timeout:
        return False, f"连接超时 (>{timeout}秒)"
    except RequestException as e:
        return False, f"连接失败: {str(e)}"
    except Exception as e:
        return False, f"验证过程发生错误: {str(e)}"