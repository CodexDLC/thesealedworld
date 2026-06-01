import sys
from pathlib import Path

# Project root
ROOT = Path(__file__).resolve().parents[2]

# Add codex-core to path if it's in the codex_tools library folder
LIB_PATH = Path("C:/install/projects/codex_tools/codex-core/src")
if LIB_PATH.exists() and str(LIB_PATH) not in sys.path:
    sys.path.insert(0, str(LIB_PATH))

try:
    from codex_core.dev.check_runner import BaseCheckRunner
except ImportError:
    print("Error: Could not find codex_core.dev.check_runner.")
    print("Ensure C:/install/projects/codex_tools/codex-core is available.")
    sys.exit(1)


class TurnBasedMMORPGCheckRunner(BaseCheckRunner):
    """Custom project runner inheriting from codex-core BaseCheckRunner."""

    def extra_checks(self) -> bool:
        """Run project-specific validators and documentation build."""
        self.print_step("Fixture Validators")
        success, _ = self.run_command([sys.executable, "tools/validators/run.py"])
        if not success:
            self.print_error("Fixture validation failed.")
            return False
        self.print_success("Fixture validation passed.")

        self.print_step("Documentation Build")
        success, _ = self.run_command(["uv", "run", "--group", "docs", "mkdocs", "build", "--clean"])
        if not success:
            self.print_error("Documentation build failed.")
            return False
        self.print_success("Documentation build passed.")

        # Call parent to handle declarative extra commands from pyproject.toml
        return super().extra_checks()


if __name__ == "__main__":
    runner = TurnBasedMMORPGCheckRunner(ROOT)
    runner.main()
