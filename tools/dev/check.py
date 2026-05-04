import os
import sys
import subprocess
from pathlib import Path

def run_step(name: str, command: str, cwd: Path) -> bool:
    print(f"\n{'='*20} {name} {'='*20}")
    # capture_output=False ensures everything goes to terminal
    result = subprocess.run(command, shell=True, cwd=cwd)
    if result.returncode != 0:
        print(f"\n❌ {name} failed.")
        return False
    print(f"\n✅ {name} passed.")
    return True

if __name__ == "__main__":
    os.system("cls" if os.name == "nt" else "clear")
    print("=== TurnBasedMMORPG Quality Gate ===")

    root = Path(__file__).parent.parent.parent

    steps = [
        ("Quality Hooks", "uv run pre-commit run --all-files"),
        ("Types (Mypy)", "uv run mypy --explicit-package-bases src tools"),
        ("Security Audit", "uv run pip-audit --skip-editable --ignore-vuln CVE-2026-3219"),
        ("Fixture Validators", "uv run python tools/validators/run.py"),
        ("Unit Tests", "uv run pytest"),
    ]

    all_success = True
    for name, cmd in steps:
        if not run_step(name, cmd, root):
            all_success = False
            if "--ci" in sys.argv:
                sys.exit(1)
            # In non-CI mode, we might want to continue or stop
            break

    if all_success:
        print("\n✨ ALL CHECKS PASSED!")
    else:
        print("\n⚠️  Gate failed. Review logs above.")
        sys.exit(1)
