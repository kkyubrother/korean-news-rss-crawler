"""뉴스 종합 정보 사이트 크롤링 후 각 사이트 정보를 추출한다."""
import time
from tqdm import tqdm
from bs4 import BeautifulSoup
from urllib.parse import urlparse
from typing import Optional
from util.req import request_get
from util import auto_save_load
from util.parser import find_rss_in_all


URL = "http://www.mediamap.co.kr/?md=A01"


def _request_and_save_site_data(url: str) -> dict:
    if text := request_get(url):
        return {
            'ok': True,
            'text': text,
            'parsed': False,
        }
    return {
        'ok': False,
        'text': "",
        'parsed': True,
    }


def _get_news_detail_urls() -> list[str]:
    """mediamap의 상세 정보 url 수집"""
    soup = BeautifulSoup(request_get(URL), 'html.parser')
    news_detail_url_list = []

    # 자세한 정보가 있는 url 획득
    for item in soup.select('a[style*="margin-right:13px;"]'):
        news_detail_url_list.append(item['href'])

    return news_detail_url_list


def _get_default_info(detail_url: str) -> dict:
    """mediamap의 상세 정보 페이지를 크롤링하고 기본 정보를 저장한다."""
    soup = BeautifulSoup(request_get(detail_url), "html.parser")
    parsed_url = urlparse(soup.select("table")[5].select("td")[9].select_one("a")['href'])
    news_homepage_url = f"{parsed_url.scheme}://{parsed_url.netloc}"

    # 자세한 정보를 획득 후 dict 형식으로 저장
    name = soup.select("table")[5].select("td")[2].get_text(strip=True)

    return {
        "name": name,
        "url": news_homepage_url,
        "status": 'ready',
        "rss": [],
        "extra": {
            'mediamap': {
                "type": soup.select("table")[5].select("td")[4].get_text(strip=True),
                "company_name": soup.select("table")[5].select("td")[7].get_text(strip=True),
                "category": soup.select("table")[5].select("td")[11].get_text(strip=True),
                "call": soup.select("table")[5].select("td")[14].get_text(strip=True),
                "address": soup.select("table")[5].select("td")[16].get_text(strip=True),
                "area": soup.select("table")[5].select("td")[18].get_text(strip=True),
                "description": soup.select("table")[5].select("td")[21].get_text(separator="\n", strip=True),
                "detail_contact": soup.select("table")[5].select("td")[24].get_text(strip=True),
            },
        },
        "from": detail_url,
        "site": {}
    }


def crawling_target_mediamap(delay: int = 5, auto_save_filename: Optional[str] = None):
    news_data = auto_save_load.auto_load(auto_save_filename)

    reversed_news_data = {n['from']: n for n in news_data.values()}

    pbar = tqdm(_get_news_detail_urls())
    # 자세한 정보를 획득
    for detail_url in pbar:
        is_preload = False
        if detail_url in reversed_news_data:
            data = reversed_news_data[detail_url]
            news_homepage_url = data['url']
            is_preload = True
        else:
            data = _get_default_info(detail_url)
            news_homepage_url = data['url']
            news_data[news_homepage_url] = data
            is_preload = False

        pbar.set_description(news_homepage_url)

        if data['status'] == 'unable':
            continue

        elif data['status'] == 'parsed':
            continue

        # 각 사이트에 부하를 주지 않기 위해 대상 사이트를 크롤링하며 쉬는 시간을 부여
        site_obj = data['site']
        site_obj['/'] = _request_and_save_site_data(f"{news_homepage_url}/")
        time.sleep(1)
        site_obj['/robots.txt'] = _request_and_save_site_data(f"{news_homepage_url}/robots.txt")
        site_obj['/sitemap.xml'] = _request_and_save_site_data(f"{news_homepage_url}/sitemap.xml")

        if not site_obj['/']['ok']:
            site_obj['/']['text'] = ""
            site_obj['/robots.txt']['text'] = ""
            site_obj['/sitemap.xml']['text'] = ""
            data['status'] = 'unable'

        else:
            for rss_item in find_rss_in_all(news_homepage_url, site_obj['/']['text']):
                data['rss'].append(rss_item.to_dict())

            site_obj['/']['parsed'] = True
            site_obj['/']['text'] = ""
            data['status'] = 'parsed'

        data['site'] = site_obj
        auto_save_load.auto_save(news_data, auto_save_filename)

        if not is_preload:
            time.sleep(delay)

        break

    return news_data


if __name__ == "__main__":
    import pprint
    pprint.pp(crawling_target_mediamap(5, "mediamap.json"), indent=2)
