import pytest
from app.analyzers.python_analyzer import PythonAnalyzer
from app.analyzers.javascript_analyzer import JavaScriptAnalyzer


def test_python_safe_sql_parameterization():
    analyzer = PythonAnalyzer()
    safe_code = """
def get_user(cursor, user_id, role):
    # Safe parameterized query
    cursor.execute("SELECT * FROM users WHERE id = %s AND role = %s", (user_id, role))
    return cursor.fetchone()
"""
    findings = analyzer.analyze("app/users.py", safe_code)
    # Ensure no PY-SEC-004 SQL injection finding
    sql_findings = [f for f in findings if f.rule_id == "PY-SEC-004"]
    assert len(sql_findings) == 0


def test_python_safe_subprocess_usage():
    analyzer = PythonAnalyzer()
    safe_code = """
import subprocess

def list_files(path):
    # Safe subprocess execution with shell=False
    res = subprocess.run(["ls", "-la", path], shell=False, capture_output=True, check=True)
    return res.stdout
"""
    findings = analyzer.analyze("app/utils.py", safe_code)
    sec_findings = [f for f in findings if f.rule_id == "PY-SEC-003"]
    assert len(sec_findings) == 0


def test_python_normal_strings_and_logging():
    analyzer = PythonAnalyzer()
    safe_code = """
import logging

logger = logging.getLogger(__name__)

MENU_TITLE = "Select your option from the list below"
QUERY_LABEL = "SELECT items"

def process_item(item_name: str):
    logger.info("Processing item: %s", item_name)
    return item_name.upper()
"""
    findings = analyzer.analyze("app/menu.py", safe_code)
    # Ensure no print debug statements or secrets findings
    assert len(findings) == 0


def test_python_safe_exception_handling():
    analyzer = PythonAnalyzer()
    safe_code = """
def parse_number(text: str) -> int:
    try:
        return int(text)
    except ValueError as err:
        return 0
    except (TypeError, KeyIndexError) as exc:
        return -1
"""
    findings = analyzer.analyze("app/parser.py", safe_code)
    bare_excepts = [f for f in findings if f.rule_id == "PY-QUAL-001"]
    assert len(bare_excepts) == 0


def test_javascript_safe_dom_manipulation():
    analyzer = JavaScriptAnalyzer()
    safe_code = """
function renderUserName(element, username) {
    // Safe textContent usage instead of innerHTML
    element.textContent = username;
    element.setAttribute("title", "Select User Account");
}
"""
    findings = analyzer.analyze("src/user.js", safe_code)
    xss_findings = [f for f in findings if f.rule_id == "JS-SEC-003"]
    assert len(xss_findings) == 0


def test_javascript_safe_strings_and_placeholder_secrets():
    analyzer = JavaScriptAnalyzer()
    safe_code = """
const apiKey = "your_api_key_here";
const clientSecret = "placeholder_secret";
const labelText = "SELECT YOUR OPTION";
"""
    findings = analyzer.analyze("src/config.js", safe_code)
    secrets = [f for f in findings if f.rule_id == "JS-SEC-002"]
    assert len(secrets) == 0
