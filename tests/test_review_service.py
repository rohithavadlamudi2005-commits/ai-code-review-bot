import pytest
from app.services.review_service import ReviewService, CombinedFinding
from app.models.finding import Finding
from app.llm.schemas import LLMFinding


def test_combine_findings_deduplication():
    service = ReviewService()

    static_finding = Finding(
        rule_id="PY-SEC-003",
        category="security",
        severity="HIGH",
        confidence=0.90,
        file="runner.py",
        line=42,
        message="Unsafe subprocess.run() with shell=True",
        explanation="Static rule violation: command injection risk.",
        suggestion="Set shell=False"
    )

    llm_finding_matched = LLMFinding(
        category="security",
        severity="HIGH",
        confidence=0.95,
        file="runner.py",
        line=42,
        message="Potential command injection via subprocess",
        explanation="Attacker input passed to shell execution.",
        suggestion="Use list arguments with shell=False",
        evidence="subprocess.run(user_input, shell=True)"
    )

    llm_finding_unmatched = LLMFinding(
        category="quality",
        severity="LOW",
        confidence=0.85,
        file="runner.py",
        line=80,
        message="Missing type annotation",
        explanation="Function parameter lacks type hint.",
        suggestion="Add : str type annotation",
        evidence="def process(val):"
    )

    combined = service.combine_findings(
        filename="runner.py",
        static_findings=[static_finding],
        llm_findings=[llm_finding_matched, llm_finding_unmatched]
    )

    assert len(combined) == 2

    # Matched item (combined)
    matched_item = [c for c in combined if c.source == "combined"][0]
    assert matched_item.static_rule_id == "PY-SEC-003"
    assert matched_item.line == 42
    assert matched_item.evidence == "subprocess.run(user_input, shell=True)"
    assert "[AI LLM Insight]" in matched_item.explanation

    # Unmatched LLM item
    llm_item = [c for c in combined if c.source == "llm"][0]
    assert llm_item.line == 80
    assert llm_item.category == "quality"
