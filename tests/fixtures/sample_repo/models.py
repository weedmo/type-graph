from dataclasses import dataclass


@dataclass
class User:
    """A user record."""
    id: int
    name: str


def normalize_name(name: str) -> str:
    """Lowercase and strip a name."""
    return name.strip().lower()
