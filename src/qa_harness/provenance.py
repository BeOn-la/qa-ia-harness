from __future__ import annotations

import subprocess
from pathlib import Path
import importlib.resources
from .common import ContractError, fingerprint, file_hash
from . import __version__


def git(root, *args, check=True):
    process = subprocess.run(["git", "-C", str(root), *args], capture_output=True, timeout=30)
    if check and process.returncode:
        raise ContractError("Git no pudo identificar el checkout; verificar permisos y repositorio")
    return process


def snapshot(root):
    root = Path(root).resolve()
    git_root = Path(git(root, "rev-parse", "--show-toplevel").stdout.decode().strip()).resolve()
    head = git(root, "rev-parse", "--verify", "HEAD", check=False)
    commit = head.stdout.decode().strip() if head.returncode == 0 else None
    listing = git(git_root, "ls-files", "--cached", "--others", "--exclude-standard", "-z").stdout
    files = {}
    for raw in listing.split(b"\0"):
        if not raw:
            continue
        name = raw.decode("utf-8")
        path = git_root / name
        if ".qa-runs" in Path(name).parts:
            tracked = git(git_root, "ls-files", "--error-unmatch", "--", name, check=False)
            if tracked.returncode == 0:
                raise ContractError("Los artefactos .qa-runs no deben versionarse")
            continue
        if not path.resolve().is_relative_to(git_root):
            raise ContractError("Archivo del checkout enlazado fuera del repositorio")
        if path.is_file():
            files[name] = file_hash(path)
    dirty = bool(git(git_root, "status", "--porcelain", "--untracked-files=all").stdout.strip())
    return {"git_root": str(git_root), "commit": commit, "dirty": dirty or commit is None,
            "files": files, "tree_sha256": fingerprint(files)}


def harness_identity():
    package = Path(__file__).resolve().parent
    files = {p.name: file_hash(p) for p in package.glob("*.py")}
    for p in importlib.resources.files("qa_harness.schemas").iterdir():
        if p.name.endswith(".json"):
            from .common import digest
            files["schemas/" + p.name] = digest(p.read_bytes())
    head = git(package, "rev-parse", "--verify", "HEAD", check=False)
    return {"version": __version__, "source_sha256": fingerprint(files),
            "commit": head.stdout.decode().strip() if head.returncode == 0 else None}
