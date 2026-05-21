#!/usr/bin/env python
"""
Management script for the tg_bot project.
"""

import os
import sys

from codex_bot.cli.management import execute_from_command_line


def main() -> None:
    """Run administrative tasks."""
    os.environ.setdefault("CODEX_BOT_PROJECT", "tg_bot")
    execute_from_command_line(sys.argv)


if __name__ == "__main__":
    main()
