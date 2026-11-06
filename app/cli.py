import argparse
import asyncio
import sys
from datetime import UTC

from sqlalchemy import select

from app.config import get_settings
from app.database import SessionLocal
from app.models import User
from app.services import as_utc, reclassify_contests
from app.sync import add_user, sync_archive, sync_user


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="atcoder-participations")
    groups = parser.add_subparsers(dest="group", required=True)

    users = groups.add_parser("users")
    user_commands = users.add_subparsers(dest="command", required=True)
    for command in ("add", "delete", "sync"):
        command_parser = user_commands.add_parser(command)
        command_parser.add_argument("username")
    user_commands.add_parser("list")
    user_commands.add_parser("sync-all")

    contests = groups.add_parser("contests")
    contest_commands = contests.add_subparsers(dest="command", required=True)
    contest_commands.add_parser("sync")
    contest_commands.add_parser("reclassify")
    return parser


async def _run(args: argparse.Namespace) -> None:
    settings = get_settings()
    if args.group == "contests" and args.command == "sync":
        print(f"Synced {await sync_archive(settings)} contests")
        return
    if args.group == "contests" and args.command == "reclassify":
        with SessionLocal.begin() as session:
            changed = reclassify_contests(session)
        print(f"Reclassified {changed} contests")
        return
    if args.command == "add":
        print(f"Registered {args.username} with {await add_user(args.username, settings)} entries")
        return
    if args.command == "delete":
        with SessionLocal.begin() as session:
            user = session.get(User, args.username)
            if user is None:
                raise LookupError(f"User is not registered: {args.username}")
            session.delete(user)
        print(f"Deleted {args.username}")
        return
    if args.command == "sync":
        print(f"Synced {await sync_user(args.username, settings)} entries for {args.username}")
        return
    if args.command == "sync-all":
        with SessionLocal() as session:
            usernames = session.scalars(select(User.username).order_by(User.username)).all()
        for username in usernames:
            print(f"Synced {await sync_user(username, settings)} entries for {username}")
        return
    if args.command == "list":
        with SessionLocal() as session:
            users = session.scalars(select(User).order_by(User.username)).all()
            for user in users:
                last_sync = as_utc(user.last_synced_at)
                next_sync = as_utc(user.next_sync_at)
                last_display = last_sync.astimezone(UTC).isoformat() if last_sync else "-"
                next_display = next_sync.astimezone(UTC).isoformat() if next_sync else "-"
                print(
                    f"{user.username}\tlast={last_display}"
                    f"\tnext={next_display}"
                    f"\terror={user.last_sync_error or '-'}"
                )


def main() -> None:
    try:
        asyncio.run(_run(_build_parser().parse_args()))
    except (LookupError, ValueError, RuntimeError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        raise SystemExit(1) from exc


if __name__ == "__main__":
    main()
