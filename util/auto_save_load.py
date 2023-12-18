"""자동 저장 관련 함수"""
import json
import logging
from typing import Optional

logger = logging.getLogger(__name__)


def auto_load(auto_save_filename: Optional[str] = None) -> dict:
    """해당 이름의 임시 파일을 불러온다."""
    if auto_save_filename:
        try:
            with open(auto_save_filename, encoding='utf-8') as f:
                news_data = json.load(f)
        except:
            logger.warning('자동 저장 파일이 올바르지 않습니다. 초기 상태로 작동합니다.')
            news_data = {}
    else:
        news_data = {}
    return news_data


def auto_save(news_data: dict, auto_save_filename: Optional[str] = None) -> bool:
    """해당 이름으로 자동 저장"""
    if auto_save_filename:
        try:
            with open(auto_save_filename, 'w', encoding='utf-8') as f:
                json.dump(news_data, f)
            return True
        except Exception as e:
            logger.warning(f'자동 저장에 실패하였습니다({e}).')
            return False
    return True
