#!/usr/bin/env python3
"""Checks that a Pitch In site is running a published release.

    python3 check.py https://pitchinhelp.com fingerprints.json [previous.json]

fingerprints.json is a release's published file (a path or a URL). Give the previous release too
and the site may match either, so the time between publishing a release and deploying it isn't
a false alarm. The check:
  1. loads the public pages and every script and stylesheet they use, and fails on any that
     isn't in the release, or whose SHA-384 differs;
  2. loads every file the release lists, and compares it;
  3. compares the Content-Security-Policy header, which decides what code pages may run.

Only Python's standard library, so anyone can read and run it. Exits 0 when everything matches,
1 otherwise. The release watcher runs it every few hours (deploy/release/README.md).

What it can't see: code served only to one person, or only on pages behind a group's passcode
that load files outside the release. Those files would still have to differ from the release to
do harm, and any shared file that changes is caught here.
"""

import base64
import hashlib
import json
import ssl
import sys
import urllib.request
from html.parser import HTMLParser
from urllib.parse import urljoin, urlsplit

PAGES = (
    "/",
    "/help/",
    "/create/",
    "/privacy/",
    "/privacy/report-card/",
    "/terms/",
    "/check/",
    "/whats-new/",
)


class Assets(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.found: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        a = dict(attrs)
        if tag == "script" and a.get("src"):
            self.found.append(a["src"] or "")
        if tag == "link" and "stylesheet" in (a.get("rel") or "") and a.get("href"):
            self.found.append(a["href"] or "")


def fetch(url: str, context: ssl.SSLContext | None) -> tuple[bytes, dict[str, str]]:
    if urlsplit(url).scheme not in ("https", "http"):
        raise ValueError(f"not a web address: {url}")
    request = urllib.request.Request(url, headers={"User-Agent": "pitchin-release-check"})  # noqa: S310
    with urllib.request.urlopen(request, timeout=20, context=context) as response:  # noqa: S310
        return response.read(), {k.lower(): v for k, v in response.headers.items()}


def sri(data: bytes) -> str:
    return "sha384-" + base64.b64encode(hashlib.sha384(data).digest()).decode()


def policy(header: str) -> list[str]:
    return sorted(part.strip() for part in header.split(";") if part.strip())


def load(source: str) -> dict:  # type: ignore[type-arg]
    if source.startswith("https://"):
        return json.loads(fetch(source, None)[0])
    with open(source, "rb") as f:
        return json.loads(f.read())


def main(argv: list[str]) -> int:
    insecure = "--insecure" in argv  # for a local test server with its own certificate
    args = [a for a in argv if a != "--insecure"]
    if len(args) not in (2, 3):
        print(__doc__)
        return 2
    site = args[0].rstrip("/")
    context = ssl._create_unverified_context() if insecure else None  # noqa: S323
    results = [compare(site, load(source), context) for source in args[1:]]
    for release, problems, count in results:
        if not problems:
            version = release["version"]
            print(f"OK: {site} matches release {version} ({count} files, {len(PAGES)} pages).")
            return 0
    release, problems, _count = results[0]
    print(f"MISMATCH: {site} is not running release {release['version']} as published:")
    for problem in problems:
        print("  - " + problem)
    if len(results) > 1:
        print(f"  (nor the previous release, {results[1][0]['version']})")
    return 1


def compare(
    site: str, release: dict, context: ssl.SSLContext | None
) -> tuple[dict, list[str], int]:  # type: ignore[type-arg]
    files: dict[str, str] = release["files"]
    problems: list[str] = []

    checked: set[str] = set()
    for page in PAGES:
        body, headers = fetch(site + page, context)
        csp = headers.get("content-security-policy", "")
        if policy(csp) != policy(release["headers"]["Content-Security-Policy"]):
            problems.append(f"{page}: the Content-Security-Policy header differs from the release")
        parser = Assets()
        parser.feed(body.decode("utf-8", "replace"))
        for src in parser.found:
            path = urlsplit(urljoin(site + page, src)).path
            if urlsplit(urljoin(site + page, src)).netloc not in ("", urlsplit(site).netloc):
                problems.append(f"{page}: loads a file from another site: {src}")
            elif path not in files:
                problems.append(f"{page}: loads a file that isn't in the release: {path}")
    for path, expected in files.items():
        actual = sri(fetch(site + path, context)[0])
        checked.add(path)
        if actual != expected:
            problems.append(f"{path}: differs from the release")

    return release, problems, len(checked)


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
