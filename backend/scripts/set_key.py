from __future__ import annotations

import re
import sys
from getpass import getpass
from pathlib import Path

ENV = Path(__file__).resolve().parents[1] / ".env"

SHAPES = {
    "GROQ_API_KEY": (r"^gsk_[A-Za-z0-9]{40,}$", "should start with gsk_ and be ~56 characters"),
    "GEMINI_API_KEY": (r"^[A-Za-z0-9_.\-]{30,}$", "should be a long alphanumeric string"),
    "JWT_SECRET": (r"^.{32,}$", "should be at least 32 characters"),
}


def mask(v: str) -> str:
    return f"{v[:6]}…{v[-4:]}  ({len(v)} chars)" if len(v) > 14 else "…"


def main() -> int:
    if len(sys.argv) != 2 or sys.argv[1] not in SHAPES:
        print(f"usage: python scripts/set_key.py [{' | '.join(SHAPES)}]")
        return 2
    name = sys.argv[1]

    if not ENV.exists():
        print(f"{ENV} does not exist — copy .env.example to .env first")
        return 1

    value = getpass(f"Paste {name} (it will stay hidden as you type/paste, then press Enter): ").strip()
    if not value:
        print("nothing entered; no change made")
        return 1

    pattern, hint = SHAPES[name]
    if not re.match(pattern, value):
        print(f"\nThat does not look like a {name} — it {hint}.")
        print("Nothing was written. Check you copied the whole key and try again.")
        return 1

    text = ENV.read_text()
    if re.search(rf"^{name}=", text, re.M):
        text = re.sub(rf"^{name}=.*$", f"{name}={value}", text, flags=re.M)
    else:
        text = text.rstrip("\n") + f"\n{name}={value}\n"
    ENV.write_text(text)

    print(f"\nSaved {name} to backend/.env  ->  {mask(value)}")
    print("The value was never displayed and is not in your shell history.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
