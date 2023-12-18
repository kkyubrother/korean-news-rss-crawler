import re
import logging
import feedparser
from lxml import etree
from bs4 import BeautifulSoup
from typing import Optional, Union
from urllib.parse import urlparse
from util.req import request_get


__P_REMOVE_CAPTION = re.compile(r'<!--(.*?)-->', flags=re.DOTALL)
__P_FIND_RSS_LINK_TAG = re.compile(r"<link[^<]+?type=\"application/rss\+xml\".+?>")
__P_FIND_RSS_URL = re.compile(r"(?<=href=\").+?(?=\")")

__P_REMOVE_ETC_TAG = re.compile(r"src=\".+?\"")
__P_REMOVE_MULTI_EMPTY = re.compile(r"\s\s+")
__P_FIND_RSS_URL_IN_SRC = re.compile(r"(https?:/)?/\S*?rss\S*?(?=[\"'<])")
__P_FIND_RSS2_URL_IN_SRC = re.compile(r"(https?:/)?/\S*?feed\S*?(?=[\"'<])")


class ValidateRssUrlResult:
    category: Optional[str]
    url: str
    need_parse: bool
    text: Optional[str]

    def __init__(self, category: Optional[str], url: str, need_parse: bool, text: Optional[str] = None):
        self.category = category
        self.url = url
        self.need_parse = need_parse
        self.text = text

    @classmethod
    def build_rss(cls, url: str, category: str = "전체"):
        return cls(category=category, url=url, need_parse=False, text=None)

    @classmethod
    def build_html(cls, url: str, text: str):
        return cls(category=None, url=url, need_parse=True, text=text)

    def __str__(self):
        return f"RSS(url={self.url}, category={self.category}, need_parse={self.need_parse})"

    def to_dict(self):
        return {
            'category': self.category,
            'url': self.url,
        }


def _extract_rss_list_in_html_type_nd(site_text: str) -> list[ValidateRssUrlResult]:
    """nd 에서 제작한 웹사이트 형식의 rss 주소를 추출한다."""
    rss_urls = []
    for item in BeautifulSoup(site_text, 'html.parser').select("table.hover tr"):
        if category_item := item.select_one("th"):
            if rss_url_item := item.select_one("td a"):
                category = category_item.get_text(strip=True)
                rss_url = rss_url_item.get_text(strip=True)
                rss_urls.append(ValidateRssUrlResult.build_rss(rss_url, category))
    return rss_urls


def _validate_rss_url(rss_url: str) -> Union[None, ValidateRssUrlResult]:
    """url 이 올바른 rss 인지 검증한다."""
    body = request_get(rss_url)
    if not body:
        return None


    # 가져온 페이지를 feedparser를 사용하여 파싱
    feed = feedparser.parse(body)

    # feed.bozo 속성은 파싱 중 오류가 있는지 여부를 나타냅니다.
    # 실제 encoding 이 다른 경우가 많아, 해당 오류는 무시
    if feed.bozo:
        # 인코딩 문제가 아닌 경우
        if not isinstance(feed.bozo_exception, (
                feedparser.exceptions.CharacterEncodingOverride,
                feedparser.exceptions.CharacterEncodingUnknown)):
            try:
                etree.HTML(body)
                return ValidateRssUrlResult.build_html(rss_url, body)

            except:
                return None

    # RSS 피드의 버전 출력
    rss_version = feed.version
    logging.info(f"{rss_url} RSS 버전: {rss_version}")
    return ValidateRssUrlResult.build_rss(rss_url)


def _normalize_url(base_url: str, target_url: str) -> str:
    """추출한 url 을 정규화한다."""
    if target_url.startswith("http://") or target_url.startswith("https://"):
        rss_url = target_url
    else:
        pared_base_url = urlparse(base_url)
        if target_url.startswith("//"):
            rss_url = f"{pared_base_url.scheme}:{target_url}"
        elif target_url.startswith("/"):
            rss_url = f"{pared_base_url.scheme}://{pared_base_url.netloc}{target_url}"
        else:
            rss_url = f"{pared_base_url.scheme}://{pared_base_url.netloc}/{target_url}"
    return rss_url


def find_rss_in_link_tag(base_url: str, site_text: str) -> list[ValidateRssUrlResult]:
    """Link 테그 안에서 rss 주소 찾기"""
    rss_list = []
    text = __P_REMOVE_CAPTION.sub("", site_text)

    for m_tag in __P_FIND_RSS_LINK_TAG.findall(text):
        if m_rss := __P_FIND_RSS_URL.search(m_tag):
            rss_url = _normalize_url(base_url, m_rss.group())
            if rss := _validate_rss_url(rss_url):
                if not rss.need_parse:
                    rss_list.append(rss)

                elif items := _extract_rss_list_in_html_type_nd(rss.text):
                    for item in items:
                        rss_list.append(item)

                else:
                    rss_list.append(rss)

    return rss_list


def find_rss_in_html(base_url: str, site_text: str) -> list[ValidateRssUrlResult]:
    """html 텍스트 안에서 rss 주소 찾기"""
    rss_list = []
    temp_rss_set = set()
    text = __P_REMOVE_CAPTION.sub("", site_text)
    text = __P_FIND_RSS_LINK_TAG.sub("", text)
    text = __P_REMOVE_ETC_TAG.sub("", text)
    text = __P_REMOVE_MULTI_EMPTY.sub("", text)

    for m_rss_url in __P_FIND_RSS_URL_IN_SRC.findall(text):
        temp_rss_set.add(_normalize_url(base_url, m_rss_url))

    for m_rss_url in __P_FIND_RSS2_URL_IN_SRC.findall(text):
        temp_rss_set.add(_normalize_url(base_url, m_rss_url))

    for rss_url in temp_rss_set:
        if rss := _validate_rss_url(rss_url):
            if not rss.need_parse:
                rss_list.append(rss)

            elif items := _extract_rss_list_in_html_type_nd(rss.text):
                for item in items:
                    rss_list.append(item)

            else:
                rss_list.append(rss)

    return rss_list


def find_rss_in_all(base_url: str, site_text: str) -> list[ValidateRssUrlResult]:
    """html link와 텍스트 안에서 rss 주소 찾기"""
    rss_dict: dict[str, ValidateRssUrlResult] = {}
    for rss in find_rss_in_link_tag(base_url, site_text):
        if not rss.need_parse:
            rss_dict[rss.url] = rss

        elif rss.url not in rss_dict:
            rss_dict[rss.url] = rss

    for rss in find_rss_in_html(base_url, site_text):
        if not rss.need_parse:
            rss_dict[rss.url] = rss

        elif rss.url not in rss_dict:
            rss_dict[rss.url] = rss

    return list(rss_dict.values())
