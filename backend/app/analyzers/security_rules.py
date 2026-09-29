"""
Modular registry of security analysis rules for Python and JavaScript/TypeScript.
"""

SECURITY_RULES = {
    "PY-SEC-001": {
        "rule_id": "PY-SEC-001",
        "name": "Hardcoded Secrets",
        "category": "security",
        "severity": "HIGH",
        "description": "Detects hardcoded passwords, tokens, and secret API keys assigned to variables."
    },
    "PY-SEC-002": {
        "rule_id": "PY-SEC-002",
        "name": "Dangerous eval/exec",
        "category": "security",
        "severity": "HIGH",
        "description": "Detects usage of eval() and exec() dynamic code execution functions."
    },
    "PY-SEC-003": {
        "rule_id": "PY-SEC-003",
        "name": "Unsafe Subprocess Execution",
        "category": "security",
        "severity": "HIGH",
        "description": "Detects subprocess calls with shell=True or os.system calls vulnerable to command injection."
    },
    "PY-SEC-004": {
        "rule_id": "PY-SEC-004",
        "name": "Potential SQL Injection",
        "category": "security",
        "severity": "HIGH",
        "description": "Detects SQL queries built via string concatenation, f-strings, or string formatting."
    },
    "JS-SEC-001": {
        "rule_id": "JS-SEC-001",
        "name": "Dangerous eval()",
        "category": "security",
        "severity": "HIGH",
        "description": "Detects dangerous eval() or dynamic Function execution in JavaScript/TypeScript."
    },
    "JS-SEC-002": {
        "rule_id": "JS-SEC-002",
        "name": "Hardcoded Secrets",
        "category": "security",
        "severity": "HIGH",
        "description": "Detects hardcoded API keys, JWT secrets, or tokens in JS/TS source code."
    },
    "JS-SEC-003": {
        "rule_id": "JS-SEC-003",
        "name": "Dangerous innerHTML / XSS",
        "category": "security",
        "severity": "HIGH",
        "description": "Detects unsafe assignment to innerHTML, outerHTML, or document.write leading to XSS."
    }
}
