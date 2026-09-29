import pytest
from app.analyzers.engine import AnalysisEngine


def test_engine_diff_aware_filtering():
    engine = AnalysisEngine()
    code = """import os
API_KEY = "ghp_1234567890abcdef1234567890abcdef"
print("Debug statement")
def foo():
    eval("1+1")
"""
    # Finding on line 2 (secret), line 3 (print), line 5 (eval)

    # 1. Analyze entire file without changed_lines filter
    resp_full = engine.analyze_file("app.py", code, changed_lines=None)
    assert resp_full.total_findings == 3

    # 2. Analyze with changed_lines = [5] (only line 5 changed in PR)
    resp_diff = engine.analyze_file("app.py", code, changed_lines=[5])
    assert resp_diff.total_findings == 1
    assert resp_diff.findings[0].line == 5
    assert resp_diff.findings[0].rule_id == "PY-SEC-002"


def test_engine_unsupported_file_extension():
    engine = AnalysisEngine()
    resp = engine.analyze_file("image.png", "binary_data")
    assert resp.skipped is True
    assert "Ignored file type" in resp.skip_reason or "No static analyzer" in resp.skip_reason
    assert resp.total_findings == 0


def test_engine_syntax_error_handling():
    engine = AnalysisEngine()
    invalid_py = "def broken_syntax(:\n    pass"
    resp = engine.analyze_file("bad.py", invalid_py)
    assert resp.skipped is False
    assert resp.total_findings == 1
    assert resp.findings[0].rule_id == "PY-QUAL-000"
    assert "Syntax Error" in resp.findings[0].message
