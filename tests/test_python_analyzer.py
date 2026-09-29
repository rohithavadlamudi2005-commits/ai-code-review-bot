import pytest
from app.analyzers.python_analyzer import PythonAnalyzer


def test_python_eval_exec_detection():
    analyzer = PythonAnalyzer()
    code = """
def run_dynamic(user_input):
    eval(user_input)
    exec("import os")
"""
    findings = analyzer.analyze("app.py", code)
    rule_ids = [f.rule_id for f in findings]
    assert "PY-SEC-002" in rule_ids
    assert len([f for f in findings if f.rule_id == "PY-SEC-002"]) == 2


def test_python_subprocess_shell_true_detection():
    analyzer = PythonAnalyzer()
    code = """
import subprocess
import os

def run_cmd(cmd):
    os.system(cmd)
    subprocess.run(cmd, shell=True)
    subprocess.Popen(cmd, shell=False) # Safe
"""
    findings = analyzer.analyze("runner.py", code)
    sec003_findings = [f for f in findings if f.rule_id == "PY-SEC-003"]
    assert len(sec003_findings) == 2
    assert sec003_findings[0].line == 6
    assert sec003_findings[1].line == 7


def test_python_hardcoded_secrets_detection():
    analyzer = PythonAnalyzer()
    code = """
API_KEY = "ghp_1234567890abcdef1234567890abcdef"
SECRET_KEY = "super_secret_auth_token_value_99"
normal_var = "Hello World"
place_holder = "YOUR_API_KEY_HERE"
"""
    findings = analyzer.analyze("config.py", code)
    secret_findings = [f for f in findings if f.rule_id == "PY-SEC-001"]
    lines = [f.line for f in secret_findings]
    assert 2 in lines
    assert 3 in lines
    assert 4 not in lines  # normal_var should not be reported
    assert 5 not in lines  # placeholder should not be reported


def test_python_sql_injection_detection():
    analyzer = PythonAnalyzer()
    code = """
def get_user(user_id):
    query1 = f"SELECT * FROM users WHERE id = {user_id}"
    query2 = "SELECT * FROM users WHERE username = '" + user_id + "'"
    query3 = "SELECT * FROM users WHERE status = 'active'" # Safe static query
    return query1, query2, query3
"""
    findings = analyzer.analyze("db.py", code)
    sql_findings = [f for f in findings if f.rule_id == "PY-SEC-004"]
    lines = [f.line for f in sql_findings]
    assert 3 in lines
    assert 4 in lines
    assert 5 not in lines


def test_python_bare_except_detection():
    analyzer = PythonAnalyzer()
    code = """
try:
    do_something()
except:
    pass

try:
    do_something()
except ValueError as err:
    handle_err(err)
"""
    findings = analyzer.analyze("handler.py", code)
    except_findings = [f for f in findings if f.rule_id == "PY-QUAL-001"]
    assert len(except_findings) == 1
    assert except_findings[0].line == 4


def test_python_debug_statements_detection():
    analyzer = PythonAnalyzer()
    code = """
def calculate():
    print("Debug value")
    breakpoint()
    return 42
"""
    findings = analyzer.analyze("calc.py", code)
    qual002_findings = [f for f in findings if f.rule_id == "PY-QUAL-002"]
    assert len(qual002_findings) == 2
    assert qual002_findings[0].severity == "LOW"
    assert qual002_findings[1].severity == "MEDIUM"


def test_python_safe_code_no_false_positives():
    analyzer = PythonAnalyzer()
    code = """
import logging

logger = logging.getLogger(__name__)

class UserProcessor:
    def __init__(self, name: str):
        self.name = name

    def process(self):
        try:
            logger.info("Processing user: %s", self.name)
        except Exception as err:
            logger.error("Processing failed: %s", err)
            raise
"""
    findings = analyzer.analyze("safe.py", code)
    assert findings == []
