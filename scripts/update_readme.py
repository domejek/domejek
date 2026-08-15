#!/usr/bin/env python3
"""
Aktualisiert den Abschnitt "Zuletzt aktualisierte Repositories" im README.md
zwischen den Markern <!--START_SECTION:recent-repos--> und <!--END_SECTION:recent-repos-->.

Wird von .github/workflows/update-readme.yml ausgeführt (Cron + Push).
Kann auch lokal getestet werden:  python3 scripts/update_readme.py
"""

import os
import re
import sys
from datetime import datetime, timezone
from urllib.request import Request, urlopen
from urllib.error import HTTPError
import json

USERNAME = os.environ.get("GH_USERNAME", "domejek")
README_PATH = os.environ.get("README_PATH", "README.md")
MAX_REPOS = int(os.environ.get("MAX_REPOS", "6"))
TOKEN = os.environ.get("GITHUB_TOKEN")

START_MARKER = "<!--START_SECTION:recent-repos-->"
END_MARKER = "<!--END_SECTION:recent-repos-->"

LANG_EMOJI = {
    "PHP": "🐘", "Python": "🐍", "JavaScript": "🟨", "TypeScript": "🔷",
    "Java": "☕", "Perl": "🐪", "HTML": "🌐", "CSS": "🎨", "Go": "🐹",
    "Shell": "🐚", "Vue": "💚", "C#": "🎯", "Rust": "🦀",
}


def fetch_repos():
    url = f"https://api.github.com/users/{USERNAME}/repos?per_page=100&sort=pushed"
    headers = {"Accept": "application/vnd.github+json", "User-Agent": USERNAME}
    if TOKEN:
        headers["Authorization"] = f"Bearer {TOKEN}"
    req = Request(url, headers=headers)
    try:
        with urlopen(req, timeout=20) as resp:
            data = json.load(resp)
    except HTTPError as e:
        print(f"GitHub API Fehler: {e.code} {e.reason}", file=sys.stderr)
        sys.exit(1)

    # Eigene, nicht archivierte, nicht geforkte Repos, ohne das Profil-Repo selbst
    repos = [
        r for r in data
        if not r.get("fork") and not r.get("archived") and r.get("name") != USERNAME
    ]
    repos.sort(key=lambda r: r["pushed_at"], reverse=True)
    return repos[:MAX_REPOS]


def format_date(iso_str):
    dt = datetime.strptime(iso_str, "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=timezone.utc)
    return dt.strftime("%d.%m.%Y")


def build_table(repos):
    if not repos:
        return "_Noch keine Repositories gefunden._"

    lines = [
        "| Repository | Sprache | Beschreibung | Zuletzt aktualisiert |",
        "|---|---|---|---|",
    ]
    for r in repos:
        name = r["name"]
        url = r["html_url"]
        lang = r.get("language") or "—"
        emoji = LANG_EMOJI.get(lang, "💻")
        desc = (r.get("description") or "_keine Beschreibung_").replace("|", "\\|")
        updated = format_date(r["pushed_at"])
        lines.append(f"| [{name}]({url}) | {emoji} {lang} | {desc} | {updated} |")

    lines.append("")
    lines.append(
        f"_Automatisch generiert am {datetime.now(timezone.utc).strftime('%d.%m.%Y %H:%M UTC')}_"
    )
    return "\n".join(lines)


def update_readme(table_md):
    with open(README_PATH, "r", encoding="utf-8") as f:
        content = f.read()

    if START_MARKER not in content or END_MARKER not in content:
        print("Marker nicht im README gefunden — nichts zu tun.", file=sys.stderr)
        sys.exit(1)

    pattern = re.compile(
        re.escape(START_MARKER) + r".*?" + re.escape(END_MARKER),
        re.DOTALL,
    )
    replacement = f"{START_MARKER}\n{table_md}\n{END_MARKER}"
    new_content = pattern.sub(replacement, content)

    if new_content == content:
        print("Keine Änderungen nötig.")
        return False

    with open(README_PATH, "w", encoding="utf-8") as f:
        f.write(new_content)
    print("README.md aktualisiert.")
    return True


if __name__ == "__main__":
    repos = fetch_repos()
    table = build_table(repos)
    changed = update_readme(table)
    # Exit-Code 0 immer, damit der Workflow-Schritt danach (git diff Check) entscheidet
    sys.exit(0)