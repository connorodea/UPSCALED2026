#!/usr/bin/env python3
import argparse
import datetime as dt
import os
import sys
from typing import Optional


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Launch a browser, log into TechLiquidators, and export cookies."
    )
    parser.add_argument(
        "--browser",
        choices=["chromium", "webkit", "firefox"],
        default="chromium",
        help="Browser engine to launch (default: chromium)",
    )
    parser.add_argument(
        "--out",
        default="Upscaled_inv_processing/data/techliquidators/techliquidators_cookies.txt",
        help="Output cookie file (Netscape format)",
    )
    parser.add_argument(
        "--url",
        default="https://www.techliquidators.com/login",
        help="Login URL to open",
    )
    return parser.parse_args()


def find_project_root(start: str) -> Optional[str]:
    current = os.path.abspath(start)
    while True:
        if os.path.isdir(os.path.join(current, "01_SOURCING")):
            return current
        parent = os.path.dirname(current)
        if parent == current:
            break
        current = parent
    return None


def resolve_path(path: str) -> str:
    if os.path.isabs(path):
        return path
    root = find_project_root(os.getcwd()) or find_project_root(os.path.dirname(__file__))
    if root:
        return os.path.join(root, path)
    return path


def write_netscape_cookie_file(path: str, cookies: list) -> None:
    lines = [
        "# Netscape HTTP Cookie File",
        f"# Generated {dt.datetime.utcnow().isoformat()}Z",
    ]
    for cookie in cookies:
        domain = cookie.get("domain") or ""
        include_subdomains = "TRUE" if domain.startswith(".") else "FALSE"
        path_value = cookie.get("path") or "/"
        secure = "TRUE" if cookie.get("secure") else "FALSE"
        expires = str(int(cookie.get("expires") or 0))
        name = cookie.get("name") or ""
        value = cookie.get("value") or ""
        lines.append("\t".join([domain, include_subdomains, path_value, secure, expires, name, value]))

    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines) + "\n")


def main() -> int:
    args = parse_args()
    out_path = resolve_path(args.out)

    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        print("playwright is required: pip install playwright && playwright install", file=sys.stderr)
        return 1

    with sync_playwright() as p:
        browser = None
        last_error = None
        browser_order = [args.browser, "webkit", "firefox"]
        for name in browser_order:
            if browser is not None:
                break
            try:
                browser = getattr(p, name).launch(headless=False)
            except Exception as exc:  # pragma: no cover
                last_error = exc
                browser = None
                continue
        if browser is None:
            raise RuntimeError(f"Failed to launch browser: {last_error}")
        context = browser.new_context()
        page = context.new_page()
        page.goto(args.url, wait_until="domcontentloaded")

        input("Log in to TechLiquidators, then press Enter here to save cookies... ")

        cookies = context.cookies()
        write_netscape_cookie_file(out_path, cookies)
        browser.close()

    print(f"Saved cookies to {out_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
