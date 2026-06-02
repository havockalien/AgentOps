"""
Tests for agent.tools — BaseTool, WebSearchTool, CodeRunnerTool, etc.
"""

from __future__ import annotations

import pytest


class TestBaseTool:
    def test_tool_repr(self):
        from agent.tools.base_tool import BaseTool
        from agent.tools.web_search import WebSearchTool
        tool = WebSearchTool()
        assert "web_search" in repr(tool)

    @pytest.mark.asyncio
    async def test_execute_returns_success_key(self):
        from agent.tools.web_search import WebSearchTool
        tool = WebSearchTool()
        result = await tool.execute(query="test query")
        assert "success" in result
        assert "output" in result

    @pytest.mark.asyncio
    async def test_execute_catches_exceptions(self):
        """BaseTool.execute() should not raise — it catches and returns error dict."""
        from agent.tools.base_tool import BaseTool

        class BrokenTool(BaseTool):
            name = "broken_tool"
            description = "always fails"
            schema = {}

            async def _execute(self, **kwargs):
                raise RuntimeError("Intentional failure")

        tool = BrokenTool()
        result = await tool.execute()
        assert result["success"] is False
        assert "error" in result
        assert "Intentional failure" in result["error"]


class TestToolRegistry:
    def test_registry_contains_all_tools(self):
        from agent.tools.base_tool import get_registry
        from agent.tools import WebSearchTool, CodeRunnerTool, FileReaderTool, SqlRunnerTool
        registry = get_registry()
        assert "web_search" in registry.names()
        assert "code_runner" in registry.names()
        assert "file_reader" in registry.names()
        assert "sql_runner" in registry.names()

    def test_registry_get_returns_tool(self):
        from agent.tools.base_tool import get_registry
        registry = get_registry()
        tool = registry.get("web_search")
        assert tool is not None
        assert tool.name == "web_search"


class TestWebSearchTool:
    @pytest.mark.asyncio
    async def test_stub_response_when_no_api_key(self, monkeypatch):
        """Without SERPAPI_KEY, should return stub response with success=True."""
        monkeypatch.delenv("SERPAPI_KEY", raising=False)
        from agent.tools.web_search import WebSearchTool
        tool = WebSearchTool()
        result = await tool.execute(query="test search")
        assert result["success"] is True
        assert result.get("stub") is True
        assert "test search" in result["output"]


class TestCodeRunnerTool:
    @pytest.mark.asyncio
    async def test_simple_python_execution(self):
        from agent.tools.code_runner import CodeRunnerTool
        tool = CodeRunnerTool()
        result = await tool.execute(code="print('hello world')")
        assert result["success"] is True
        assert "hello world" in result["output"]

    @pytest.mark.asyncio
    async def test_math_computation(self):
        from agent.tools.code_runner import CodeRunnerTool
        tool = CodeRunnerTool()
        result = await tool.execute(code="print(2 + 2)")
        assert result["success"] is True
        assert "4" in result["output"]

    @pytest.mark.asyncio
    async def test_syntax_error_returns_failure(self):
        from agent.tools.code_runner import CodeRunnerTool
        tool = CodeRunnerTool()
        result = await tool.execute(code="def broken(: pass")
        assert result["success"] is False or result.get("exit_code", 0) != 0


class TestFileReaderTool:
    @pytest.mark.asyncio
    async def test_read_nonexistent_file(self, tmp_path, monkeypatch):
        monkeypatch.setenv("AGENT_WORKSPACE", str(tmp_path))
        # Re-import to pick up env var
        import importlib
        import agent.tools.file_reader as fr
        importlib.reload(fr)
        tool = fr.FileReaderTool()
        result = await tool.execute(action="read", path="nonexistent.txt")
        assert result.get("error") == "not_found"

    @pytest.mark.asyncio
    async def test_write_and_read_file(self, tmp_path, monkeypatch):
        monkeypatch.setenv("AGENT_WORKSPACE", str(tmp_path))
        import importlib
        import agent.tools.file_reader as fr
        importlib.reload(fr)
        tool = fr.FileReaderTool()
        write_result = await tool.execute(action="write", path="test.txt", content="hello agent")
        assert write_result["success"] is True
        read_result = await tool.execute(action="read", path="test.txt")
        assert "hello agent" in read_result["output"]


class TestSqlRunnerTool:
    @pytest.mark.asyncio
    async def test_stub_response_without_db(self, monkeypatch):
        monkeypatch.delenv("POSTGRES_URL", raising=False)
        from agent.tools.sql_runner import SqlRunnerTool
        tool = SqlRunnerTool()
        result = await tool.execute(query="SELECT 1")
        assert result["success"] is True
        assert result.get("stub") is True

    @pytest.mark.asyncio
    async def test_blocks_dml_statements(self):
        from agent.tools.sql_runner import SqlRunnerTool
        tool = SqlRunnerTool()
        result = await tool.execute(query="DELETE FROM users")
        # Should fail with a ValueError before reaching DB
        assert result["success"] is False
        assert "not allowed" in result.get("error", "").lower() or "permitted" in result.get("error", "").lower() or "DELETE" in result.get("output", "")
