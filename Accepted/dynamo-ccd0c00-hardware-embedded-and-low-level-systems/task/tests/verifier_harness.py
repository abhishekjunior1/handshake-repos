"""Runs the submitted pipeline on the hidden configs under a hardened sandbox.

The pipeline is agent-authored code that has to be executed at grade time (the
task is "fix the controller", so the fix can only be observed by running it on
configurations the agent never saw). Executing agent code next to the answer key
is the risk this harness removes:

  * the expected outputs are read into memory and **deleted from disk** for the
    duration of every pipeline run, so no answer key exists on the filesystem
    while agent code is executing;
  * /tests and /logs are sealed to the owner alone and the run is dropped to
    an unprivileged uid where the platform allows it, so agent code can neither
    read the fixtures nor forge the reward;
  * each graded output is captured only after a lstat-based guard that rejects
    symlinks, non-regular files, and anything that resolves outside /app.

Captured outputs and expected values are staged in a root-only directory for the
pytest modules to read; nothing is handed back to /app. That directory is wiped
and recreated first and every file in it is written O_EXCL|O_NOFOLLOW, so a
submission cannot pre-plant a link that aliases a captured output onto the
expected values it is about to be compared against.
"""

import json
import os
import shutil
import stat
import subprocess
import sys
import sysconfig
from pathlib import Path

TESTS_DIR = Path(__file__).resolve().parent
APP_DIR = Path("/app")
OUTPUT_PATH = APP_DIR / "output.json"
CONFIG_PATH = APP_DIR / "dma_config.json"
LOGS_DIR = Path("/logs")

CONFIGS = (1, 2, 3)
RUN_TIMEOUT_SEC = 30
NOBODY_UID = 65534
NOBODY_GID = 65534


def safe_remove(path: Path) -> None:
    """Delete path without following it if it is a symlink."""
    try:
        st = path.lstat()
    except FileNotFoundError:
        return
    if stat.S_ISDIR(st.st_mode):
        shutil.rmtree(path, ignore_errors=True)
    else:
        path.unlink(missing_ok=True)


def staging_candidates():
    """Ordered staging locations, most private first.

    /opt is preferred and is root-only, but the verifier is not guaranteed to
    run as root; falling back keeps a correct submission from being failed by
    an unwritable staging dir rather than by its own output.
    """
    override = os.environ.get("DMA_VERIFY_DIR")
    if override:
        return [Path(override)]
    return [Path("/opt/dma_verify"), Path.home() / ".dma_verify", Path("/tmp/.dma_verify")]


def make_staging_dir() -> Path:
    """Wipe and recreate the first staging location we can own outright."""
    last = None
    for candidate in staging_candidates():
        try:
            safe_remove(candidate)
            candidate.mkdir(parents=True)
            os.chmod(candidate, 0o700)
            return candidate
        except OSError as exc:
            last = exc
    raise RuntimeError(f"no writable staging directory: {last}")


def write_json_exclusive(path: Path, payload) -> None:
    """Write JSON to a brand-new file, never through a pre-existing symlink.

    The staging directory is wiped and recreated first, but O_EXCL|O_NOFOLLOW
    makes it impossible for anything planted here to redirect a write — in
    particular, aliasing a captured output onto its own expected file.
    """
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600)
    with os.fdopen(fd, "w") as handle:
        json.dump(payload, handle)


def find_interpreter_hooks():
    """List any sitecustomize/usercustomize modules planted in the site dirs.

    Nothing in the base image installs these, and no legitimate fix to a DMA
    controller needs one; their presence means the interpreter itself was
    tampered with, so the assertions refuse to score the run.
    """
    found = []
    for key in ("purelib", "platlib", "stdlib"):
        base = Path(sysconfig.get_paths()[key])
        for name in ("sitecustomize.py", "usercustomize.py"):
            if (base / name).exists():
                found.append(str(base / name))
    return sorted(set(found))


def chmod_quiet(path: Path, mode: int) -> bool:
    """chmod that tolerates a read-only mount. True if the mode was applied."""
    try:
        os.chmod(path, mode)
        return True
    except OSError:
        return False


def guard_output(path: Path) -> dict:
    """Return the parsed output, or raise if the path is not a real file in /app.

    Rejects the "point the answer at the reference file" exploit: a submission
    that leaves /app/output.json as a symlink (dangling during the agent run,
    resolving onto the fixtures at grade time) never gets read.
    """
    try:
        st = path.lstat()
    except FileNotFoundError:
        raise AssertionError(f"{path} was not produced by the pipeline")
    if stat.S_ISLNK(st.st_mode):
        raise AssertionError(f"{path} is a symlink; graded output must be a real file")
    if not stat.S_ISREG(st.st_mode):
        raise AssertionError(f"{path} is not a regular file")
    resolved = Path(os.path.realpath(path))
    if resolved != path:
        raise AssertionError(f"{path} resolves outside its declared location ({resolved})")
    with open(path, "r") as handle:
        return json.load(handle)


def drop_privs():
    """Best-effort preexec that drops the pipeline run to an unprivileged uid."""
    os.setgid(NOBODY_GID)
    os.setgroups([])
    os.setuid(NOBODY_UID)


def run_pipeline(unprivileged: bool) -> subprocess.CompletedProcess:
    """Execute the submitted pipeline with a minimal environment."""
    env = {
        "PATH": "/usr/local/bin:/usr/bin:/bin",
        "HOME": "/tmp",
        "LANG": "C.UTF-8",
        "PYTHONDONTWRITEBYTECODE": "1",
    }
    kwargs = {}
    if unprivileged:
        kwargs["preexec_fn"] = drop_privs
    return subprocess.run(
        [sys.executable, "pipeline.py"],
        cwd=str(APP_DIR),
        env=env,
        capture_output=True,
        text=True,
        timeout=RUN_TIMEOUT_SEC,
        **kwargs,
    )


def make_app_writable() -> bool:
    """Hand /app to the unprivileged uid. False if that is not possible here."""
    try:
        for root, dirs, files in os.walk(APP_DIR):
            for name in dirs:
                target = os.path.join(root, name)
                if not os.path.islink(target):
                    os.chown(target, NOBODY_UID, NOBODY_GID)
                    os.chmod(target, os.stat(target).st_mode | 0o700)
            for name in files:
                target = os.path.join(root, name)
                if not os.path.islink(target):
                    os.chown(target, NOBODY_UID, NOBODY_GID)
                    os.chmod(target, os.stat(target).st_mode | 0o600)
        os.chown(APP_DIR, NOBODY_UID, NOBODY_GID)
        os.chmod(APP_DIR, os.stat(APP_DIR).st_mode | 0o700)
        return True
    except (PermissionError, OSError):
        return False


def main() -> int:
    # The staging dir must not pre-exist: anything the submission left here
    # (a symlink aliasing a captured output onto its expected file, a planted
    # status record) is destroyed before a single value is staged.
    verify_dir = make_staging_dir()

    # Lift the answer key off disk before any agent code runs.
    expected = {}
    removed = []
    for n in CONFIGS:
        src = TESTS_DIR / f"expected_output_{n}.json"
        expected[n] = json.loads(src.read_text())
        try:
            src.unlink()
            removed.append(n)
        except OSError:
            pass  # read-only /tests; the perm/uid defenses below still apply
    configs = {n: json.loads((TESTS_DIR / f"hidden_config_{n}.json").read_text()) for n in CONFIGS}

    tests_mode = TESTS_DIR.stat().st_mode & 0o777
    logs_mode = LOGS_DIR.stat().st_mode & 0o777 if LOGS_DIR.exists() else None
    sealed = chmod_quiet(TESTS_DIR, 0o700)
    if logs_mode is not None:
        chmod_quiet(LOGS_DIR, 0o700)

    unprivileged = make_app_writable()
    status = {
        "unprivileged": unprivileged,
        "answer_key_removed": sorted(removed),
        "tests_dir_sealed": sealed,
        "interpreter_hooks": find_interpreter_hooks(),
        "runs": {},
    }

    try:
        for n in CONFIGS:
            entry = {"ok": False, "error": None, "stderr": ""}
            try:
                safe_remove(OUTPUT_PATH)
                safe_remove(CONFIG_PATH)
                CONFIG_PATH.write_text(json.dumps(configs[n], indent=2))
                os.chmod(CONFIG_PATH, 0o644)
                if unprivileged:
                    os.chown(CONFIG_PATH, NOBODY_UID, NOBODY_GID)

                proc = run_pipeline(unprivileged)
                entry["stderr"] = (proc.stderr or "")[-2000:]
                if proc.returncode != 0:
                    raise AssertionError(
                        f"pipeline.py exited {proc.returncode} on hidden config {n}"
                    )

                actual = guard_output(OUTPUT_PATH)
                write_json_exclusive(verify_dir / f"actual_{n}.json", actual)
                entry["ok"] = True
            except subprocess.TimeoutExpired:
                entry["error"] = f"pipeline.py exceeded {RUN_TIMEOUT_SEC}s on hidden config {n}"
            except Exception as exc:  # surfaced to pytest as a failing guard test
                entry["error"] = str(exc)
            status["runs"][str(n)] = entry
    finally:
        chmod_quiet(TESTS_DIR, tests_mode)
        if logs_mode is not None:
            chmod_quiet(LOGS_DIR, logs_mode)

    # Answer key goes back only into the 0700 staging dir, never /tests.
    for n in CONFIGS:
        write_json_exclusive(verify_dir / f"expected_{n}.json", expected[n])
        write_json_exclusive(verify_dir / f"config_{n}.json", configs[n])
    write_json_exclusive(verify_dir / "status.json", status)

    for n in CONFIGS:
        entry = status["runs"][str(n)]
        if not entry["ok"]:
            print(f"hidden config {n}: {entry['error']}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())
