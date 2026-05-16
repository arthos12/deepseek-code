"""Skill loader — scan and load SKILL.md files on demand."""

from pathlib import Path


class SkillManager:
    def __init__(self, skills_dir: str):
        self.skills_dir = Path(skills_dir)

    def list_skills(self) -> list[str]:
        """Return list of skill names found."""
        if not self.skills_dir.is_dir():
            return []
        names = []
        for md in self.skills_dir.glob("**/SKILL.md"):
            name = md.parent.name if md.parent != self.skills_dir else "root"
            names.append(name)
        return sorted(names)

    def get_descriptions(self) -> str:
        """Return compact skill listing for inclusion in system prompt."""
        if not self.skills_dir.is_dir():
            return ""
        lines = []
        for md in sorted(self.skills_dir.glob("**/SKILL.md")):
            try:
                with open(md, encoding="utf-8") as f:
                    first = f.readline().strip().lstrip("#").strip()
                name = md.parent.name if md.parent != self.skills_dir else md.stem
                lines.append(f"- {name}: {first}")
            except Exception:
                pass
        return "\n".join(lines)

    def load_skill(self, name: str) -> str | None:
        """Load full SKILL.md content by skill name."""
        if not self.skills_dir.is_dir():
            return None
        for md in self.skills_dir.glob("**/SKILL.md"):
            dir_name = md.parent.name if md.parent != self.skills_dir else "root"
            if dir_name == name:
                try:
                    return md.read_text(encoding="utf-8")
                except Exception:
                    return None
        return None
