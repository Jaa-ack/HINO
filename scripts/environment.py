"""專案環境入口：固定直譯器、隔離設定與前景服務。僅使用標準函式庫。"""
from __future__ import annotations

import argparse
import importlib.metadata
import os
from pathlib import Path
import re
import site
import socket
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
VENV = ROOT / ".venv"
PYTHON = VENV / "bin/python"
LOCK = ROOT / "requirements-lock.txt"

HELP = """HINO EcoPilot｜獨立專案環境（macOS / Linux，Python 3.14）
  ./ecopilot setup                 建立 .venv，依固定版本安裝套件
  ./ecopilot check                 檢查隔離設定、固定版本與套件相依
  ./ecopilot start [--port 18501]   前景啟動；按 Ctrl+C 停止
  ./ecopilot build [參數]          建置分析資料
  ./ecopilot inspect [參數]        檢查來源活頁簿
  ./ecopilot test [參數]           執行 pytest
  ./ecopilot python [參數]         使用專案 Python
"""


def project_environment():
    env = {key: value for key, value in os.environ.items()
           if not key.startswith(("PYTHON", "PIP_", "STREAMLIT_"))}
    runtime = ROOT / ".runtime"
    for name in ("tmp", "cache"):
        (runtime / name).mkdir(parents=True, exist_ok=True)
    env.update({
        "VIRTUAL_ENV": str(VENV),
        "PATH": str(VENV / "bin") + os.pathsep + env.get("PATH", os.defpath),
        "PYTHONNOUSERSITE": "1",
        "PIP_CONFIG_FILE": os.devnull,
        "TMPDIR": str(runtime / "tmp"),
        "TMP": str(runtime / "tmp"),
        "TEMP": str(runtime / "tmp"),
        "XDG_CACHE_HOME": str(runtime / "cache"),
        "OPENBLAS_NUM_THREADS": "1",
        "OMP_NUM_THREADS": "1",
        "MKL_NUM_THREADS": "1",
        "VECLIB_MAXIMUM_THREADS": "1",
        "NUMEXPR_NUM_THREADS": "1",
        "STREAMLIT_BROWSER_GATHER_USAGE_STATS": "false",
    })
    return env


def check_interpreter():
    if sys.version_info[:2] != (3, 14):
        raise ValueError("固定環境需要 Python 3.14；目前版本為 " + sys.version.split()[0])


def check_venv():
    check_interpreter()
    if VENV.is_symlink():
        raise ValueError(".venv 不可是指向其他環境的符號連結；請建立專案自己的虛擬環境。")
    if sys.prefix == sys.base_prefix or Path(sys.prefix).resolve() != VENV.resolve():
        raise ValueError("請使用 ./ecopilot 指令；不允許使用其他環境或系統套件。")
    config = (VENV / "pyvenv.cfg").read_text().lower()
    settings = dict(line.split("=", 1) for line in config.splitlines() if "=" in line)
    settings = {key.strip(): value.strip() for key, value in settings.items()}
    if settings.get("include-system-site-packages") != "false" or site.ENABLE_USER_SITE:
        raise ValueError(".venv 未隔離系統或使用者套件，請重新建立專案虛擬環境。")


def check_versions():
    normalize = lambda name: re.sub(r"[-_.]+", "-", name).lower()
    installed = {normalize(dist.metadata["Name"]): dist.version
                 for dist in importlib.metadata.distributions()}
    problems = []
    count = 0
    for line in LOCK.read_text().splitlines():
        if not line.strip() or line.startswith("#"):
            continue
        name, version = line.strip().split("==")
        actual = installed.get(normalize(name))
        if actual != version:
            problems.append(f"{name}：需要 {version}，目前 {actual or '未安裝'}")
        count += 1
    if problems:
        raise ValueError("套件與 requirements-lock.txt 不一致；執行 ./ecopilot setup 修復：\n"
                         + "\n".join(problems))
    return count


def pip_command(*args):
    return [str(PYTHON), "-I", "-m", "pip", "--isolated", "--disable-pip-version-check",
            "--no-cache-dir", "--require-virtualenv", *args]


def setup(env):
    check_interpreter()
    if VENV.is_symlink():
        raise ValueError(".venv 不可是符號連結；不會修改其他環境。")
    if not PYTHON.exists():
        if VENV.exists():
            raise ValueError(".venv 已存在但不完整；請先將它移至備份位置，再執行 setup。")
        subprocess.run([sys.executable, "-I", "-m", "venv", str(VENV)],
                       cwd=ROOT, env=env, check=True)
        os.execve(str(PYTHON), [str(PYTHON), "-I", str(Path(__file__)), "setup"], env)
    check_venv()
    subprocess.run(pip_command("install", "--no-user", "--only-binary=:all:",
                               "-r", str(LOCK)), cwd=ROOT, env=env, check=True)
    verify(env)


def verify(env):
    check_venv()
    count = check_versions()
    print(f"隔離檢查通過：{VENV}", flush=True)
    print(f"Python {sys.version.split()[0]}；requirements-lock.txt 的 {count} 個套件版本一致。",
          flush=True)
    subprocess.run(pip_command("check"), cwd=ROOT, env=env, check=True)


def start_arguments(args):
    parser = argparse.ArgumentParser(prog="./ecopilot start", description="以前景模式啟動本機服務")
    parser.add_argument("--port", type=int, default=18501, help="本機連接埠，預設 18501")
    port = parser.parse_args(args).port
    if not 1024 <= port <= 65535:
        parser.error("連接埠必須介於 1024 與 65535。")
    # 僅探測是否可綁定；不終止或修改既有服務。Streamlit 也會再次檢查。
    try:
        with socket.socket() as probe:
            probe.bind(("127.0.0.1", port))
    except OSError as exc:
        raise ValueError(f"無法使用連接埠 {port}：{exc}；可改用 --port 18502。") from exc
    print(f"啟動 http://127.0.0.1:{port}；在此終端機按 Ctrl+C 停止。", flush=True)
    return ["-m", "streamlit", "run", str(ROOT / "app.py"),
            "--server.address", "127.0.0.1", "--server.port", str(port),
            "--server.headless", "true", "--server.fileWatcherType", "none",
            "--server.runOnSave", "false", "--browser.gatherUsageStats", "false"]


def main():
    action, *args = sys.argv[1:] or ["help"]
    if action in ("help", "--help", "-h"):
        print(HELP)
        return
    if action not in {"setup", "check", "start", "build", "inspect", "test", "python"}:
        raise ValueError(f"未知指令：{action}\n{HELP}")
    if action in {"setup", "check"} and args:
        raise ValueError(f"{action} 不接受額外參數。")
    os.chdir(ROOT)
    env = project_environment()
    if action == "setup":
        setup(env)
        return
    check_venv()
    if action == "check":
        verify(env)
        return
    if action == "start":
        check_versions()
        command = start_arguments(args)
    elif action == "build":
        command = [str(ROOT / "scripts/build_pipeline.py"), *args]
    elif action == "inspect":
        command = [str(ROOT / "scripts/inspect_workbook.py"), *args]
    elif action == "test":
        command = ["-m", "pytest", *args]
    else:
        command = args
    # 取代目前程序，避免遺留背景子程序；Ctrl+C 直接送至應用程式。
    os.execve(str(PYTHON), [str(PYTHON), "-I", *command], env)


if __name__ == "__main__":
    try:
        main()
    except (ValueError, OSError) as exc:
        print(f"環境檢查未通過：{exc}", file=sys.stderr)
        sys.exit(1)
    except subprocess.CalledProcessError as exc:
        sys.exit(exc.returncode)
