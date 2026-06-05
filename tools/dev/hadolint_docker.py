from __future__ import annotations

import subprocess
import sys
from pathlib import Path


def main(argv: list[str]) -> int:
    files = [Path(arg) for arg in argv if Path(arg).is_file()]
    if not files:
        return 0

    docker = subprocess.run(
        ["docker", "info", "--format", "{{.ServerVersion}}"],
        capture_output=True,
        text=True,
    )
    if docker.returncode != 0:
        print("Docker daemon is unavailable; skipping hadolint Dockerfile lint.", file=sys.stderr)
        if docker.stderr.strip():
            print(docker.stderr.strip(), file=sys.stderr)
        return 0

    failed = False
    for dockerfile in files:
        result = subprocess.run(
            [
                "docker",
                "run",
                "--rm",
                "-i",
                "hadolint/hadolint:latest",
                "hadolint",
                "--failure-threshold",
                "error",
                "-",
            ],
            input=dockerfile.read_bytes(),
            capture_output=True,
        )
        if result.stdout:
            sys.stdout.buffer.write(result.stdout)
        if result.stderr:
            sys.stderr.buffer.write(result.stderr)
        if result.returncode != 0:
            print(f"hadolint failed for {dockerfile}", file=sys.stderr)
            failed = True

    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
