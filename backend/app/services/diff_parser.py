import re
from typing import List, Optional
from pydantic import BaseModel, Field


class HunkLine(BaseModel):
    """
    Represents a single line within a diff hunk.
    """
    type: str  # 'add' (+), 'delete' (-), or 'context' (' ')
    old_line_number: Optional[int] = None
    new_line_number: Optional[int] = None
    content: str


class DiffHunk(BaseModel):
    """
    Represents a single hunk header and its parsed lines.
    """
    header: str
    old_start: int
    old_lines_count: int
    new_start: int
    new_lines_count: int
    lines: List[HunkLine] = Field(default_factory=list)


class LineChange(BaseModel):
    """
    Represents an added or removed line with line number and content.
    """
    line_number: int
    content: str


class ParsedDiff(BaseModel):
    """
    Structured parsed unified diff result.
    """
    file_path: Optional[str] = None
    old_file_path: Optional[str] = None
    hunks: List[DiffHunk] = Field(default_factory=list)
    added_lines: List[LineChange] = Field(default_factory=list)
    removed_lines: List[LineChange] = Field(default_factory=list)
    changed_line_numbers: List[int] = Field(default_factory=list)
    is_binary: bool = False


# Regex pattern to parse standard unified diff hunk headers: @@ -10,5 +10,7 @@
HUNK_HEADER_REGEX = re.compile(
    r"^@@\s+-(\d+)(?:,(\d+))?\s+\+(\d+)(?:,(\d+))?\s+@@(.*)"
)


class DiffParser:
    """
    Service for parsing unified GitHub patch strings into structured diff objects.
    """

    @staticmethod
    def parse_patch(patch_str: Optional[str], file_path: Optional[str] = None) -> ParsedDiff:
        """
        Parses a unified patch string into a structured ParsedDiff model.

        :param patch_str: Unified diff/patch string from GitHub API.
        :param file_path: Optional filename associated with the patch.
        :return: ParsedDiff containing hunks, line changes, and metadata.
        """
        if not patch_str or not patch_str.strip():
            return ParsedDiff(file_path=file_path)

        # Check for binary file markers
        if "Binary files " in patch_str or "GIT binary patch" in patch_str:
            return ParsedDiff(file_path=file_path, is_binary=True)

        lines = patch_str.splitlines()
        hunks: List[DiffHunk] = []
        added_lines: List[LineChange] = []
        removed_lines: List[LineChange] = []
        changed_line_numbers: List[int] = []

        current_hunk: Optional[DiffHunk] = None
        current_old_line = 0
        current_new_line = 0

        parsed_old_path: Optional[str] = None
        parsed_new_path: Optional[str] = file_path

        for line in lines:
            # Check for header file paths if present
            if line.startswith("--- "):
                parsed_old_path = line[4:].strip().lstrip("a/")
                continue
            elif line.startswith("+++ "):
                parsed_new_path = line[4:].strip().lstrip("b/")
                continue

            # Check for hunk header
            hunk_match = HUNK_HEADER_REGEX.match(line)
            if hunk_match:
                old_start = int(hunk_match.group(1))
                old_count = int(hunk_match.group(2)) if hunk_match.group(2) is not None else 1
                new_start = int(hunk_match.group(3))
                new_count = int(hunk_match.group(4)) if hunk_match.group(4) is not None else 1

                current_hunk = DiffHunk(
                    header=line,
                    old_start=old_start,
                    old_lines_count=old_count,
                    new_start=new_start,
                    new_lines_count=new_count,
                    lines=[]
                )
                hunks.append(current_hunk)
                current_old_line = old_start
                current_new_line = new_start
                continue

            # If we haven't encountered a hunk header yet, skip file header metadata
            if current_hunk is None:
                continue

            # Process diff line within current hunk
            if line.startswith("+") and not line.startswith("+++"):
                content = line[1:]
                hunk_line = HunkLine(
                    type="add",
                    new_line_number=current_new_line,
                    content=content
                )
                current_hunk.lines.append(hunk_line)
                added_lines.append(LineChange(line_number=current_new_line, content=content))
                changed_line_numbers.append(current_new_line)
                current_new_line += 1

            elif line.startswith("-") and not line.startswith("---"):
                content = line[1:]
                hunk_line = HunkLine(
                    type="delete",
                    old_line_number=current_old_line,
                    content=content
                )
                current_hunk.lines.append(hunk_line)
                removed_lines.append(LineChange(line_number=current_old_line, content=content))
                current_old_line += 1

            elif line.startswith("\\"):
                # Handle "\ No newline at end of file"
                continue

            else:
                # Context line (starts with space or empty space)
                content = line[1:] if line.startswith(" ") else line
                hunk_line = HunkLine(
                    type="context",
                    old_line_number=current_old_line,
                    new_line_number=current_new_line,
                    content=content
                )
                current_hunk.lines.append(hunk_line)
                current_old_line += 1
                current_new_line += 1

        return ParsedDiff(
            file_path=parsed_new_path or file_path,
            old_file_path=parsed_old_path,
            hunks=hunks,
            added_lines=added_lines,
            removed_lines=removed_lines,
            changed_line_numbers=changed_line_numbers,
            is_binary=False
        )
