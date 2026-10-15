

def _load_env() -> None:
    """Read the git-ignored .env at the repo root (Azure credentials), without overriding variables already set."""
    from pathlib import Path

    try:
        from dotenv import load_dotenv
    except ImportError:
        return
    load_dotenv(Path(__file__).resolve().parents[1] / ".env", override=False)


_load_env()
