import asyncio
import sys

from app.checker import check_and_notify
from app.config import get_settings


def main() -> None:
    try:
        notified = asyncio.run(check_and_notify(get_settings()))
        print("No qualifying participation; webhooks sent" if notified else "Participation found")
    except (ValueError, RuntimeError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        raise SystemExit(1) from exc


if __name__ == "__main__":
    main()
