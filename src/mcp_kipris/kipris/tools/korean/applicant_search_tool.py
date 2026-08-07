import logging
import os
from collections.abc import Sequence

from mcp.types import TextContent, Tool
from pydantic import BaseModel, Field, ValidationError

from mcp_kipris.kipris.abc import ToolHandler
from mcp_kipris.kipris.api.korean.applicant_search_api import PatentApplicantSearchAPI

logger = logging.getLogger("mcp-kipris")
api_key = os.getenv("KIPRIS_API_KEY")

if not api_key:
    raise ValueError("KIPRIS_API_KEY environment variable required.")


class PatentApplicantSearchArgs(BaseModel):
    applicant: str = Field(..., description="Applicant name is required")
    docs_start: int = Field(1, description="Start index for documents, default is 1")
    docs_count: int = Field(10, description="Number of documents to return, default is 10, range is 1-30")
    patent: bool = Field(True, description="Include patents, default is True")
    utility: bool = Field(True, description="Include utility models, default is True")
    lastvalue: str = Field(
        "", description="Patent registration status; leave empty for all, (A, C, F, G, I, J, R or empty)"
    )
    sort_spec: str = Field(
        "AD",
        description="Field to sort by; default is 'AD'(PD-공고일자, AD-출원일자, GD-등록일자, OPD-공개일자, FD-국제출원일자, FOD-국제공개일자, RD-우선권주장일자)",
    )
    desc_sort: bool = Field(
        True,
        description="Sort in descending order; default is True, when True, sort by descending order.it mean latest date first.",
    )


class PatentApplicantSearchTool(ToolHandler):
    def __init__(self):
        super().__init__("patent_applicant_search")
        self.api = PatentApplicantSearchAPI(api_key=api_key)
        self.description = "patent search by applicant name, this tool is for korean patent search"

    def get_tool_description(self) -> Tool:
        logger.info(f"get_tool_description: {self.name}")
        tool = Tool(
            name=self.name,
            description=self.description,
            inputSchema={
                "type": "object",
                "properties": {
                    "applicant": {"type": "string", "description": "출원인 이름"},
                    "docs_start": {"type": "integer", "description": "검색 시작 위치 (기본값: 1)"},
                    "docs_count": {"type": "integer", "description": "검색 결과 수 (기본값: 10, 범위: 1-30)"},
                    "patent": {"type": "boolean", "description": "특허 포함 여부 (기본값: true)"},
                    "utility": {"type": "boolean", "description": "실용신안 포함 여부 (기본값: true)"},
                    "lastvalue": {
                        "type": "string",
                        "description": (
                            "특허 등록 상태 (A:공개, C:정정공개, F:공고, G:정정공고, I:무효공고, J:취소공고, R:재공고, 공백:전체). "
                            "공백(전체)으로 조회하면 이미 '등록' 상태로 넘어간 건은 공개일(OpeningDate)이 "
                            "비어서 나오는 경우가 많으니, 공개일 기준 집계가 목적이면 A로 필터링하세요."
                        ),
                        "enum": ["A", "C", "F", "G", "I", "J", "R", ""],
                    },
                    "sort_spec": {
                        "type": "string",
                        "description": "정렬 기준 필드",
                        "enum": ["PD", "AD", "GD", "OPD", "FD", "FOD", "RD"],
                        "default": "AD",
                    },
                    "desc_sort": {"type": "boolean", "description": "내림차순 정렬 여부 (기본값: true)"},
                },
                "required": ["applicant"],
            },
            metadata={
                "usage_hint": (
                    "출원인(특허를 출원한 사람 또는 회사)의 이름으로 한국 특허를 검색합니다. 권리자(특허권자)와는 다릅니다. "
                    "특정 월의 공개 건수 등 공개일 기준 집계가 필요하면, 건별 상세조회 없이도 lastvalue=A로 "
                    "필터링해서 목록 결과의 OpeningDate/OpeningNumber만으로 집계할 수 있습니다."
                ),
                "example_user_queries": [
                    "삼성전자가 출원한 특허 보여줘",
                    "LG화학이 최근 출원한 특허 5건 검색해줘",
                    "네이버가 출원한 특허 목록 알려줘",
                    "한화에어로스페이스가 2026년 7월에 공개한 특허가 몇 건이야?",
                ],
                "preferred_response_style": (
                    "출원인, 출원일자, 발명의 명칭, 출원번호를 포함하여 최근 순으로 표 형태로 정리해주세요. "
                    "간결하고 이해하기 쉽게 응답해 주세요."
                ),
            },
        )
        logger.info(f"get_tool_description: {tool}")
        return tool

    #: applicantNameSearchInfo (the openapi/rest legacy service family) has
    #: no response.count block -- confirmed live, unlike the kipo-api/kipi
    #: getAdvancedSearch family used by ipc/abstract/agent_search -- so
    #: there is no genuine total-match figure to report here, only how many
    #: rows this page returned.
    _NO_TOTAL_COUNT_NOTE = "※ 이 KIPRIS 엔드포인트는 totalCount를 제공하지 않아 전체 검색결과 수는 확인할 수 없습니다."

    #: this legacy schema's own field names for 공개일/공개번호 -- confirmed
    #: live -- are "Opening*", not the "open*" camelCase used by ipc/
    #: abstract/agent_search's different (getAdvancedSearch) endpoint.
    _SUMMARY_COLUMNS = [
        "ApplicationNumber",
        "ApplicationDate",
        "InventionName",
        "Applicant",
        "OpeningNumber",
        "OpeningDate",
    ]

    def _format_result(self, response, docs_count: int) -> Sequence[TextContent]:
        if response.empty:
            return [TextContent(type="text", text=f"there is no result\n{self._NO_TOTAL_COUNT_NOTE}")]

        summary_df = self.select_columns(response, self._SUMMARY_COLUMNS)
        header = f"표시: {len(summary_df)}건 (요청: {docs_count}건)\n{self._NO_TOTAL_COUNT_NOTE}\n\n"
        return [TextContent(type="text", text=header + self.format_table(summary_df))]

    def run_tool(self, args: dict) -> Sequence[TextContent]:
        try:
            validated_args = PatentApplicantSearchArgs(**args)
            logger.info(f"Searching for applicant: {validated_args.applicant}")

            response = self.api.sync_search(
                applicant=validated_args.applicant,
                docs_count=validated_args.docs_count,
                docs_start=validated_args.docs_start,
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

    async def run_tool_async(self, args: dict) -> Sequence[TextContent]:
        try:
            validated_args = PatentApplicantSearchArgs(**args)
            logger.info(f"Searching for applicant: {validated_args.applicant}")

            response = await self.api.async_search(
                applicant=validated_args.applicant,
                docs_count=validated_args.docs_count,
                docs_start=validated_args.docs_start,
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
