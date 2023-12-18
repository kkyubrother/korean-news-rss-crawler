import requests
from typing import Optional


# 낮은 보안인 경우를 무시한다
requests.packages.urllib3.disable_warnings()
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:120.0) Gecko/20100101 Firefox/120.0"
}

__CACHE = {}


def request_get(url: str) -> Optional[str]:
    """url 텍스트 요청(자체 캐싱)"""
    try:
        if url in __CACHE:
            response = __CACHE[url]
        else:
            response = requests.get(url, headers=HEADERS)
            __CACHE[url] = response
        response.raise_for_status()
        return response.text
    except requests.exceptions.RequestException as e:
        pass
    return None

