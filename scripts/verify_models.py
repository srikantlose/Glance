"""lists available Gemini models and picks the flash/pro/embedding ids per the
pinned selection rule. run once on day 1, then copy the printed values into .env."""

import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "backend"))

from google import genai  # noqa: E402

from app.config import settings  # noqa: E402

EXCLUDE = ("preview", "exp", "lite", "1.5", "1.0", "image", "tts", "live", "thinking")
FLASH_RE = re.compile(r"^models/gemini-(\d+\.\d+)-flash$")
PRO_RE = re.compile(r"^models/gemini-(\d+\.\d+)-pro$")


def _clean(names: list[str]) -> list[str]:
    return [n for n in names if not any(bad in n for bad in EXCLUDE)]


def _pick_best(names: list[str], pattern: re.Pattern) -> str | None:
    candidates = [(float(m.group(1)), n) for n in names if (m := pattern.match(n))]
    if not candidates:
        return None
    candidates.sort(key=lambda t: t[0], reverse=True)
    return candidates[0][1]


def main() -> None:
    client = genai.Client(api_key=settings.GEMINI_API_KEY)
    all_names = [m.name for m in client.models.list()]
    clean_names = _clean(all_names)

    flash = _pick_best(clean_names, FLASH_RE)
    pro = _pick_best(clean_names, PRO_RE)

    if "models/gemini-embedding-001" in all_names:
        embed = "models/gemini-embedding-001"
    else:
        embed_candidates = [n for n in clean_names if "embedding" in n]
        embed = embed_candidates[0] if embed_candidates else None

    for label, model_id in (("flash", flash), ("pro", pro), ("embed", embed)):
        if model_id and "1.5" in model_id:
            print(f"ABORT: chosen {label} model {model_id} contains '1.5' -- wrong id per spec")
            sys.exit(1)

    flash_bare = flash.replace("models/", "") if flash else None
    pro_bare = pro.replace("models/", "") if pro else None
    embed_bare = embed.replace("models/", "") if embed else None

    print(f"GEMINI_FLASH_MODEL={flash_bare or 'NOT FOUND'}")
    print(f"GEMINI_PRO_MODEL={pro_bare or 'NOT FOUND'}")
    print(f"GEMINI_EMBED_MODEL={embed_bare or 'NOT FOUND'}")

    if embed_bare:
        resp = client.models.embed_content(model=embed_bare, contents=["dimension probe"])
        print(f"EMBED_DIM={len(resp.embeddings[0].values)}")

    print("\nall available models:")
    for n in all_names:
        print(f"  {n}")


if __name__ == "__main__":
    main()
