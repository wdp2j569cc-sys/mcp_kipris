import asyncio
import logging
import os
import typing as t
from collections.abc import Sequence
from typing import List

from mcp.types import EmbeddedResource, ImageContent, TextContent, Tool
from pydantic import BaseModel, Field, ValidationError

from mcp_kipris.kipris.abc import ToolHandler
from mcp_kipris.kipris.api.korean.free_search_api import PatentFreeSearchAPI

logger = logging.getLogger("mcp-kipris")

api_key = os.getenv("KIPRIS_API_KEY")

if not api_key:
    raise ValueError("KIPRIS_API_KEY environment variable required.")


class PatentFreeSearchArgs(BaseModel):
    word: str = Field(..., description="Search word, it must be filled")
    patent: bool = Field(True, description="Include patent search")
    utility: bool = Field(True, description="Include utility model search")
    lastvalue: str = Field("", description="Last value for pagination")
    docs_start: int = Field(1, description="Start index of documents")
    docs_count: int = Field(10, description="Number of documents to return")
    desc_sort: bool = Field(True, description="Sort in descending order")
    sort_spec: str = Field("AD", description="Sort specification")


class PatentFreeSearchTool(ToolHandler):
    def __init__(self):
        super().__init__("patent_free_search")
        self.api = PatentFreeSearchAPI(api_key=api_key)
        self.description = "patent search by keyword, this tool is for korean patent search"
        self.args_schema = PatentFreeSearchArgs

    def get_tool_description(self) -> Tool:
        return Tool(
            name=self.name,
            description=self.description,
            inputSchema={
                "type": "object",
                "properties": {
                    "word": {"type": "string", "description": "검색어"},
                    "patent": {"type": "boolean", "description": "특허 포함 여부 (기본값: true)"},
                    "utility": {"type": "boolean", "description": "실용신안 포함 여부 (기본값: true)"},
                    "lastvalue": {
                        "type": "string",
                        "description": "특허 등록 상태 (A:공개, C:정정공개, F:공고, G:정정공고, I:무효공고, J:취소공고, R:재공고, 공백:전체)",
                        "enum": ["A", "C", "F", "G", "I", "J", "R", ""],
                    },
                    "docs_start": {"type": "integer", "description": "검색 시작 위치 (기본값: 1)"},
                    "docs_count": {"type": "integer", "description": "검색 결과 수 (기본값: 10, 범위: 1-30)"},
                    "desc_sort": {"type": "boolean", "description": "내림차순 정렬 여부 (기본값: true)"},
                    "sort_spec": {
                        "type": "string",
                        "description": "정렬 기준 필드 (PD-공고일자, AD-출원일자, GD-등록일자, OPD-공개일자)",
                        "enum": ["PD", "AD", "GD", "OPD"],
                        "default": "AD",
                    },
                },
                "required": ["word"],
            },
            metadata={
                "usage_hint": "키워드로 한국 특허를 검색하고 특허에 대한 정보를 제공합니다.",
                "example_user_queries": ["'이차전지' 관련 특허를 검색해줘"],
                "preferred_response_style": (
                    "키워드, 출원일자, 발명의 명칭, 출원인을 포함하여 최근 순으로 표 형태로 정리해주세요. "
                    "간결하고 이해하기 쉽게 응답해 주세요."
                ),
            },
        )

    #: this tool hits a different KIPRIS endpoint (freeSearchInfo, not
    #: getAdvancedSearch) with its own PascalCase item schema
    #: (PatentUtilityInfo).
    _SUMMARY_COLUMNS = ["ApplicationNumber", "ApplicationDate", "InventionName", "Applicant"]

    @staticmethod
    def _page_no(docs_start: int, docs_count: int) -> int:
        # PatentFreeSearchAPI paginates by page number, not by record
        # offset, so docs_start (an offset, 1 = first record) only maps
        # onto page_no when it lands on a page boundary for docs_count.
        return ((docs_start - 1) // docs_count) + 1 if docs_count else 1

    def _format_result(self, response, docs_count: int) -> List[TextContent]:
        # Confirmed live: freeSearchInfo ignores numOfRows/pageNo entirely
        # and always returns a fixed batch (30 rows), with no response.count
        # block to report a real total from. So `returned_count` here is
        # just "how many rows this KIPRIS endpoint happened to send back",
        # not a true match total -- trim to docs_count client-side and say
        # so, rather than silently returning more rows than requested.
        returned_count = len(response)
        if response.empty:
            return [TextContent(type="text", text=f"there is no result (KIPRIS 반환: {returned_count}건)")]

        summary_df = self.select_columns(response.head(docs_count), self._SUMMARY_COLUMNS)
        header = (
            f"KIPRIS 반환: {returned_count}건 중 {len(summary_df)}건 표시 (요청: {docs_count}건)\n"
            "※ 이 검색 엔드포인트는 KIPRIS가 개수 제한(numOfRows)을 지원하지 않아, "
            "요청 건수와 무관하게 반환된 결과를 이 도구가 잘라서 보여줍니다.\n\n"
        )
        return [TextContent(type="text", text=header + self.format_table(summary_df))]

    def run_tool(self, args: dict) -> List[TextContent]:
        try:
            validated_args = PatentFreeSearchArgs(**args)
            logger.info(f"Searching for keyword: {validated_args.word}")

            response = self.api.sync_search(
                word=validated_args.word,
                num_of_rows=validated_args.docs_count,
                page_no=self._page_no(validated_args.docs_start, validated_args.docs_count),
                lastvalue=validated_args.lastvalue,
                patent=validated_args.patent,
                utility=validated_args.utility,
                sort_spec=validated_args.sort_spec,
                desc_sort=validated_args.desc_sort,
            )

            return self._format_result(response, validated_args.docs_count)

        except ValidationError as e:
            logger.error(f"Validation error: {str(e)}")
            return [TextContent(type="text", text=f"입력값 검증 오류: {str(e)}")]
        except Exception as e:
            logger.error(f"Error occurred: {str(e)}")
            return [TextContent(type="text", text=f"오류가 발생했습니다: {str(e)}")]

    async def run_tool_async(self, args: dict) -> List[TextContent]:
        try:
            validated_args = PatentFreeSearchArgs(**args)
            logger.info(f"Searching for keyword: {validated_args.word}")

            response = await self.api.async_search(
                word=validated_args.word,
                num_of_rows=validated_args.docs_count,
                page_no=self._page_no(validated_args.docs_start, validated_args.docs_count),
                lastvalue=validated_args.lastvalue,
                patent=validated_args.patent,
                utility=validated_args.utility,
                sort_spec=validated_args.sort_spec,
                desc_sort=validated_args.desc_sort,
            )

            return self._format_result(response, validated_args.docs_count)

        except ValidationError as e:
            logger.error(f"Validation error: {str(e)}")
            return [TextContent(type="text", text=f"입력값 검증 오류: {str(e)}")]
        except Exception as e:
            logger.error(f"Error occurred: {str(e)}")
            return [TextContent(type="text", text=f"오류가 발생했습니다: {str(e)}")]
