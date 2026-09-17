#!/usr/bin/env python3
"""Create a new, local-only Telethon workspace without writing credentials."""

from __future__ import annotations

import argparse
from pathlib import Path


FILES = {
    ".gitignore": """.env
.venv/
*.session
*.session-journal
tg_login_qr.png
__pycache__/
""",
    ".env.example": """# Copy this file to .env and fill values locally. Do not share the completed file.
TELEGRAM_API_ID=your_numeric_api_id
TELEGRAM_API_HASH=your_secret_api_hash
""",
    "requirements.txt": """telethon>=1.45,<2
qrcode[pil]>=8,<9
""",
    "scripts/_config.py": r'''"""Load the two Telegram API credentials from process env or a local .env file."""

import os
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def credentials() -> tuple[int, str]:
    values = {
        "TELEGRAM_API_ID": os.environ.get("TELEGRAM_API_ID", ""),
        "TELEGRAM_API_HASH": os.environ.get("TELEGRAM_API_HASH", ""),
    }
    env_path = ROOT / ".env"
    if env_path.exists():
        for raw_line in env_path.read_text(encoding="utf-8").splitlines():
            line = raw_line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, value = line.split("=", 1)
            key = key.strip()
            if key in values and not values[key]:
                values[key] = value.strip().strip('"').strip("'")

    try:
        api_id = int(values["TELEGRAM_API_ID"])
    except ValueError as error:
        raise SystemExit("Missing or invalid TELEGRAM_API_ID in the local .env file.") from error
    api_hash = values["TELEGRAM_API_HASH"]
    if not api_hash or api_hash == "your_secret_api_hash":
        raise SystemExit("Missing or invalid TELEGRAM_API_HASH in the local .env file.")
    return api_id, api_hash
''',
    "scripts/qr_login.py": r'''"""Authorize a local Telethon session using a QR code; never prints secrets."""

import argparse
import asyncio
import getpass
import subprocess
import sys

import qrcode
from telethon import TelegramClient
from telethon.errors import SessionPasswordNeededError

from _config import ROOT, credentials

SESSION = ROOT / "telegram"
QR_IMAGE = ROOT / "tg_login_qr.png"


def focus_terminal() -> None:
    if sys.platform == "darwin":
        subprocess.run(
            ["osascript", "-e", 'tell application "Terminal" to activate'],
            check=False,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )


async def main(focus_on_2fa: bool) -> None:
    api_id, api_hash = credentials()
    client = TelegramClient(str(SESSION), api_id, api_hash)
    await client.connect()
    try:
        if await client.is_user_authorized():
            print("A local Telegram session already exists. Nothing was changed.")
            return
        login = await client.qr_login()
        qrcode.make(login.url).save(QR_IMAGE)
        print("Open tg_login_qr.png and scan it in Telegram: Settings → Devices → Link Desktop Device.")
        try:
            await login.wait()
        except SessionPasswordNeededError:
            if focus_on_2fa:
                focus_terminal()
            password = getpass.getpass("Telegram 2FA password (local input): ")
            await client.sign_in(password=password)
        except TimeoutError as error:
            raise SystemExit("QR expired. Run this script again for a fresh QR.") from error
        print("Authorization succeeded. telegram.session stays local; do not copy or commit it.")
    finally:
        await client.disconnect()


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--focus-terminal-on-2fa", action="store_true")
    args = parser.parse_args()
    asyncio.run(main(args.focus_terminal_on_2fa))
''',
    "scripts/launch_qr_login_macos.py": r'''"""Launch QR login in a user-visible macOS Terminal for secure 2FA input."""

import json
import shlex
import subprocess
import sys

from _config import ROOT


def main() -> None:
    if sys.platform != "darwin":
        raise SystemExit("This launcher is only for macOS. Run qr_login.py in your visible terminal.")
    python = ROOT / ".venv" / "bin" / "python"
    login_script = ROOT / "scripts" / "qr_login.py"
    command = (
        f"cd {shlex.quote(str(ROOT))} && "
        f"exec {shlex.quote(str(python))} {shlex.quote(str(login_script))} --focus-terminal-on-2fa"
    )
    apple_script = (
        'tell application "Terminal"\n'
        "activate\n"
        f"do script {json.dumps(command)}\n"
        "end tell"
    )
    subprocess.run(["osascript", "-e", apple_script], check=True)


if __name__ == "__main__":
    main()
''',
    "scripts/code_login.py": r'''"""Authorize a local Telethon session using Telegram's selected code-delivery path."""

import asyncio
import getpass

from telethon import TelegramClient
from telethon.errors import SessionPasswordNeededError

from _config import ROOT, credentials

SESSION = ROOT / "telegram"


async def main() -> None:
    api_id, api_hash = credentials()
    client = TelegramClient(str(SESSION), api_id, api_hash)
    await client.connect()
    try:
        if await client.is_user_authorized():
            print("A local Telegram session already exists. Nothing was changed.")
            return
        phone = input("Phone number in international format: ").strip()
        sent = await client.send_code_request(phone)
        delivery = type(sent.type).__name__.removeprefix("SentCodeType")
        print(f"Telegram requested a {delivery} code. Follow the delivery path Telegram selected.")
        code = input("Telegram login code (local input): ").strip()
        try:
            await client.sign_in(phone=phone, code=code, phone_code_hash=sent.phone_code_hash)
        except SessionPasswordNeededError:
            password = getpass.getpass("Telegram 2FA password (local input): ")
            await client.sign_in(password=password)
        print("Authorization succeeded. telegram.session stays local; do not copy or commit it.")
    finally:
        await client.disconnect()


if __name__ == "__main__":
    asyncio.run(main())
''',
    "scripts/check_readonly.py": r'''"""Verify a local session without sending, editing, or deleting Telegram data."""

import argparse
import asyncio

from telethon import TelegramClient

from _config import ROOT, credentials

SESSION = ROOT / "telegram"


async def main(show_dialogs: bool) -> None:
    api_id, api_hash = credentials()
    client = TelegramClient(str(SESSION), api_id, api_hash)
    await client.connect()
    try:
        if not await client.is_user_authorized():
            raise SystemExit("No authorized local session found. Run a login script first.")
        me = await client.get_me()
        print(f"Connected as: {me.first_name or 'Telegram user'} (phone and ID hidden)")
        if show_dialogs:
            print("Recent dialog names (read-only):")
            async for dialog in client.iter_dialogs(limit=5):
                print(f"- {dialog.name}")
    finally:
        await client.disconnect()


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--dialogs", action="store_true", help="Show up to five dialog names after explicit consent.")
    args = parser.parse_args()
    asyncio.run(main(args.dialogs))
''',
    "scripts/telegram_readonly.py": r'''"""Read selected Telegram data through a local session; never sends or edits messages."""

import argparse
import asyncio

from telethon import TelegramClient

from _config import ROOT, credentials

SESSION = ROOT / "telegram"


async def resolve_chat(client: TelegramClient, locator: str):
    if locator.startswith("@") or locator.lstrip("-").isdigit():
        return await client.get_entity(locator)
    matches = []
    async for dialog in client.iter_dialogs():
        if dialog.name.casefold() == locator.casefold():
            matches.append(dialog.entity)
    if not matches:
        raise SystemExit("Chat not found by exact name. Run `dialogs` first or use @username / numeric ID.")
    if len(matches) > 1:
        raise SystemExit("Several chats have this name. Use @username or numeric ID to disambiguate.")
    return matches[0]


def clean_text(text: str | None) -> str:
    return " ".join((text or "").split())[:2000] or "[no text]"


async def run(args: argparse.Namespace) -> None:
    api_id, api_hash = credentials()
    client = TelegramClient(str(SESSION), api_id, api_hash)
    await client.connect()
    try:
        if not await client.is_user_authorized():
            raise SystemExit("No authorized local session found. Run a login script first.")
        if args.command == "dialogs":
            async for dialog in client.iter_dialogs(limit=args.limit):
                print(dialog.name)
            return

        entity = await resolve_chat(client, args.chat)
        if args.command == "recent":
            messages = client.iter_messages(entity, limit=args.limit)
        else:
            messages = client.iter_messages(entity, search=args.query, limit=args.limit)
        async for message in messages:
            timestamp = message.date.astimezone().isoformat(timespec="minutes")
            print(f"[{timestamp}] {clean_text(message.text)}")
    finally:
        await client.disconnect()


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="command", required=True)
    dialogs = subparsers.add_parser("dialogs", help="List dialog names only")
    dialogs.add_argument("--limit", type=int, default=20, choices=range(1, 101))
    for name, help_text in (("recent", "Read recent messages"), ("search", "Search messages")):
        command = subparsers.add_parser(name, help=help_text)
        command.add_argument("--chat", required=True, help="Exact chat title, @username, or numeric ID")
        command.add_argument("--limit", type=int, default=20, choices=range(1, 101))
        if name == "search":
            command.add_argument("--query", required=True)
    args = parser.parse_args()
    asyncio.run(run(args))


if __name__ == "__main__":
    main()
''',
}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--target", required=True, help="New empty folder for the local Telegram project")
    args = parser.parse_args()
    target = Path(args.target).expanduser().resolve()

    if target.exists() and any(target.iterdir()):
        raise SystemExit(f"Refusing to overwrite non-empty folder: {target}")
    target.mkdir(parents=True, exist_ok=True)

    for relative, content in FILES.items():
        destination = target / relative
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_text(content, encoding="utf-8")

    print(f"Created local Telethon workspace: {target}")
    print("Next: copy .env.example to .env and fill it yourself; do not share .env or telegram.session.")


if __name__ == "__main__":
    main()
