"""
Modular registry of quality analysis rules for Python and JavaScript/TypeScript.
"""

QUALITY_RULES = {
    "PY-QUAL-000": {
        "rule_id": "PY-QUAL-000",
        "name": "Python Syntax Error",
        "category": "quality",
        "severity": "HIGH",
        "description": "Triggered when Python code contains syntax errors preventing AST analysis."
    },
    "PY-QUAL-001": {
        "rule_id": "PY-QUAL-001",
        "name": "Bare Except Handler",
        "category": "quality",
        "severity": "MEDIUM",
        "description": "Detects try-except blocks catching all exceptions without specifying the exception class."
    },
    "PY-QUAL-002": {
        "rule_id": "PY-QUAL-002",
        "name": "Debug Statements",
        "category": "quality",
        "severity": "LOW",
        "description": "Detects print() and breakpoint() debug calls in Python code."
    },
    "JS-QUAL-001": {
        "rule_id": "JS-QUAL-001",
        "name": "Console Logging Statements",
        "category": "quality",
        "severity": "LOW",
        "description": "Detects console.log(), console.debug(), and console.trace() calls in JS/TS code."
    }
}
