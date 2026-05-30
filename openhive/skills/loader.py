"""Discover and load SKILL.md files from skill directories."""

import logging
from dataclasses import dataclass, field
from pathlib import Path

import yaml

logger = logging.getLogger(__name__)

DEFAULT_SKILL_DIRS = [
    Path.home() / ".openhive" / "skills",
]


@dataclass
class Skill:
    """A loaded skill parsed from a SKILL.md file."""

    name: str
    description: str
    instructions: str
    path: Path
    metadata: dict[str, object] = field(default_factory=dict)


def parse_skill_md(skill_path: Path) -> Skill | None:
    """Parse a SKILL.md file into a Skill object."""
    try:
        content = skill_path.read_text(encoding="utf-8")
    except OSError as e:
        logger.warning("Failed to read %s: %s", skill_path, e)
        return None

    frontmatter, body = _split_frontmatter(content)
    if frontmatter is None:
        logger.warning("No frontmatter found in %s", skill_path)
        return None

    try:
        meta: dict[str, object] = yaml.safe_load(frontmatter) or {}
    except yaml.YAMLError as e:
        logger.warning("Invalid YAML frontmatter in %s: %s", skill_path, e)
        return None

    name = meta.get("name")
    description = meta.get("description")

    if not isinstance(name, str) or not name:
        # Fall back to directory name
        name = skill_path.parent.name

    if not isinstance(description, str) or not description:
        description = f"Skill: {name}"

    return Skill(
        name=name,
        description=description,
        instructions=body.strip(),
        path=skill_path,
        metadata=meta,
    )


def _split_frontmatter(content: str) -> tuple[str | None, str]:
    """Split YAML frontmatter from markdown body."""
    stripped = content.strip()
    if not stripped.startswith("---"):
        return None, content

    end = stripped.find("---", 3)
    if end == -1:
        return None, content

    frontmatter = stripped[3:end].strip()
    body = stripped[end + 3 :]
    return frontmatter, body


def discover_skills(
    extra_dirs: list[Path] | None = None,
) -> list[Skill]:
    """Discover and load skills from all skill directories.

    Searches directories in priority order. First match for a skill
    name wins (higher priority sources shadow lower ones).
    """
    dirs = list(DEFAULT_SKILL_DIRS)
    if extra_dirs:
        dirs = extra_dirs + dirs

    seen_names: set[str] = set()
    skills: list[Skill] = []

    for skill_dir in dirs:
        if not skill_dir.is_dir():
            continue

        # Find all SKILL.md files (supports nested directories)
        for skill_path in sorted(skill_dir.rglob("SKILL.md")):
            skill = parse_skill_md(skill_path)
            if skill is None:
                continue

            if skill.name in seen_names:
                logger.debug(
                    "Skipping duplicate skill '%s' from %s",
                    skill.name,
                    skill_path,
                )
                continue

            seen_names.add(skill.name)
            skills.append(skill)
            logger.info("Loaded skill '%s' from %s", skill.name, skill_path)

    return skills
