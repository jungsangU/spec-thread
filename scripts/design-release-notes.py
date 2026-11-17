"""Print the nonempty CHANGELOG entry matching an existing design tag."""

import re
import sys
from pathlib import Path


def release_notes(changelog, tag):
    match = re.fullmatch(r"design-v((?:0|[1-9][0-9]*)\.(?:0|[1-9][0-9]*))", tag)
    if not match:
        raise ValueError("Expected a design-vX.Y tag")
    sections = re.split(r"(?m)^##[ \t]+([^\n]+)\n", changelog)
    entries = [
        content.strip()
        for title, content in zip(sections[1::2], sections[2::2])
        if title.strip() == match[1]
    ]
    if len(entries) != 1 or not entries[0]:
        raise ValueError(f"Expected one nonempty entry for design {match[1]}")
    return entries[0]


if __name__ == "__main__":
    try:
        print(release_notes(Path("CHANGELOG.md").read_text(encoding="utf-8"), sys.argv[1]))
    except (IndexError, OSError, ValueError) as error:
        sys.exit(str(error))
