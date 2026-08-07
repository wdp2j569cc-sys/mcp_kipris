import logging
import os
import typing as t
from urllib.parse import urlencode

import pandas as pd
from dotenv import load_dotenv
from stringcase import camelcase

from mcp_kipris.kipris.api.utils import get_nested_key_value, get_response, get_response_async
from mcp_kipris.kipris.errors import KiprisApiError, KiprisErrorCode
from mcp_kipris.kipris.logging_utils import redact_sensitive_data
from mcp_kipris.kipris.rate_limiter import wait_if_rate_limited, wait_if_rate_limited_sync

# KIPRIS result codes that mean "the request succeeded but matched
# nothing" rather than an actual failure — parse_response treats only
# these as an empty (not exceptional) result.
_NO_RESULT_CODES = {"20"}

logging.basicConfig(
    format="%(asctime)s - %(levelname)s - %(message)s",
    level=logging.INFO,  # INFO 레벨을 출력
    handlers=[logging.StreamHandler()],
)
logger = logging.getLogger("mcp-kipris")
load_dotenv(override=True)


# ic.disable()
class ABSKiprisAPI:
    def __init__(self, **kwargs):
        self.HEADER_KEY_STRING = "response.body.items.item"
        self.KEY_STRING = ""
        if "api_key" in kwargs:
            self.api_key = kwargs["api_key"]
        else:
            if os.getenv("KIPRIS_API_KEY"):
                self.api_key = os.getenv("KIPRIS_API_KEY")
            else:
                raise ValueError(
                    "KIPRIS_API_KEY is not set you must set KIPRIS_API_KEY in .env file or pass api_key to constructor "
                )

    def sync_call(self, api_url: str, api_key_field="accessKey", **params) -> t.Dict:
        """
        KIPRIS API 공통 호출 서비스

        Args:
            api_url (str): 서브 URL
            api_key_field (str): 키 필드 이름
            params (dict): 파라미터

        Returns:
            t.List[dict]: 응답 데이터
        """

        try:
            wait_if_rate_limited_sync()
            params_dict = {camelcase(k): v for k, v in params.items() if v is not None and v != ""}
            params_dict[api_key_field] = self.api_key
            full_url = f"{api_url}?{urlencode(params_dict)}"
            logger.info(f"KIPRIS 요청 URL: {redact_sensitive_data(full_url)}")
            return get_response(full_url)
        except Exception as e:
            logger.error(f"KIPRIS 요청 실패: {e}")
            raise

    async def async_call(self, api_url: str, api_key_field="accessKey", **params) -> t.Dict:
        """
        KIPRIS API 비동기 호출 서비스

        Args:
            api_url (str): 서브 URL
            api_key_field (str): 키 필드 이름
            params (dict): 파라미터

        Returns:
            dict: 응답 데이터
        """
        try:
            await wait_if_rate_limited()
            params_dict = {camelcase(k): v for k, v in params.items() if v is not None and v != ""}
            params_dict[api_key_field] = self.api_key
            full_url = f"{api_url}?{urlencode(params_dict)}"
            logger.info(f"[async] KIPRIS 요청 URL: {redact_sensitive_data(full_url)}")
            return await get_response_async(full_url)
        except Exception as e:
            logger.error(f"[async] KIPRIS 요청 실패: {e}")
            raise

    def check_api_error(self, response: dict) -> t.Optional[str]:
        """Check KIPRIS API response for error codes.

        Returns:
            Error message string if error found, None otherwise.
        """
        if response is None:
            return "Empty response from KIPRIS API"
        result_code = get_nested_key_value(response, "response.header.resultCode")
        if result_code and result_code != "00":
            result_msg = get_nested_key_value(response, "response.header.resultMsg") or "Unknown error"
            error_map = {
                "00": "NORMAL SERVICE",
                "10": "INVALID_REQUEST_PARAMETER_ERROR",
                "20": "NO_RESULTS",
                "30": "ACCESS_KEY_NOT_REGISTERED",
                "31": "DEADLINE_EXPIRED",
            }
            code_desc = error_map.get(str(result_code), f"CODE_{result_code}")
            logger.warning(f"KIPRIS API 에러: [{result_code}] {result_msg} ({code_desc})")
            return f"[{result_code}] {result_msg}"
        return None

    def parse_response(self, response: dict) -> pd.DataFrame:
        # Check for API-level errors first. Only a genuine "no matching
        # results" response is treated as empty; anything else (bad
        # parameters, an unauthorized/expired key for this service, ...)
        # is raised so the caller sees the real reason instead of a
        # search that looks like it just found nothing.
        api_error = self.check_api_error(response)
        if api_error:
            result_code = str(get_nested_key_value(response, "response.header.resultCode")) if response else None
            if result_code in _NO_RESULT_CODES:
                logger.info(f"KIPRIS: 매칭 결과 없음 ({api_error})")
                return self._with_total_count(pd.DataFrame(), 0)
            raise KiprisApiError(
                code=KiprisErrorCode.API_ERROR,
                message=f"KIPRIS API 오류: {api_error}",
                details={"result_code": result_code},
            )

        # totalCount lives at response.count (a sibling of header/body, not
        # nested under body) and outside KEY_STRING, so it must be read from
        # the untouched response before we drill down. Confirmed against the
        # live API: response.body has no "count" key at all.
        raw_total_count = get_nested_key_value(response, "response.count.totalCount")

        res_dict = get_nested_key_value(response, self.KEY_STRING)
        if res_dict is None:
            logger.info("patents is None")
            message = get_nested_key_value(response, self.HEADER_KEY_STRING)
            if message:
                logger.warning(f"KIPRIS API 응답 메시지: {message}")
            return self._with_total_count(pd.DataFrame(), raw_total_count, default=0)
        if isinstance(res_dict, t.Dict):
            res_dict = [res_dict]
        df = pd.DataFrame(res_dict)
        return self._with_total_count(df, raw_total_count, default=len(df))

    @staticmethod
    def _with_total_count(df: pd.DataFrame, raw_total_count, default: int = 0) -> pd.DataFrame:
        """Attach the KIPRIS-reported total match count so callers can report it.

        Falls back to `default` (usually the number of rows actually
        returned) when this KIPRIS service doesn't include a count block at
        all, so `df.attrs["total_count"]` is always a usable int rather than
        sometimes missing.
        """
        try:
            df.attrs["total_count"] = int(raw_total_count) if raw_total_count is not None else default
        except (TypeError, ValueError):
            df.attrs["total_count"] = default
        return df
