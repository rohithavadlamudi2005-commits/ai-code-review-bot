import re
from typing import List, Optional
import esprima

from app.analyzers.base import CodeAnalyzer
from app.models.finding import Finding, Severity, Category

# Regex patterns for line scanning
JS_SECRET_PATTERN = re.compile(
    r"(?i)(const|let|var|readonly)\s+([a-z0-9_$]*(api_key|secret_key|private_key|access_token|auth_token|passwd|password|client_secret)[a-z0-9_$]*)\s*[:=]\s*(['\"`])([^\'\"`]{4,})\4"
)

JS_EVAL_PATTERN = re.compile(r"\b(eval\s*\(|new\s+Function\s*\()")
JS_INNER_HTML_PATTERN = re.compile(r"(\.innerHTML\s*=|\.outerHTML\s*=|document\.write\s*\()")
JS_CONSOLE_PATTERN = re.compile(r"\bconsole\.(log|debug|trace)\s*\(")


class JavaScriptAnalyzer(CodeAnalyzer):
    """
    Static analyzer for JavaScript and TypeScript source files (.js, .jsx, .ts, .tsx).
    Uses combined line-by-line pattern scanning and AST parsing for reliable detection across JS/TS/JSX dialects.
    """

    @property
    def supported_extensions(self) -> List[str]:
        return [".js", ".jsx", ".ts", ".tsx"]

    def analyze(self, file_path: str, source_code: str, changed_lines: Optional[List[int]] = None) -> List[Finding]:
        if not source_code or not source_code.strip():
            return []

        lines = source_code.splitlines()
        findings: List[Finding] = []

        # 1. Line-by-line token scanning (works across JS, JSX, TS, TSX)
        findings.extend(self._analyze_lines(lines, file_path))

        # 2. Esprima AST parsing for deep AST analysis where supported
        try:
            parsed_ast = esprima.parseModule(source_code, {"tolerant": True, "loc": True})
            findings.extend(self._analyze_ast(parsed_ast, file_path))
        except Exception:
            try:
                parsed_ast = esprima.parseScript(source_code, {"tolerant": True, "loc": True})
                findings.extend(self._analyze_ast(parsed_ast, file_path))
            except Exception:
                pass

        # 3. Deduplicate findings by (rule_id, line)
        seen = set()
        deduped: List[Finding] = []
        for f in findings:
            key = (f.rule_id, f.line)
            if key not in seen:
                seen.add(key)
                deduped.append(f)

        return self.filter_findings_by_lines(deduped, changed_lines)

    def _analyze_ast(self, ast_tree: esprima.nodes.Node, file_path: str) -> List[Finding]:
        """
        Walks Esprima AST nodes to identify AST-specific JS rule violations.
        """
        findings: List[Finding] = []

        def get_prop(obj, prop_name):
            if isinstance(obj, dict):
                return obj.get(prop_name)
            return getattr(obj, prop_name, None)

        def walk(node):
            if not node:
                return

            node_type = get_prop(node, "type")
            loc = get_prop(node, "loc")
            line_no = loc.start.line if loc and hasattr(loc, "start") else 1

            if node_type == "CallExpression":
                callee = get_prop(node, "callee")
                if callee:
                    callee_name = get_prop(callee, "name")
                    if callee_name == "eval":
                        findings.append(Finding(
                            rule_id="JS-SEC-001",
                            category=Category.SECURITY.value,
                            severity=Severity.HIGH.value,
                            confidence=0.95,
                            file=file_path,
                            line=line_no,
                            message="Dangerous use of eval() function",
                            explanation="eval() executes arbitrary strings as JavaScript code, introducing severe XSS and code injection vulnerabilities.",
                            suggestion="Avoid eval(). Use JSON.parse() or structured logic instead."
                        ))

            # Recursively traverse children
            if isinstance(node, dict):
                for v in node.values():
                    if isinstance(v, dict):
                        walk(v)
                    elif isinstance(v, list):
                        for item in v:
                            if isinstance(item, dict):
                                walk(item)
            elif hasattr(node, "__dict__"):
                for v in node.__dict__.values():
                    if hasattr(v, "type"):
                        walk(v)
                    elif isinstance(v, list):
                        for item in v:
                            if hasattr(item, "type"):
                                walk(item)

        try:
            walk(ast_tree)
        except Exception:
            pass

        return findings

    def _analyze_lines(self, lines: List[str], file_path: str) -> List[Finding]:
        """
        Line-by-line scanner for JS/TS/JSX code.
        """
        findings: List[Finding] = []

        for idx, line in enumerate(lines, start=1):
            stripped = line.strip()

            if stripped.startswith("//") or stripped.startswith("/*") or stripped.startswith("*"):
                continue

            # JS-SEC-001: Dangerous eval() or new Function()
            if JS_EVAL_PATTERN.search(stripped):
                findings.append(Finding(
                    rule_id="JS-SEC-001",
                    category=Category.SECURITY.value,
                    severity=Severity.HIGH.value,
                    confidence=0.90,
                    file=file_path,
                    line=idx,
                    message="Dangerous use of eval() or dynamic Function constructor",
                    explanation="Executing arbitrary code via eval() or new Function() exposes the frontend/backend to severe XSS or RCE.",
                    suggestion="Avoid dynamic string code execution. Use safe JSON parsing or explicit logic."
                ))

            # JS-SEC-002: Hardcoded secrets
            secret_match = JS_SECRET_PATTERN.search(stripped)
            if secret_match:
                var_name = secret_match.group(2)
                val_str = secret_match.group(5)
                lower_val = val_str.lower()
                if not any(ph in lower_val for ph in ["change_me", "your_", "todo", "placeholder", "xxx", "dummy", "test"]):
                    findings.append(Finding(
                        rule_id="JS-SEC-002",
                        category=Category.SECURITY.value,
                        severity=Severity.HIGH.value,
                        confidence=0.90,
                        file=file_path,
                        line=idx,
                        message=f"Possible hardcoded secret in variable '{var_name}'",
                        explanation=f"Variable '{var_name}' appears to contain a hardcoded credential or secret token.",
                        suggestion="Store secrets in environment variables or client-safe configuration managers."
                    ))

            # JS-SEC-003: Dangerous innerHTML / outerHTML / document.write
            if JS_INNER_HTML_PATTERN.search(stripped):
                findings.append(Finding(
                    rule_id="JS-SEC-003",
                    category=Category.SECURITY.value,
                    severity=Severity.HIGH.value,
                    confidence=0.90,
                    file=file_path,
                    line=idx,
                    message="Dangerous innerHTML / outerHTML / document.write usage",
                    explanation="Injecting raw HTML strings directly into DOM elements without sanitization causes Cross-Site Scripting (XSS).",
                    suggestion="Use element.textContent, React JSX interpolation, or DOMPurify."
                ))

            # JS-QUAL-001: console.log debugging statements
            if JS_CONSOLE_PATTERN.search(stripped):
                findings.append(Finding(
                    rule_id="JS-QUAL-001",
                    category=Category.QUALITY.value,
                    severity=Severity.LOW.value,
                    confidence=0.85,
                    file=file_path,
                    line=idx,
                    message="console.log() debugging statement detected",
                    explanation="console.log statements left in frontend/backend code can leak diagnostic details to users.",
                    suggestion="Remove console.log calls or replace with a dedicated logging utility."
                ))

        return findings
