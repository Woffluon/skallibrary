"""Kullanim: python scripts/migrate_to_neon.py [--url postgresql://...] [--skip-data]"""
import argparse
import getpass
import os
import re
import subprocess
import sys
from pathlib import Path

DUMP = Path("data.json")


def run(label, args, env):
    print(f"==> {label}")
    r = subprocess.run([sys.executable, *args], env=env)
    if r.returncode != 0:
        sys.exit(f"'{label}' basarisiz (exit {r.returncode})")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--url", help="Neon DATABASE_URL (vermezsen gizli sorar)")
    ap.add_argument("--skip-data", action="store_true", help="sadece semayi kur")
    a = ap.parse_args()

    if not Path("manage.py").exists():
        sys.exit("manage.py yok. Proje kok klasorunde calistir.")

    url = a.url or getpass.getpass("Neon DATABASE_URL: ").strip()
    if not re.match(r"^postgres(ql)?://", url):
        sys.exit("DATABASE_URL postgres:// ile baslamali.")
    direct = url.replace("-pooler", "")  # migrate/loaddata icin dogrudan host

    base = {**os.environ, "PYTHONUTF8": "1"}
    base.pop("DATABASE_URL", None)
    neon = {**base, "DATABASE_URL": direct}

    run("Paketler", ["-m", "pip", "install", "-q", "dj-database-url", "psycopg[binary]"], base)

    try:
        if not a.skip_data:
            run("SQLite -> data.json", [
                "manage.py", "dumpdata", "--natural-foreign", "--natural-primary",
                "-e", "contenttypes", "-e", "auth.Permission",
                "--indent", "2", "-o", str(DUMP),
            ], base)

        run("Neon migrate", ["manage.py", "migrate", "--noinput"], neon)

        if not a.skip_data:
            out = subprocess.run(
                [sys.executable, "manage.py", "shell", "-c",
                 "from django.contrib.auth import get_user_model as g; print(g().objects.count())"],
                env=neon, capture_output=True, text=True,
            )
            count = int(out.stdout.strip() or 0)
            if count > 0 and input(f"Neon'da zaten {count} kullanici var. Yine de yukle? (e/H) ") != "e":
                sys.exit("Iptal edildi.")
            run("Neon loaddata", ["manage.py", "loaddata", str(DUMP)], neon)

        print("Bitti. Kontrol: python manage.py runserver")
    finally:
        DUMP.unlink(missing_ok=True)  # sifre hash'leri icerir


if __name__ == "__main__":
    main()
