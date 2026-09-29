import pytest
from app.services.diff_parser import DiffParser, ParsedDiff, DiffHunk, LineChange, HunkLine


def test_parse_empty_or_none_patch():
    res1 = DiffParser.parse_patch(None, file_path="app.py")
    assert res1.file_path == "app.py"
    assert res1.hunks == []
    assert res1.added_lines == []
    assert res1.removed_lines == []
    assert res1.changed_line_numbers == []
    assert not res1.is_binary

    res2 = DiffParser.parse_patch("", file_path="app.py")
    assert res2.hunks == []


def test_parse_binary_patch():
    patch = "Binary files a/image.png and b/image.png differ"
    res = DiffParser.parse_patch(patch, file_path="image.png")
    assert res.is_binary
    assert res.file_path == "image.png"
    assert res.hunks == []


def test_parse_single_hunk_patch():
    patch = """--- a/src/main.py
+++ b/src/main.py
@@ -10,5 +10,6 @@ def process():
 line_10
-line_11_old
+line_11_new
+line_12_added
 line_13
"""
    res = DiffParser.parse_patch(patch, file_path="src/main.py")
    assert res.file_path == "src/main.py"
    assert res.old_file_path == "src/main.py"
    assert len(res.hunks) == 1
    hunk = res.hunks[0]
    assert hunk.old_start == 10
    assert hunk.new_start == 10

    # Added lines checks
    assert len(res.added_lines) == 2
    assert res.added_lines[0].line_number == 11
    assert res.added_lines[0].content == "line_11_new"
    assert res.added_lines[1].line_number == 12
    assert res.added_lines[1].content == "line_12_added"

    # Removed lines checks
    assert len(res.removed_lines) == 1
    assert res.removed_lines[0].line_number == 11
    assert res.removed_lines[0].content == "line_11_old"

    # Changed line numbers list
    assert res.changed_line_numbers == [11, 12]


def test_parse_multi_hunk_patch():
    patch = """@@ -1,3 +1,4 @@
 line1
+line1_plus
 line2
 line3
@@ -20,3 +21,4 @@
 line20
-line21_old
+line21_new
+line22_new
 line23
"""
    res = DiffParser.parse_patch(patch, file_path="test.txt")
    assert len(res.hunks) == 2

    # First hunk: line1_plus added at new line 2
    assert res.hunks[0].new_start == 1

    # Second hunk: new_start=21
    assert res.hunks[1].new_start == 21

    added_nums = [l.line_number for l in res.added_lines]
    assert added_nums == [2, 22, 23]

    removed_nums = [l.line_number for l in res.removed_lines]
    assert removed_nums == [21]

    assert res.changed_line_numbers == [2, 22, 23]


def test_parse_patch_with_no_newline_comment():
    patch = """@@ -1,2 +1,2 @@
-old line
\\ No newline at end of file
+new line
\\ No newline at end of file
"""
    res = DiffParser.parse_patch(patch, file_path="hello.txt")
    assert len(res.added_lines) == 1
    assert res.added_lines[0].content == "new line"
    assert len(res.removed_lines) == 1
    assert res.removed_lines[0].content == "old line"
