"""NUL-safe Git inventory and read-only worktree/index content access."""

from __future__ import annotations

import os
from pathlib import Path
import stat
import subprocess

from .policy import PolicyError, display, relative_path


class Repository:
    def __init__(self, root: Path, staged: bool):
        self.root = root.resolve()
        self.staged = staged
        top = self.git("rev-parse", "--show-toplevel").rstrip(b"\n")
        if Path(os.fsdecode(top)).resolve() != self.root:
            raise PolicyError("--root must name the Git repository root")
        self.index_raw = self.git("ls-files", "--stage", "-z")
        self.entries = {}
        for record in self.index_raw.split(b"\0"):
            if not record:
                continue
            metadata, path_raw = record.split(b"\t", 1)
            mode, oid, stage = metadata.decode("ascii").split()
            if stage != "0":
                raise PolicyError("Git index has unresolved merge entries; resolve and stage them before checking")
            self.entries[os.fsdecode(path_raw)] = (mode, oid)
        changed_raw = self.git("diff", "--cached", "--name-only", "--no-renames", "-z", "--")
        self.changed = set(self.names(changed_raw))
        self.paths = set(self.entries)
        if not staged:
            self.paths.update(self.names(self.git("ls-files", "--others", "--exclude-standard", "-z")))

    def git(self, *args: str) -> bytes:
        try:
            process = subprocess.run(["git", "-C", str(self.root), *args], capture_output=True,
                                     env={**os.environ, "GIT_OPTIONAL_LOCKS": "0"})
        except OSError as error:
            raise PolicyError("cannot run Git; install Git and check --root") from error
        if process.returncode:
            raise PolicyError(f"Git {args[0]} failed; check repository access and index/object availability")
        return process.stdout

    @staticmethod
    def names(raw: bytes) -> list[str]:
        return [os.fsdecode(name) for name in raw.split(b"\0") if name]

    def read(self, path: str) -> bytes:
        relative_path(path)
        if self.staged:
            if path not in self.entries:
                raise PolicyError(f"file {display(path)} is absent from the index; stage it before checking")
            mode, oid = self.entries[path]
            if mode not in ("100644", "100755"):
                raise PolicyError(f"selected path {display(path)} is a symlink or submodule; explicitly exclude it with a reason")
            return self.git("cat-file", "blob", oid)
        # Never follow selected symlinks, including directory components.
        target = self.root
        try:
            for part in path.split("/"):
                target /= part
                if target.is_symlink():
                    raise PolicyError(f"selected path {display(path)} uses a symlink; explicitly exclude it with a reason")
            mode = target.stat().st_mode
            if not stat.S_ISREG(mode):
                raise PolicyError(f"selected path {display(path)} is not a regular file; explicitly exclude submodules/generated content")
            return target.read_bytes()
        except OSError as error:
            raise PolicyError(f"cannot read selected file {display(path)}: {type(error).__name__}; restore it or correct the policy") from error

    def verify_index(self) -> None:
        if self.staged and self.git("ls-files", "--stage", "-z") != self.index_raw:
            raise PolicyError("Git index changed during checking; rerun on a stable index")
