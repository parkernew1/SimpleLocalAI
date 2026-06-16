from __future__ import annotations

import argparse
import sys

from .app import ChatApp
from .doctor import run_doctor


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="simplelocalai")
    subparsers = parser.add_subparsers(dest="command")

    chat = subparsers.add_parser("chat", help="start the terminal chat UI")
    chat.add_argument("--config", help="path to a config JSON file")

    doctor = subparsers.add_parser("doctor", help="check local model readiness")
    doctor.add_argument("--config", help="path to a config JSON file")

    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    if args.command == "doctor":
        return run_doctor(args.config)

    if args.command in (None, "chat"):
        try:
            ChatApp(config_path=args.config).run()
        except KeyboardInterrupt:
            print("\nbye")
        return 0

    parser.print_help()
    return 2


if __name__ == "__main__":
    sys.exit(main())

