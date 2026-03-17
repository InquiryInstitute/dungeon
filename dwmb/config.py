"""
Load environment from .env. Prefer project root; fallback to ../Inquiry.Institute for keys.
"""
from __future__ import annotations

import os
from pathlib import Path


def load_dotenv_paths() -> None:
    """Load .env from dungeon project or ../Inquiry.Institute (no extra deps)."""
    try:
        import dotenv
        dotenv.load_dotenv()
        return
    except ImportError:
        pass
    # Fallback: manual parse
    for path in _env_paths():
        if path.exists():
            _load_env_file(path)
            return


def _env_paths() -> list[Path]:
    root = Path(__file__).resolve().parent.parent
    return [
        root / ".env",
        root / ".env.local",
        root / ".." / "Inquiry.Institute" / ".env.local",
        root / ".." / "Inquiry.Institute" / ".env",
    ]


def _load_env_file(path: Path) -> None:
    with open(path) as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            if "=" in line:
                k, v = line.split("=", 1)
                k, v = k.strip(), v.strip()
                if v.startswith('"') and v.endswith('"'):
                    v = v[1:-1].replace('\\"', '"')
                elif v.startswith("'") and v.endswith("'"):
                    v = v[1:-1]
                if k and k not in os.environ:
                    os.environ[k] = v


def get_supabase_url() -> str | None:
    return os.environ.get("SUPABASE_URL") or os.environ.get("NEXT_PUBLIC_SUPABASE_URL")


def get_supabase_key() -> str | None:
    return os.environ.get("SUPABASE_SERVICE_ROLE_KEY") or os.environ.get("SUPABASE_ANON_KEY")


def get_vertex_credentials() -> dict[str, str] | None:
    """Return Vertex AI credentials if set (for LLM baseline)."""
    project = os.environ.get("VERTEX_PROJECT_ID") or os.environ.get("GCP_PROJECT_ID")
    location = os.environ.get("VERTEX_LOCATION") or os.environ.get("GCP_LOCATION", "us-central1")
    key = os.environ.get("VERTEX_SERVICE_ACCOUNT_JSON")
    if project and location:
        return {"project_id": project, "location": location, "service_account_json": key}
    return None
