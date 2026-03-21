"""Data models for remote app launcher."""

from dataclasses import dataclass


@dataclass
class App:
    """Represents a launchable desktop application."""

    name: str
    desktop_id: str
    desktop_path: str
    icon: str = ""
    categories: str = ""

    def to_dict(self) -> dict:
        return {
            "name": self.name,
            "desktop_id": self.desktop_id,
            "desktop_path": self.desktop_path,
            "icon": self.icon,
            "categories": self.categories,
        }

    @classmethod
    def from_dict(cls, d: dict) -> "App":
        return cls(
            name=d.get("name", ""),
            desktop_id=d.get("desktop_id", ""),
            desktop_path=d.get("desktop_path", ""),
            icon=d.get("icon", ""),
            categories=d.get("categories", ""),
        )

    def fzf_line(self, delimiter: str = " | ") -> str:
        cats = self.categories.replace(";", ", ").strip(", ") if self.categories else ""
        return f"{self.name}{delimiter}{cats}{delimiter}{self.desktop_id}"
