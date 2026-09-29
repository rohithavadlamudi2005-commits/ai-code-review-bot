import ast
import re
from typing import List, Optional
from app.analyzers.base import CodeAnalyzer
from app.models.finding import Finding, Severity, Category

# Regex for common secret variable names
SECRET_VAR_PATTERN = re.compile(
    r"(?i).*(api_key|secret_key|private_key|access_token|auth_token|passwd|password|client_secret|aws_secret).*"
)

# Regex for detecting common secret token formats (e.g. ghp_, sk_live_, etc.)
SECRET_VALUE_PATTERN = re.compile(
    r"^(ghp_[a-zA-Z0-9]{36}|sk_live_[a-zA-Z0-9]{24,}|AKIA[0-9A-Z]{16}|[a-zA-Z0-9+/]{40}=*)$"
)

# SQL keyword patterns
SQL_PATTERN = re.compile(r"(?i)\b(SELECT|INSERT\s+INTO|UPDATE|DELETE\s+FROM|DROP\s+TABLE|ALTER\s+TABLE)\b")


class PythonASTVisitor(ast.NodeVisitor):
    """
    AST Visitor to traverse Python source code and collect security & quality findings.
    """

    def __init__(self, filename: str, source_lines: List[str]):
        self.filename = filename
        self.source_lines = source_lines
        self.findings: List[Finding] = []

    def visit_Assign(self, node: ast.Assign):
        """
        PY-SEC-001: Hardcoded Secrets Detection
        """
        for target in node.targets:
            target_name = ""
            if isinstance(target, ast.Name):
                target_name = target.id
            elif isinstance(target, ast.Attribute):
                target_name = target.attr

            if target_name and SECRET_VAR_PATTERN.match(target_name):
                str_val = None
                if isinstance(node.value, ast.Constant) and isinstance(node.value.value, str):
                    str_val = node.value.value

                if str_val and len(str_val.strip()) > 3:
                    # Ignore obvious placeholders like "your_api_key_here", "CHANGE_ME", "", "env"
                    lower_val = str_val.lower()
                    if not any(ph in lower_val for ph in ["change_me", "your_", "todo", "placeholder", "xxx", "dummy"]):
                        self.findings.append(Finding(
                            rule_id="PY-SEC-001",
                            category=Category.SECURITY.value,
                            severity=Severity.HIGH.value,
                            confidence=0.90,
                            file=self.filename,
                            line=node.lineno,
                            message=f"Possible hardcoded secret in variable '{target_name}'",
                            explanation=f"Variable '{target_name}' is assigned a hardcoded string literal. Hardcoding secrets exposes sensitive credentials in source code.",
                            suggestion="Move secrets to environment variables or a secure key management system."
                        ))

        self.generic_visit(node)

    def visit_Call(self, node: ast.Call):
        """
        PY-SEC-002: Dangerous eval/exec
        PY-SEC-003: Unsafe subprocess shell=True / os.system
        PY-QUAL-002: Debug statements (print, breakpoint)
        """
        func = node.func
        func_name = ""

        if isinstance(func, ast.Name):
            func_name = func.id
        elif isinstance(func, ast.Attribute):
            func_name = func.attr

        # PY-SEC-002: Dangerous eval/exec
        if func_name in ("eval", "exec"):
            self.findings.append(Finding(
                rule_id="PY-SEC-002",
                category=Category.SECURITY.value,
                severity=Severity.HIGH.value,
                confidence=0.95,
                file=self.filename,
                line=node.lineno,
                message=f"Use of dangerous dynamic execution function '{func_name}()'",
                explanation=f"Calling '{func_name}()' executes arbitrary code string and exposes the application to code injection vulnerabilities.",
                suggestion=f"Avoid using '{func_name}()'. Parse input securely or use safe alternatives like ast.literal_eval()."
            ))

        # PY-SEC-003: Unsafe subprocess usage (shell=True) or os.system
        if func_name == "system" and isinstance(func, ast.Attribute) and isinstance(func.value, ast.Name) and func.value.id == "os":
            self.findings.append(Finding(
                rule_id="PY-SEC-003",
                category=Category.SECURITY.value,
                severity=Severity.HIGH.value,
                confidence=0.90,
                file=self.filename,
                line=node.lineno,
                message="Unsafe os.system() command execution",
                explanation="os.system() passes commands directly to the system shell, leading to command injection risks.",
                suggestion="Use subprocess.run() with shell=False and pass arguments as a list."
            ))

        if func_name in ("run", "Popen", "call", "check_output", "check_call") and isinstance(func, ast.Attribute):
            is_subprocess = (isinstance(func.value, ast.Name) and func.value.id == "subprocess")
            if is_subprocess:
                for kw in node.keywords:
                    if kw.arg == "shell" and isinstance(kw.value, ast.Constant) and kw.value.value is True:
                        self.findings.append(Finding(
                            rule_id="PY-SEC-003",
                            category=Category.SECURITY.value,
                            severity=Severity.HIGH.value,
                            confidence=0.90,
                            file=self.filename,
                            line=node.lineno,
                            message=f"Unsafe subprocess.{func_name}() call with shell=True",
                            explanation="Executing commands with shell=True can allow arbitrary command injection if inputs are user-controlled.",
                            suggestion="Set shell=False and pass command arguments as a list of strings."
                        ))

        # PY-QUAL-002: Debug statements
        if func_name == "print":
            self.findings.append(Finding(
                rule_id="PY-QUAL-002",
                category=Category.QUALITY.value,
                severity=Severity.LOW.value,
                confidence=0.85,
                file=self.filename,
                line=node.lineno,
                message="Use of print() debug statement",
                explanation="print() statements left in production code can pollute stdout logs and leak internal debug info.",
                suggestion="Replace print() with structured logger calls (e.g. logger.info() or logger.debug())."
            ))

        if func_name in ("breakpoint", "set_trace"):
            self.findings.append(Finding(
                rule_id="PY-QUAL-002",
                category=Category.QUALITY.value,
                severity=Severity.MEDIUM.value,
                confidence=0.95,
                file=self.filename,
                line=node.lineno,
                message=f"Debug breakpoint statement '{func_name}()' left in code",
                explanation=f"Calling '{func_name}()' will halt execution in production environments.",
                suggestion="Remove breakpoint/debugger statements before merging code."
            ))

        self.generic_visit(node)

    def visit_JoinedStr(self, node: ast.JoinedStr):
        """
        PY-SEC-004: Potential SQL Injection in f-strings
        """
        raw_text = ""
        has_expression = False

        for value in node.values:
            if isinstance(value, ast.Constant) and isinstance(value.value, str):
                raw_text += value.value
            elif isinstance(value, ast.FormattedValue):
                has_expression = True
                raw_text += " {param} "

        if has_expression and SQL_PATTERN.search(raw_text):
            self.findings.append(Finding(
                rule_id="PY-SEC-004",
                category=Category.SECURITY.value,
                severity=Severity.HIGH.value,
                confidence=0.85,
                file=self.filename,
                line=node.lineno,
                message="Potential SQL Injection via f-string formatting",
                explanation="Constructing SQL queries using f-string interpolation allows attackers to manipulate SQL syntax.",
                suggestion="Use parameterized queries (e.g. cursor.execute('SELECT * FROM users WHERE id = %s', (user_id,)))"
            ))

        self.generic_visit(node)

    def visit_BinOp(self, node: ast.BinOp):
        """
        PY-SEC-004: Potential SQL Injection via string concatenation (+) or modulo (%)
        """
        if isinstance(node.op, (ast.Add, ast.Mod)):
            # Helper to inspect string content
            def contains_sql_literal(expr: ast.AST) -> bool:
                if isinstance(expr, ast.Constant) and isinstance(expr.value, str):
                    return bool(SQL_PATTERN.search(expr.value))
                return False

            if contains_sql_literal(node.left) or contains_sql_literal(node.right):
                self.findings.append(Finding(
                    rule_id="PY-SEC-004",
                    category=Category.SECURITY.value,
                    severity=Severity.HIGH.value,
                    confidence=0.80,
                    file=self.filename,
                    line=node.lineno,
                    message="Potential SQL Injection via string concatenation or format string",
                    explanation="Dynamically building SQL queries with string concatenation or '%' operator enables SQL injection.",
                    suggestion="Use parameterized query placeholders instead of string concatenation."
                ))

        self.generic_visit(node)

    def visit_ExceptHandler(self, node: ast.ExceptHandler):
        """
        PY-QUAL-001: Bare except handler
        """
        if node.type is None:
            self.findings.append(Finding(
                rule_id="PY-QUAL-001",
                category=Category.QUALITY.value,
                severity=Severity.MEDIUM.value,
                confidence=0.95,
                file=self.filename,
                line=node.lineno,
                message="Bare 'except:' catch block detected",
                explanation="Catching all exceptions indiscriminately masks system exceptions like KeyboardInterrupt and SystemExit.",
                suggestion="Catch specific exception classes (e.g., 'except Exception as err:')"
            ))

        self.generic_visit(node)


class PythonAnalyzer(CodeAnalyzer):
    """
    Static analyzer for Python source code utilizing AST parsing.
    """

    @property
    def supported_extensions(self) -> List[str]:
        return [".py"]

    def analyze(self, file_path: str, source_code: str, changed_lines: Optional[List[int]] = None) -> List[Finding]:
        if not source_code or not source_code.strip():
            return []

        source_lines = source_code.splitlines()

        try:
            tree = ast.parse(source_code, filename=file_path)
        except SyntaxError as exc:
            # Handle syntax error gracefully
            return self.filter_findings_by_lines([Finding(
                rule_id="PY-QUAL-000",
                category=Category.QUALITY.value,
                severity=Severity.HIGH.value,
                confidence=1.0,
                file=file_path,
                line=exc.lineno or 1,
                message="Python Syntax Error",
                explanation=f"Unable to parse Python code: {exc.msg}",
                suggestion="Fix the syntax error to enable complete static analysis."
            )], changed_lines)

        visitor = PythonASTVisitor(file_path, source_lines)
        visitor.visit(tree)

        return self.filter_findings_by_lines(visitor.findings, changed_lines)
