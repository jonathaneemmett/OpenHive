from pathlib import Path

from openhive.skills.loader import discover_skills, parse_skill_md

FIXTURES_DIR = Path(__file__).parent / "fixtures" / "skills"


def _write_skill(tmp_path: Path, name: str, content: str) -> Path:
    skill_dir = tmp_path / name
    skill_dir.mkdir(parents=True)
    skill_file = skill_dir / "SKILL.md"
    skill_file.write_text(content)
    return skill_file


def test_parse_skill_md_valid(tmp_path: Path) -> None:
    content = (
        "---\n"
        "name: test-skill\n"
        "description: A test skill.\n"
        "---\n"
        "\n"
        "# Instructions\n"
        "\n"
        "Do the thing.\n"
    )
    path = _write_skill(tmp_path, "test-skill", content)
    skill = parse_skill_md(path)
    assert skill is not None
    assert skill.name == "test-skill"
    assert skill.description == "A test skill."
    assert "Do the thing." in skill.instructions


def test_parse_skill_md_no_frontmatter(tmp_path: Path) -> None:
    content = "# Just markdown\n\nNo frontmatter here.\n"
    path = _write_skill(tmp_path, "no-front", content)
    skill = parse_skill_md(path)
    assert skill is None


def test_parse_skill_md_missing_name_uses_dir(tmp_path: Path) -> None:
    content = "---\ndescription: No name field.\n---\n\nInstructions.\n"
    path = _write_skill(tmp_path, "fallback-name", content)
    skill = parse_skill_md(path)
    assert skill is not None
    assert skill.name == "fallback-name"


def test_discover_skills_from_directory(tmp_path: Path) -> None:
    content_a = (
        "---\nname: alpha\ndescription: Alpha skill.\n---\n\nAlpha instructions.\n"
    )
    content_b = "---\nname: beta\ndescription: Beta skill.\n---\n\nBeta instructions.\n"
    _write_skill(tmp_path, "alpha", content_a)
    _write_skill(tmp_path, "beta", content_b)

    skills = discover_skills(extra_dirs=[tmp_path])
    names = {s.name for s in skills}
    assert "alpha" in names
    assert "beta" in names


def test_discover_skills_priority(tmp_path: Path) -> None:
    high = tmp_path / "high"
    low = tmp_path / "low"

    content_high = "---\nname: dupe\ndescription: High priority.\n---\n\nHigh.\n"
    content_low = "---\nname: dupe\ndescription: Low priority.\n---\n\nLow.\n"

    high.mkdir()
    low.mkdir()
    _write_skill(high, "dupe", content_high)
    _write_skill(low, "dupe", content_low)

    skills = discover_skills(extra_dirs=[high, low])
    dupes = [s for s in skills if s.name == "dupe"]
    assert len(dupes) == 1
    assert dupes[0].description == "High priority."


def test_discover_skills_empty_directory(tmp_path: Path) -> None:
    skills = discover_skills(extra_dirs=[tmp_path])
    # May include skills from ~/.openhive/skills if they exist,
    # but at minimum should not crash
    assert isinstance(skills, list)
