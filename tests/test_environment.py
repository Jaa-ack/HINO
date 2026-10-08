"""Exercise the public launcher with a real project interpreter."""
import json
import os
from pathlib import Path
import shutil
import subprocess

ROOT = Path(__file__).resolve().parents[1]


def launch(*args, env=None, root=ROOT):
    return subprocess.run(
        ["/bin/sh", str(root / "ecopilot"), *args],
        cwd="/tmp", env=env, text=True, capture_output=True, timeout=30,
    )


def test_launcher_uses_project_venv_and_ignores_foreign_python_settings():
    env = dict(os.environ, PYTHONHOME="/foreign/python", PYTHONPATH="/foreign/packages",
               VIRTUAL_ENV="/foreign/venv", PIP_TARGET="/foreign/packages", PIP_USER="1")
    result = launch("python", "-c", """
import json, os, site, sys, tempfile
print(json.dumps(dict(prefix=sys.prefix, user_site=site.ENABLE_USER_SITE,
    paths=sys.path, cwd=os.getcwd(), temp=tempfile.gettempdir(),
    target=os.getenv('PIP_TARGET'), virtual_env=os.getenv('VIRTUAL_ENV'),
    pip_config=os.getenv('PIP_CONFIG_FILE'), threads=os.getenv('OPENBLAS_NUM_THREADS'))))
""", env=env)
    assert result.returncode == 0, result.stderr
    data = json.loads(result.stdout)
    assert Path(data["prefix"]) == ROOT / ".venv"
    assert data["user_site"] is False
    assert "/foreign/packages" not in data["paths"]
    assert Path(data["cwd"]) == ROOT
    assert Path(data["temp"]).is_relative_to(ROOT / ".runtime")
    assert data["target"] is None
    assert data["virtual_env"] == str(ROOT / ".venv")
    assert data["pip_config"] == os.devnull
    assert data["threads"] == "1"


def test_launcher_refuses_to_fall_back_to_system_packages(tmp_path):
    launcher = ROOT / "ecopilot"
    assert launcher.exists(), "缺少專案環境啟動入口"
    shutil.copy2(launcher, tmp_path / "ecopilot")
    result = launch("python", "-c", "print('should not run')", root=tmp_path)
    assert result.returncode != 0
    assert "./ecopilot setup" in result.stderr
    assert "should not run" not in result.stdout


def test_launcher_refuses_venv_linked_to_another_project(tmp_path):
    shutil.copy2(ROOT / "ecopilot", tmp_path / "ecopilot")
    (tmp_path / "scripts").mkdir()
    shutil.copy2(ROOT / "scripts/environment.py", tmp_path / "scripts/environment.py")
    (tmp_path / ".venv").symlink_to(ROOT / ".venv", target_is_directory=True)
    result = launch("python", "-c", "print('should not run')", root=tmp_path)
    assert result.returncode != 0
    assert "符號連結" in result.stderr
    assert "should not run" not in result.stdout


def test_launcher_preserves_arguments_and_child_exit_status():
    result = launch("python", "-c", "import sys; print(sys.argv[1]); sys.exit(7)", "含 空白的參數")
    assert result.returncode == 7, result.stderr
    assert result.stdout.strip() == "含 空白的參數"


def test_environment_check_confirms_pinned_dependencies():
    result = launch("check")
    assert result.returncode == 0, result.stdout + result.stderr
    assert "requirements-lock.txt" in result.stdout
    assert "No broken requirements found" in result.stdout


def test_start_rejects_invalid_port_without_launching_server():
    result = launch("start", "--port", "0")
    assert result.returncode != 0
    assert "1024" in result.stderr
