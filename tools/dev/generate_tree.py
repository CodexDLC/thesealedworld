from pathlib import Path

from codex_core.dev.project_tree import ProjectTreeGenerator

if __name__ == "__main__":
    # Initialize from project root
    ProjectTreeGenerator(Path(__file__).parent.parent.parent).interactive()
