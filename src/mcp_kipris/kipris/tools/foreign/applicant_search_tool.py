import logging
import os
import typing as t
from collections.abc import Sequence

import pandas as pd

# from icecream import ic
from mcp.types import EmbeddedResource, ImageContent, TextContent, Tool
from pydantic import BaseModel, Field, ValidationError, field_validator

from mcp_kipris.kipris.abc import ToolHandler
from mcp_kipris.kipris.api.foreign.applicant_search import ForeignPatentApplicantSearchAPI
from mcp_kipris.kipris.tools.code import country_dict, sort_field_dict

logger = logging.getLogger("mcp-kipris")
api_key = os.getenv("KIPRIS_API_KEY")

if not api_key:
    raise ValueError("KIPRIS_API_KEY environment variable required.")


class ForeignPatentApplicantSearchArgs(BaseModel):
    applicant: str = Field(..., description="Applicant name, it must be filled")
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


class ForeignPatentApplicantSearchTool(ToolHandler):
    #: this KIPRIS legacy service (openapi/rest/ForeignPatentAdvencedSearchService)
    #: has no response.count block and no page-size parameter -- confirmed
    #: live, it always returns a fixed batch per current_page -- so there is
    #: no genuine total-match figure to report, only which page is shown.
    _NO_TOTAL_COUNT_NOTE = "※ 이 KIPRIS 엔드포인트는 totalCount를 제공하지 않아 전체 검색결과 수는 확인할 수 없습니다."

    def __init__(self):
        super().__init__("foreign_patent_applicant_search")
        self.api = ForeignPatentApplicantSearchAPI(api_key=api_key)
        self.description = "foreign patent search by applicant, this tool is for foreign(US, EP, WO, JP, PJ, CP, CN, TW, RU, CO, SE, ES, IL) patent search"
        self.args_schema = ForeignPatentApplicantSearchArgs

    def get_tool_description(self) -> Tool:
        return Tool(
            name=self.name,
            description=self.description,
            inputSchema={
                "type": "object",
                "properties": {
                    "applicant": {"type": "string", "description": "출원인명"},
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
                "required": ["applicant"],
            },
        )

    def run_tool(self, args: dict) -> Sequence[TextContent | ImageContent | EmbeddedResource]:
        try:
            validated_args = ForeignPatentApplicantSearchArgs(**args)
            logger.info(f"applicant: {validated_args.applicant}")

            response = self.api.sync_search(
                applicant=validated_args.applicant,
                current_page=validated_args.current_page,
                sort_field=validated_args.sort_field,
                sort_state=validated_args.sort_state,
                collection_values=validated_args.collection_values,
            )
            # ic(response)
            if response.empty:
                return [TextContent(type="text", text=f"검색 결과가 없습니다.\n{self._NO_TOTAL_COUNT_NOTE}")]

            header = f"표시: {len(response)}건 (페이지: {validated_args.current_page})\n{self._NO_TOTAL_COUNT_NOTE}\n\n"
            return [TextContent(type="text", text=header + self.format_table(response))]
        except ValidationError as e:
            logger.error(f"Validation error: {str(e)}")
            messages = []
            for error in e.errors():
                field = error["loc"][0]
                if field == "applicant":
                    messages.append("출원인명(applicant) 정보가 필요합니다.")
                elif field == "collection_values":
                    messages.append(
                        f"국가 코드(collection_values)는 다음 중 하나여야 합니다: {', '.join(country_dict.keys())}"
                    )
                elif field == "sort_field":
                    messages.append(
                        f"정렬 기준(sort_field)은 다음 중 하나여야 합니다: {', '.join(sort_field_dict.keys())}"
                    )
            text = " ".join(messages) if messages else str(e)
            return [TextContent(type="text", text=f"입력값 검증 오류: {text}")]
        except Exception as e:
            logger.error(f"Error occurred: {str(e)}")
            return [TextContent(type="text", text=f"오류가 발생했습니다: {str(e)}")]

    async def run_tool_async(self, args: dict) -> Sequence[TextContent | ImageContent | EmbeddedResource]:
        try:
            validated_args = ForeignPatentApplicantSearchArgs(**args)
            logger.info(f"applicant: {validated_args.applicant}")

            response = await self.api.async_search(
                applicant=validated_args.applicant,
                current_page=validated_args.current_page,
                sort_field=validated_args.sort_field,
                sort_state=validated_args.sort_state,
                collection_values=validated_args.collection_values,
            )

            if response.empty:
                return [TextContent(type="text", text=f"검색 결과가 없습니다.\n{self._NO_TOTAL_COUNT_NOTE}")]

            header = f"표시: {len(response)}건 (페이지: {validated_args.current_page})\n{self._NO_TOTAL_COUNT_NOTE}\n\n"
            return [TextContent(type="text", text=header + self.format_table(response))]
        except ValidationError as e:
            logger.error(f"Validation error: {str(e)}")
            messages = []
            for error in e.errors():
                field = error["loc"][0]
                if field == "applicant":
                    messages.append("출원인명(applicant) 정보가 필요합니다.")
                elif field == "collection_values":
                    messages.append(
                        f"국가 코드(collection_values)는 다음 중 하나여야 합니다: {', '.join(country_dict.keys())}"
                    )
                elif field == "sort_field":
                    messages.append(
                        f"정렬 기준(sort_field)은 다음 중 하나여야 합니다: {', '.join(sort_field_dict.keys())}"
                    )
            text = " ".join(messages) if messages else str(e)
            return [TextContent(type="text", text=f"입력값 검증 오류: {text}")]
        except Exception as e:
            logger.error(f"Error occurred: {str(e)}")
            return [TextContent(type="text", text=f"오류가 발생했습니다: {str(e)}")]
