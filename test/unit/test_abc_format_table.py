"""ToolHandler.format_table() sanitizes DataFrame cells before rendering to
markdown. KIPRIS delimits multiple co-applicants/inventors within a single
field with a literal "|" (confirmed live: "삼성전자주식회사|전남대학교산학협력단"
for a co-owned patent), which is also the markdown table column separator —
every one of the 16 tool files that call to_markdown() used to be exposed to
this, corrupting the table whenever a result had more than one applicant.
"""

import pandas as pd
import pytest

from mcp_kipris.kipris.abc import ToolHandler

pytestmark = pytest.mark.unit


def test_pipe_character_does_not_produce_extra_columns():
    df = pd.DataFrame([{"Applicant": "삼성전자|전남대학교산학협력단", "Title": "발명"}])

    text = ToolHandler.format_table(df)
    lines = text.strip().splitlines()

    assert len(lines) == 3  # header, separator, one data row
    assert lines[0].count("|") == lines[2].count("|")
    assert "삼성전자/전남대학교산학협력단" in text


def test_embedded_newline_does_not_split_into_extra_rows():
    df = pd.DataFrame([{"Claim": "1. 청구항\n\n2. 청구항"}])

    text = ToolHandler.format_table(df)

    assert len(text.strip().splitlines()) == 3


def test_missing_values_are_left_as_nan_not_stringified():
    df = pd.DataFrame([{"A": "x", "B": None}])

    text = ToolHandler.format_table(df)

    assert "nan" not in text.lower() or "|    |" in text  # tabulate renders NaN as empty, not the string "None"


def test_normal_values_render_unchanged():
    df = pd.DataFrame([{"ApplicationNumber": "1020230000001", "Applicant": "삼성전자"}])

    text = ToolHandler.format_table(df)

    assert "1020230000001" in text
    assert "삼성전자" in text
