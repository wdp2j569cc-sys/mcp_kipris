import logging
import os
import typing as t
from collections.abc import Sequence

import pandas as pd
from mcp.types import EmbeddedResource, ImageContent, TextContent, Tool
from pydantic import BaseModel, Field, ValidationError, field_validator

from mcp_kipris.kipris.abc import ToolHandler
from mcp_kipris.kipris.api.korean.patent_detail_search_api import PatentDetailSearchAPI

logger = logging.getLogger("mcp-kipris")
api_key = os.getenv("KIPRIS_API_KEY")

if not api_key:
    raise ValueError("KIPRIS_API_KEY environment variable required.")

# Maps a flat output field name to where it lives in the raw
# getBibliographyDetailInfoSearch response: item[array_key][item_key] is
# either a dict (one entry) or a list of dicts (repeated entries — IPC
# codes, applicants, claims, ...); source_field is read off each entry and
# joined with `sep` when there's more than one. Field names that exist in
# more than one group (name/engName/address/code/country show up under
# applicant, inventor, and agent alike) are prefixed to stay unambiguous.
# imagePathInfo is intentionally omitted — the KIPRIS docs don't make its
# nesting unambiguous and it's image file paths, not useful to an LLM.
_FIELD_REGISTRY: t.Dict[str, t.Tuple[str, str, str, str]] = {}


def _register(fields: t.Dict[str, str], array_key: str, item_key: str, sep: str = ", ") -> None:
    for output_name, source_field in fields.items():
        _FIELD_REGISTRY[output_name] = (array_key, item_key, source_field, sep)


_register(
    {
        f: f
        for f in [
            "applicationDate",
            "applicationNumber",
            "applicationFlag",
            "claimCount",
            "examinerName",
            "finalDisposal",
            "inventionTitle",
            "inventionTitleEng",
            "openDate",
            "openNumber",
            "originalApplicationDate",
            "originalApplicationKind",
            "originalApplicationNumber",
            "originalExaminationRequestDate",
            "originalExaminationRequestFlag",
            "publicationDate",
            "publicationNumber",
            "registerDate",
            "registerNumber",
            "registerStatus",
            "translationSubmitDate",
        ]
    },
    "biblioSummaryInfoArray",
    "biblioSummaryInfo",
)
_register({"ipcNumber": "ipcNumber", "ipcDate": "ipcDate"}, "ipcInfoArray", "ipcInfo")
_register({"familyApplicationNumber": "familyApplicationNumber"}, "familyInfoArray", "familyInfo")
_register({"astrtCont": "astrtCont"}, "abstractInfoArray", "abstractInfo", sep="\n\n")
_register(
    {
        "internationOpenDate": "internationOpenDate",
        "internationOpenNumber": "internationOpenNumber",
        "internationalApplicationDate": "internationalApplicationDate",
        "internationalApplicationNumber": "internationalApplicationNumber",
    },
    "internationalInfoArray",
    "internationalInfo",
)
_register({"claim": "claim"}, "claimInfoArray", "claimInfo", sep="\n\n")
_register(
    {
        "applicantName": "name",
        "applicantNameEng": "engName",
        "applicantAddress": "address",
        "applicantCode": "code",
        "applicantCountry": "country",
    },
    "applicantInfoArray",
    "applicantInfo",
)
_register(
    {
        "inventorName": "name",
        "inventorNameEng": "engName",
        "inventorAddress": "address",
        "inventorCode": "code",
        "inventorCountry": "country",
    },
    "inventorInfoArray",
    "inventorInfo",
)
_register(
    {
        "agentName": "name",
        "agentNameEng": "engName",
        "agentAddress": "address",
        "agentCode": "code",
        "agentCountry": "country",
    },
    "agentInfoArray",
    "agentInfo",
)
_register(
    {
        "priorityApplicationCountry": "priorityApplicationCountry",
        "priorityApplicationNumber": "priorityApplicationNumber",
        "priorityApplicationDate": "priorityApplicationDate",
    },
    "priorityInfoArray",
    "priorityInfo",
)
_register(
    {"designatedStateKind": "kind", "designatedStateCountry": "country"},
    "designatedStateInfoArray",
    "designatedStateInfo",
)
_register(
    {"priorArtDocumentsNumber": "documentsNumber", "examinerQuotationFlag": "examinerQuotationFlag"},
    "priorArtDocumentsInfoArray",
    "priorArtDocumentsInfo",
)
_register(
    {
        "legalStatusCommonCodeName": "commonCodeName",
        "legalStatusDocumentName": "documentName",
        "legalStatusDocumentNameEng": "documentEngName",
        "legalStatusReceiptDate": "receiptDate",
        "legalStatusReceiptNumber": "receiptNumber",
    },
    "legalStatusInfoArray",
    "legalStatusInfo",
)
_register(
    {
        f: f
        for f in [
            "rndDepartmentName",
            "rndDuration",
            "rndManagingInstituteName",
            "rndProjectName",
            "rndSpecialInstituteName",
            "rndTaskContribution",
            "rndTaskName",
            "rndTaskNumber",
        ]
    },
    "rndInfoArray",
    "rndInfo",
)

_ALL_FIELDS = sorted(_FIELD_REGISTRY)
_DEFAULT_FIELDS = [
    "applicationNumber",
    "applicationDate",
    "inventionTitle",
    "applicantName",
    "registerStatus",
    "ipcNumber",
]


def _as_list(value: t.Any) -> t.List[t.Any]:
    """xmltodict collapses a single repeated element into a dict; normalize to a list."""
    if value is None:
        return []
    return value if isinstance(value, list) else [value]


def _extract_field(item: t.Dict, array_key: str, item_key: str, source_field: str, sep: str) -> t.Optional[str]:
    array_node = item.get(array_key)
    if not isinstance(array_node, dict):
        return None

    values = [
        str(entry[source_field])
        for entry in _as_list(array_node.get(item_key))
        if isinstance(entry, dict) and entry.get(source_field) not in (None, "")
    ]
    return sep.join(values) if values else None


def _select_fields(item: t.Dict, fields: t.List[str]) -> pd.DataFrame:
    row = {field: _extract_field(item, *_FIELD_REGISTRY[field]) for field in fields}
    return pd.DataFrame([row]).fillna("")


class PatentDetailSearchArgs(BaseModel):
    application_number: str = Field(..., description="출원번호 (숫자만, 하이픈(-) 없이 입력하세요. 예: 1020230045678)")
    fields: t.Optional[t.List[str]] = Field(
        default=None,
        description=(
            "반환할 필드 목록. 지정하지 않거나 빈 배열이면 기본 요약 필드만 반환합니다. "
            f"사용 가능한 전체 필드: {', '.join(_ALL_FIELDS)}"
        ),
    )

    @field_validator("fields")
    @classmethod
    def _validate_fields(cls, value: t.Optional[t.List[str]]) -> t.Optional[t.List[str]]:
        if not value:
            return value
        unknown = sorted(set(value) - set(_FIELD_REGISTRY))
        if unknown:
            raise ValueError(f"알 수 없는 필드: {', '.join(unknown)}. 사용 가능한 필드: {', '.join(_ALL_FIELDS)}")
        return value


class PatentDetailSearchTool(ToolHandler):
    def __init__(self):
        super().__init__("patent_detail_search")
        self.api = PatentDetailSearchAPI(api_key=api_key)
        self.description = "patent search by applicant name"

    def get_tool_description(self) -> Tool:
        logger.info(f"get_tool_description: {self.name}")
        tool = Tool(
            name=self.name,
            description=self.description,
            inputSchema={
                "type": "object",
                "properties": {
                    "application_number": {"type": "string", "description": "출원번호"},
                    "fields": {
                        "type": "array",
                        "items": {"type": "string", "enum": _ALL_FIELDS},
                        "description": (
                            f"반환할 필드 목록(자유 조합 가능). 생략하거나 빈 배열이면 기본 요약 필드"
                            f"({', '.join(_DEFAULT_FIELDS)})만 반환합니다."
                        ),
                    },
                },
                "required": ["application_number"],
            },
            metadata={
                "usage_hint": (
                    "출원번호가 주어졌을 때, 해당 특허의 상세한 법적/기술적 정보를 보여줍니다. "
                    "기본적으로는 요약 필드만 반환하며, 초록/청구항/출원인 등 더 상세한 정보가 필요하면 "
                    "fields 파라미터로 필요한 필드만 선택해서 요청하세요(토큰 절약)."
                ),
                "example_user_queries": [
                    "출원번호 1020250037551 특허의 상세 정보 알려줘",
                    "이 특허의 청구항 전문을 보여줘",
                    "이 특허의 초록과 IPC 코드만 알려줘",
                ],
                "preferred_response_style": (
                    "정보가 많기 때문에 Markdown 형식으로 구분된 섹션별로 정리해서 보여주세요. "
                    "예: 기본정보 / 출원인정보 / 발명자정보 / 대리인정보 / 우선권정보 등"
                ),
            },
        )
        return tool

    def run_tool(self, args: dict) -> Sequence[TextContent | ImageContent | EmbeddedResource]:
        try:
            validated_args = PatentDetailSearchArgs(**args)
            validated_args.application_number = validated_args.application_number.replace("-", "")
            logger.info(f"Searching for application number: {validated_args.application_number}")

            response = self.api.sync_search(application_number=validated_args.application_number)

            if response.empty:
                return [TextContent(type="text", text="there is no result")]

            item = response.iloc[0].to_dict()
            summary_df = _select_fields(item, validated_args.fields or _DEFAULT_FIELDS)
            return [TextContent(type="text", text=summary_df.to_markdown(index=False))]

        except ValidationError as e:
            logger.error(f"Validation error: {str(e)}")
            return [TextContent(type="text", text=f"입력값 검증 오류: {str(e)}")]
        except Exception as e:
            logger.error(f"Error occurred: {str(e)}")
            return [TextContent(type="text", text=f"오류가 발생했습니다: {str(e)}")]

    async def run_tool_async(self, args: dict) -> Sequence[TextContent | ImageContent | EmbeddedResource]:
        try:
            validated_args = PatentDetailSearchArgs(**args)
            validated_args.application_number = validated_args.application_number.replace("-", "")
            logger.info(f"Searching for application number: {validated_args.application_number}")

            response = await self.api.async_search(application_number=validated_args.application_number)

            if response.empty:
                return [TextContent(type="text", text="there is no result")]

            item = response.iloc[0].to_dict()
            summary_df = _select_fields(item, validated_args.fields or _DEFAULT_FIELDS)
            return [TextContent(type="text", text=summary_df.to_markdown(index=False))]

        except ValidationError as e:
            logger.error(f"Validation error: {str(e)}")
            return [TextContent(type="text", text=f"입력값 검증 오류: {str(e)}")]
        except Exception as e:
            logger.error(f"Error occurred: {str(e)}")
            return [TextContent(type="text", text=f"오류가 발생했습니다: {str(e)}")]
