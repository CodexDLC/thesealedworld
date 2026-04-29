from pathlib import Path

from codex_core.dev.check_runner import BaseCheckRunner

if __name__ == "__main__":
    # Initialize from project root
    BaseCheckRunner(Path(__file__).parent.parent.parent).main()
