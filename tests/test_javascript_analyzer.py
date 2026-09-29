import pytest
from app.analyzers.javascript_analyzer import JavaScriptAnalyzer


def test_js_eval_detection():
    analyzer = JavaScriptAnalyzer()
    code = """
function executeCode(input) {
    eval(input);
    const fn = new Function(input);
}
"""
    findings = analyzer.analyze("app.js", code)
    eval_findings = [f for f in findings if f.rule_id == "JS-SEC-001"]
    assert len(eval_findings) >= 1


def test_js_inner_html_detection():
    analyzer = JavaScriptAnalyzer()
    code = """
function renderUser(userInput) {
    const div = document.getElementById("content");
    div.innerHTML = "<p>" + userInput + "</p>";
    document.write("Hello");
}
"""
    findings = analyzer.analyze("render.jsx", code)
    xss_findings = [f for f in findings if f.rule_id == "JS-SEC-003"]
    assert len(xss_findings) >= 1


def test_js_console_log_detection():
    analyzer = JavaScriptAnalyzer()
    code = """
const Component = () => {
    console.log("Rendering component");
    console.debug("State update");
    return <div>Hello</div>;
};
"""
    findings = analyzer.analyze("Component.tsx", code)
    log_findings = [f for f in findings if f.rule_id == "JS-QUAL-001"]
    assert len(log_findings) >= 2


def test_js_hardcoded_secrets_detection():
    analyzer = JavaScriptAnalyzer()
    code = """
const API_KEY = "sk_live_99887766554433221100";
const SECRET_KEY = "secret_auth_token_9999";
const normalVar = "Hello World";
"""
    findings = analyzer.analyze("config.ts", code)
    secret_findings = [f for f in findings if f.rule_id == "JS-SEC-002"]
    assert len(secret_findings) >= 1
    rule_lines = [f.line for f in secret_findings]
    assert 2 in rule_lines or 3 in rule_lines
