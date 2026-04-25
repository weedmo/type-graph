from sample_repo.models import User, normalize_name


def make_user(uid: int, name: str) -> User:
    """Construct a User after normalizing its name."""
    return User(id=uid, name=normalize_name(name))


def greet(u: User) -> str:
    return f"hello {u.name}"
