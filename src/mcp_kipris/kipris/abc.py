from collections.abc import Sequence

import pandas as pd
from mcp.types import EmbeddedResource, ImageContent, TextContent, Tool


class ToolHandler:
    def __init__(self, tool_name: str):
        self.name = tool_name

    def get_tool_description(self) -> Tool:
        raise NotImplementedError("Subclasses must implement this method")

    def run_tool(self, args: dict) -> Sequence[TextContent | ImageContent | EmbeddedResource]:
        raise NotImplementedError("Subclasses must implement this method")

    @staticmethod
    def format_table(df: pd.DataFrame, index: bool = False) -> str:
        """Render a DataFrame as a markdown table, safe for raw KIPRIS data.

        KIPRIS delimits multiple co-applicants/inventors within a single
        field using a literal "|" (e.g. "삼성전자|전남대학교산학협력단"),
        which is also the markdown table column separator — left as-is, it
        splits that one field into a phantom extra column and misaligns the
        whole row (confirmed against the live API). Embedded newlines in
        long text fields do the same thing across rows instead of columns.
        Both are sanitized here so every tool renders a well-formed table
        without each one reimplementing this.
        """

        def _clean(value):
            if pd.isna(value):
                return value
            return str(value).replace("|", "/").replace("\r\n", " ").replace("\n", " ")

        return df.map(_clean).to_markdown(index=index)
