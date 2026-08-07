import logging
import os
from typing import List

from mcp.types import TextContent, Tool
from pydantic import BaseModel, Field, ValidationError, field_validator

from mcp_kipris.kipris.abc import ToolHandler
from mcp_kipris.kipris.api.foreign.application_number_search import ForeignPatentApplicationNumberSearchAPI
from mcp_kipris.kipris.tools.code import country_dict, sort_field_dict

logger = logging.getLogger("mcp-kipris")
api_key = os.getenv("KIPRIS_API_KEY")

if not api_key:
    raise ValueError("KIPRIS_API_KEY environment variable required.")


class ForeignPatentApplicationNumberSearchArgs(BaseModel):
    application_number: str = Field(..., description="Application number, it must be filled")
    current_page: int = Field(1, description="Current page number")
    sort_field: str = Field("AD", description="Sort field")
    sort_state: bool = Field(True, description="Sort state")
    collection_values: str = Field(
        "US",
        description="Collection values, must be one of: US(미국), EP(유럽), WO(PCT), JP(일본), PJ(일본영문초록), CP(중국), CN(중국특허영문초록), TW(대만영문초록), RU(러시아), CO(콜롬비아), SE(스웨덴), ES(스페인), IL(이스라엘)",
    )

    @field_validator("collection_values")
    @classmethod
    def validate_collection_values(cls, v: str) -> str:
        if v not in country_dict:
            raise ValueError(f"collection_values must be one of: {', '.join(country_dict.keys())}")
        return v

    @field_validator("sort_field")
    @classmethod
    def validate_sort_field(cls, v: str) -> str:
        if v not in sort_field_dict:
            raise ValueError(f"sort_field must be one of: {', '.join(sort_field_dict.keys())}")
        return v


class ForeignPatentApplicationNumberSearchTool(ToolHandler):
    #: this KIPRIS legacy service (openapi/rest/ForeignPatentAdvencedSearchService)
    #: has no response.count block and no page-size parameter -- confirmed
    #: live, it always returns a fixed batch per current_page -- so there is
    #: no genuine total-match figure to report, only which page is shown.
    _NO_TOTAL_COUNT_NOTE = "※ 이 KIPRIS 엔드포인트는 totalCount를 제공하지 않아 전체 검색결과 수는 확인할 수 없습니다."

    def __init__(self):
        super().__init__("foreign_patent_application_number_search")
        self.api = ForeignPatentApplicationNumberSearchAPI(api_key=api_key)
        self.description = "foreign patent search by application number, this tool is for foreign(US, EP, WO, JP, PJ, CP, CN, TW, RU, CO, SE, ES, IL) patent search"
        self.args_schema = ForeignPatentApplicationNumberSearchArgs

    def get_tool_description(self) -> Tool:
        return Tool(
            name=self.name,
            description=self.description,
            inputSchema={
                "type": "object",
                "properties": {
                    "application_number": {"type": "string", "description": "출원번호"},
                    "current_page": {"type": "integer", "description": "현재 페이지 번호 (기본값: 1)"},
                    "sort_field": {
                        "type": "string",
                        "description": "정렬 기준 필드",
                        "enum": list(sort_field_dict.keys()),
                        "default": "AD",
                    },
                    "sort_state": {"type": "boolean", "description": "정렬 상태 (기본값: true)"},
                    "collection_values": {
                        "type": "string",
                        "description": "검색 대상 국가",
                        "enum": list(country_dict.keys()),
                        "default": "US",
                    },
                },
                "required": ["application_number"],
            },
        )

    def run_tool(self, args: dict) -> List[TextContent]:
        try:
            validated_args = ForeignPatentApplicationNumberSearchArgs(**args)
            logger.info(f"Searching for application number: {validated_args.application_number}")

            response = self.api.sync_search(
                application_number=validated_args.application_number,
                current_page=validated_args.current_page,
                sort_field=validated_args.sort_field,
                sort_state=validated_args.sort_state,
                collection_values=validated_args.collection_values,
            )

            if response.empty:
                return [TextContent(type="text", text=f"there is no result\n{self._NO_TOTAL_COUNT_NOTE}")]

            summary_df = response[["applicationNo", "applicationDate", "inventionName", "applicant"]].copy()
            header = (
                f"표시: {len(summary_df)}건 (페이지: {validated_args.current_page})\n{self._NO_TOTAL_COUNT_NOTE}\n\n"
            )
            return [TextContent(type="text", text=header + self.format_table(summary_df))]

        except ValidationError as e:
            logger.error(f"Validation error: {str(e)}")
            return [TextContent(type="text", text=f"입력값 검증 오류: {str(e)}")]
        except Exception as e:
            logger.error(f"Error occurred: {str(e)}")
            return [TextContent(type="text", text=f"오류가 발생했습니다: {str(e)}")]

    async def run_tool_async(self, args: dict) -> List[TextContent]:
        try:
            validated_args = ForeignPatentApplicationNumberSearchArgs(**args)
            logger.info(f"Searching for application number: {validated_args.application_number}")

            response = await self.api.async_search(
                application_number=validated_args.application_number,
                current_page=validated_args.current_page,
                sort_field=validated_args.sort_field,
                sort_state=validated_args.sort_state,
                collection_values=validated_args.collection_values,
            )

            if response.empty:
                return [TextContent(type="text", text=f"there is no result\n{self._NO_TOTAL_COUNT_NOTE}")]

            summary_df = response[["applicationNo", "applicationDate", "inventionName", "applicant"]].copy()
            header = (
                f"표시: {len(summary_df)}건 (페이지: {validated_args.current_page})\n{self._NO_TOTAL_COUNT_NOTE}\n\n"
            )
            return [TextContent(type="text", text=header + self.format_table(summary_df))]

        except ValidationError as e:
            logger.error(f"Validation error: {str(e)}")
            return [TextContent(type="text", text=f"입력값 검증 오류: {str(e)}")]
        except Exception as e:
            logger.error(f"Error occurred: {str(e)}")
            return [TextContent(type="text", text=f"오류가 발생했습니다: {str(e)}")]
