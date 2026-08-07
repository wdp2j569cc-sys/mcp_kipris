import asyncio
import logging
import os
import typing as t
import warnings
from collections.abc import Sequence

import pandas as pd
from mcp.types import EmbeddedResource, ImageContent, TextContent, Tool
from pydantic import BaseModel, Field, ValidationError

from mcp_kipris.kipris.abc import ToolHandler
from mcp_kipris.kipris.api.korean.patent_search_api import PatentSearchAPI

logger = logging.getLogger("mcp-kipris")

api_key = os.getenv("KIPRIS_API_KEY")

if not api_key:
    raise ValueError("KIPRIS_API_KEY environment variable required.")

# Raw KIPRIS field names (from the getAdvancedSearch response) mapped to the
# same PascalCase column names patent_application_number_search returns, so
# both tools' tables look the same regardless of which KIPRIS service
# actually answered the query.
_OUTPUT_COLUMN_MAP = {
    "applicationNumber": "ApplicationNumber",
    "applicationDate": "ApplicationDate",
    "inventionTitle": "InventionName",
    "applicantName": "Applicant",
}
_OUTPUT_COLUMNS = list(_OUTPUT_COLUMN_MAP.values())


class PatentAdvancedSearchArgs(BaseModel):
    application_number: str = Field(..., description="Application number, it must be filled")


def _format_response(response: pd.DataFrame) -> Sequence[TextContent]:
    if response.empty:
        return [TextContent(type="text", text="검색 결과가 없습니다.")]

    summary_df = response.rename(columns=_OUTPUT_COLUMN_MAP)[_OUTPUT_COLUMNS].copy()
    return [TextContent(type="text", text=ToolHandler.format_table(summary_df))]


class PatentAdvancedSearchTool(ToolHandler):
    """Wraps KIPRIS's getAdvancedSearch service, looked up here by application
    number. This is a different KIPRIS endpoint from
    patent_application_number_search (applicationNumberSearchInfo) — the two
    are not interchangeable at the API level, but their output tables use the
    same column names for consistency.
    """

    def __init__(self, tool_name: str = "patent_advanced_search"):
        super().__init__(tool_name)
        self.api = PatentSearchAPI(api_key=api_key)
        self.description = (
            "patent search by application number via KIPRIS's advanced search service, "
            "this tool is for korean patent search"
        )

    def get_tool_description(self) -> Tool:
        return Tool(
            name=self.name,
            description=self.description,
            inputSchema={
                "type": "object",
                "properties": {"application_number": {"type": "string", "description": "출원번호"}},
                "required": ["application_number"],
            },
            metadata={
                "usage_hint": "출원번호로 한국 특허를 검색하고 특허에 대한 기본적인 정보를 제공합니다.",
                "example_user_queries": ["1020230045678 특허의 기본 정보를 알고 싶어."],
                "preferred_response_style": (
                    "출원번호, 출원일자, 발명의 명칭, 출원인을 포함하여 최근 순으로 표 형태로 정리해주세요. "
                    "간결하고 이해하기 쉽게 응답해 주세요."
                ),
            },
        )

    def run_tool(self, args: dict) -> Sequence[TextContent | ImageContent | EmbeddedResource]:
        try:
            validated_args = PatentAdvancedSearchArgs(**args)
            logger.info(f"application_number: {validated_args.application_number}")

            response = self.api.sync_search(word="", application_number=validated_args.application_number)
            return _format_response(response)

        except ValidationError as e:
            logger.error(f"Validation error: {str(e)}")
            return [TextContent(type="text", text=f"입력값 검증 오류: {str(e)}")]
        except Exception as e:
            logger.error(f"Error occurred: {str(e)}")
            return [TextContent(type="text", text=f"오류가 발생했습니다: {str(e)}")]

    async def run_tool_async(self, args: dict) -> Sequence[TextContent | ImageContent | EmbeddedResource]:
        """특허 검색 비동기 실행 메서드"""
        try:
            validated_args = PatentAdvancedSearchArgs(**args)
            logger.info(f"application_number: {validated_args.application_number}")

            response = await self.api.async_search(word="", application_number=validated_args.application_number)
            return _format_response(response)

        except ValidationError as e:
            logger.error(f"Validation error: {str(e)}")
            return [TextContent(type="text", text=f"입력값 검증 오류: {str(e)}")]
        except Exception as e:
            logger.error(f"Error occurred: {str(e)}")
            return [TextContent(type="text", text=f"오류가 발생했습니다: {str(e)}")]


class PatentSearchTool(PatentAdvancedSearchTool):
    """Deprecated alias for PatentAdvancedSearchTool under its old name
    ('patent_search'). Kept registered for backward compatibility; scheduled
    for removal in a future major version. New integrations should use
    patent_advanced_search instead.
    """

    def __init__(self):
        super().__init__(tool_name="patent_search")
        warnings.warn(
            "PatentSearchTool ('patent_search') is deprecated and will be removed in a future major "
            "version; use PatentAdvancedSearchTool ('patent_advanced_search') instead.",
            DeprecationWarning,
            stacklevel=2,
        )
        self.description = (
            "[DEPRECATED — renamed to patent_advanced_search; this alias will be removed in a "
            "future major version] " + self.description
        )

    def get_tool_description(self) -> Tool:
        tool = super().get_tool_description()
        metadata = dict(tool.metadata or {})
        metadata.update(
            {
                "deprecated": True,
                "replacement_tool": "patent_advanced_search",
                "removal_notice": "Scheduled for removal in a future major version; kept for backward compatibility.",
            }
        )
        return tool.model_copy(update={"metadata": metadata})
