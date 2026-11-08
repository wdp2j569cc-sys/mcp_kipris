"""KIPRIS 응답 형태를 흉내 낸 테스트용 XML (실제 서버 응답이 아님)."""

LIST_XML = """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<response>
  <header><resultCode>00</resultCode><resultMsg>NORMAL SERVICE.</resultMsg></header>
  <body>
    <items>
      <item>
        <applicantName>테스트항공</applicantName>
        <applicationDate>20230315</applicationDate>
        <applicationNumber>1020230034567</applicationNumber>
        <astrtCont>{abstract}</astrtCont>
        <inventionTitle>전익기의 측풍 착륙 제어 방법</inventionTitle>
        <ipcNumber>B64C 39/02</ipcNumber>
        <registerStatus>등록</registerStatus>
      </item>
      <item>
        <applicantName>샘플대학교</applicantName>
        <applicationDate>20220101</applicationDate>
        <applicationNumber>1020220000123</applicationNumber>
        <astrtCont>짧은 초록</astrtCont>
        <inventionTitle>가변 미익 무인기</inventionTitle>
        <ipcNumber></ipcNumber>
        <registerStatus>공개</registerStatus>
      </item>
    </items>
  </body>
  <count><numOfRows>10</numOfRows><pageNo>1</pageNo><totalCount>42</totalCount></count>
</response>
"""

EMPTY_XML = """<?xml version="1.0" encoding="UTF-8"?>
<response><header><resultCode>20</resultCode><resultMsg>NO OPEN API SERVICE ERROR</resultMsg></header></response>
"""

KEY_ERROR_XML = """<?xml version="1.0" encoding="UTF-8"?>
<response><header><resultCode>30</resultCode><resultMsg>SERVICE KEY IS NOT REGISTERED ERROR.</resultMsg></header></response>
"""

PORTAL_ERROR_XML = """<?xml version="1.0" encoding="UTF-8"?>
<OpenAPI_ServiceResponse>
  <cmmMsgHeader><errMsg>SERVICE ERROR</errMsg><returnAuthMsg>SERVICE_KEY_IS_NOT_REGISTERED_ERROR</returnAuthMsg></cmmMsgHeader>
</OpenAPI_ServiceResponse>
"""

DETAIL_XML = """<?xml version="1.0" encoding="UTF-8"?>
<response>
  <header><resultCode>00</resultCode><resultMsg>NORMAL SERVICE.</resultMsg></header>
  <body>
    <item>
      <biblioSummaryInfoArray>
        <biblioSummaryInfo>
          <applicationNumber>1020230034567</applicationNumber>
          <inventionTitle>전익기의 측풍 착륙 제어 방법</inventionTitle>
        </biblioSummaryInfo>
      </biblioSummaryInfoArray>
      <abstractInfoArray><abstractInfo><astrtCont>상세 초록입니다.</astrtCont></abstractInfo></abstractInfoArray>
      <claimInfoArray>
        <claimInfo><claim>청구항 1. 전익기에 있어서 ...</claim></claimInfo>
        <claimInfo><claim>청구항 2. 제1항에 있어서 ...</claim></claimInfo>
      </claimInfoArray>
    </item>
  </body>
</response>
"""
