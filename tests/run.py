"""
✅ Все проверки проекта одной командой (без Postgres и Redis — SQLite + fakeredis, наружу ничего не шлётся):

    pip install -r requirements.txt -r tests/requirements.txt     # один раз
    python tests/run.py                  # все
    python tests/run.py spots impact     # только эти (по части имени файла)

Каждый tests/test_*.py — отдельный сценарий: запускается в своём процессе со своей чистой базой,
в конце печатает «OK: N проверок». Упал — видно, какая проверка и почему (строка с AssertionError).
Настройки Django для тестов — tests/test_settings.py.
"""
import os
import re
import subprocess
import sys
import tempfile
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent


def main(filters):
    files = sorted(p for p in HERE.glob("test_*.py") if p.name != "test_settings.py")
    if filters:
        files = [p for p in files if any(f in p.stem for f in filters)]
    total, failed = 0, []
    start = time.time()
    for p in files:
        with tempfile.TemporaryDirectory() as tmp:
            env = {**os.environ, "TDB": str(Path(tmp) / "db.sqlite3"), "PYTHONPATH": f"{HERE}{os.pathsep}{ROOT}"}
            t0 = time.time()
            r = subprocess.run([sys.executable, str(p)], cwd=ROOT, env=env, capture_output=True, text=True, timeout=600)
        out = r.stdout + r.stderr
        m = re.search(r"OK: (\d+)(?:/\d+)?", out)
        if r.returncode == 0 and m:
            n = int(m.group(1))
            total += n
            print(f"  ✅ {p.stem:<18} {n:>3} проверок   {time.time() - t0:5.1f} с")
        else:
            failed.append(p.stem)
            print(f"  ❌ {p.stem:<18} УПАЛ")
            tail = [ln for ln in out.strip().splitlines() if ln.strip()][-12:]
            print("     " + "\n     ".join(tail))
    print(f"\n{'❌ Упало: ' + ', '.join(failed) if failed else '✅ Всё прошло'} — {total} проверок за {time.time() - start:.0f} с")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
