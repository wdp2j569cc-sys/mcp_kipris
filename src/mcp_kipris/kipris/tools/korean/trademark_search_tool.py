import logging
import os
from typing import List

from mcp.types import TextContent, Tool
from pydantic import BaseModel, Field, ValidationError

from mcp_kipris.kipris.abc import ToolHandler
from mcp_kipris.kipris.api.korean.trademark_search_api import TrademarkSearchAPI

logger = logging.getLogger("mcp-kipris")

api_key = os.getenv("KIPRIS_API_KEY")

if not api_key:
    raise ValueError("KIPRIS_API_KEY environment variable required.")


class TrademarkSearchArgs(BaseModel):
    word: str = Field(..., description="상표 검색 키워드")
    docs_start: int = Field(1, description="검색 시작 위치 (기본값: 1)")
    docs_count: int = Field(10, description="검색 결과 수 (기본값: 10, 범위: 1-30)")
    desc_sort: bool = Field(True, description="내림차순 정렬 여부 (기본값: true)")
    sort_spec: str = Field("AD", description="정렬 기준 필드 (PD-공고일자, AD-출원일자, GD-등록일자, OPD-공개일자)")


class TrademarkSearchTool(ToolHandler):
    def __init__(self):
        super().__init__("trademark_search")
        self.api = TrademarkSearchAPI(api_key=api_key)
        self.description = "trademark search by keyword, this tool is for korean trademark search"
        self.args_schema = TrademarkSearchArgs

    def get_tool_description(self) -> Tool:
        return Tool(
            name=self.name,
            description=self.description,
            inputSchema={
                "type": "object",
                "properties": {
                    "word": {"type": "string", "description": "상표 검색 키워드"},
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
                "usage_hint": "키워드로 한국 상표를 검색하고 상표에 대한 정보를 제공합니다.",
                "example_user_queries": ["'삼성' 관련 상표를 검색해줘"],
                "preferred_response_style": (
                    "상표명, 출원일자, 상표 상태, 출원인을 포함하여 최근 순으로 표 형태로 정리해주세요. "
                    "간결하고 이해하기 쉽게 응답해 주세요."
                ),
            },
        )

    @staticmethod
    def _page_no(docs_start: int, docs_count: int) -> int:
        # TrademarkSearchAPI paginates by page number, not by record offset,
        # so docs_start (an offset, 1 = first record) only maps onto page_no
        # when it lands on a page boundary for the requested docs_count.
        return ((docs_start - 1) // docs_count) + 1 if docs_count else 1

    def _format_result(self, response, docs_count: int) -> List[TextContent]:
        total_count = response.attrs.get("total_count", len(response))
        if response.empty:
            return [TextContent(type="text", text=f"there is no result (총 검색결과: {total_count}건)")]

        # 상표 검색 결과의 컬럼이 특허와 다를 수 있으므로, 일반적인 컬럼만 선택
        available_columns = response.columns.tolist()
        summary_columns = []

        # 일반적인 상표 정보 컬럼들
        for col in ["ApplicationNumber", "ApplicationDate", "TrademarkName", "Applicant"]:
            if col in available_columns:
                summary_columns.append(col)

        # 만약 위 컬럼들이 없다면, 처음 4개 컬럼을 선택
        if not summary_columns:
            summary_columns = available_columns[:4]

        summary_df = response[summary_columns].copy()
        header = f"총 검색결과: {total_count}건 (표시: {len(summary_df)}건, 요청: {docs_count}건)\n\n"
        return [TextContent(type="text", text=header + self.format_table(summary_df))]

    def run_tool(self, args: dict) -> List[TextContent]:
        try:
            validated_args = TrademarkSearchArgs(**args)
            logger.info(f"Searching for trademark: {validated_args.word}")

            # NOTE: this project's KIPRIS key returns result code 31
            # (DEADLINE_EXPIRED) for every trademarkInfoSearchService query
            # (see README / issue #9), so num_of_rows/page_no being honored
            # here is unverified against a live 00 response.
            response = self.api.sync_search(
                word=validated_args.word,
                num_of_rows=validated_args.docs_count,
                page_no=self._page_no(validated_args.docs_start, validated_args.docs_count),
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
            validated_args = TrademarkSearchArgs(**args)
            logger.info(f"Searching for trademark: {validated_args.word}")

            response = await self.api.async_search(
                word=validated_args.word,
                num_of_rows=validated_args.docs_count,
                page_no=self._page_no(validated_args.docs_start, validated_args.docs_count),
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
