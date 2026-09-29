import pytest
from app.services.github_review_formatter import GitHubReviewFormatter
from app.services.review_service import CombinedFinding


def test_format_review_summary_empty():
    md = GitHubReviewFormatter.format_review_summary([], {}, 3, 0)
    assert "AI Code Review" in md
    assert "Clean Code Review!" in md
    assert "3 analyzed file(s)" in md


def test_format_review_summary_with_findings():
    findings = [
        CombinedFinding(
            id="1",
            category="security",
            severity="HIGH",
            confidence=0.9,
            file="app.py",
            line=42,
            message="Potential SQL Injection",
            explanation="Concatenated input into SQL query.",
            suggestion="Use parameterized query.",
            evidence="query = 'SELECT * FROM users WHERE id=' + user_id",
            source="combined",
            static_rule_id="PY-SEC-004"
        )
    ]
    severity_counts = {"CRITICAL": 0, "HIGH": 1, "MEDIUM": 0, "LOW": 0, "INFO": 0}

    md = GitHubReviewFormatter.format_review_summary(findings, severity_counts, 1, 0)
    assert "Found **1 issue(s)**" in md
    assert "HIGH" in md
    assert "Potential SQL Injection" in md
    assert "app.py" in md
    assert "Line:` `42`" in md or "Line:** `42`" in md or "42" in md


def test_prepare_inline_comments():
    findings = [
        CombinedFinding(
            id="1",
            category="security",
            severity="HIGH",
            confidence=0.9,
            file="app.py",
            line=42,
            message="High severity issue",
            explanation="Expl",
            suggestion="Sugg",
            evidence="code",
            source="static",
            static_rule_id="PY-SEC-001"
        ),
        CombinedFinding(
            id="2",
            category="quality",
            severity="LOW",
            confidence=0.8,
            file="app.py",
            line=None,
            message="General quality issue",
            explanation="General explanation",
            suggestion="Fix general",
            evidence=None,
            source="llm"
        )
    ]

    inline, unplaced = GitHubReviewFormatter.prepare_inline_comments(findings)
    assert len(inline) == 1
    assert inline[0]["path"] == "app.py"
    assert inline[0]["line"] == 42
    assert "High severity issue" in inline[0]["body"]

    assert len(unplaced) == 1
    assert unplaced[0].id == "2"
