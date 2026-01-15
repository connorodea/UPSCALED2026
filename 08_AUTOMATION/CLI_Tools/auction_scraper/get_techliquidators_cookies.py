#!/usr/bin/env python3
import argparse
import datetime as dt
import os
import sys
import time
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
        default="upscaled-tl/data/techliquidators/techliquidators_cookies.txt",
        help="Output cookie file (Netscape format)",
    )
    parser.add_argument(
        "--url",
        default="https://www.techliquidators.com/login",
        help="Login URL to open",
    )
    parser.add_argument(
        "--creds-file",
        help="Path to .env file with TL_USERNAME and TL_PASSWORD",
    )
    parser.add_argument(
        "--auto-save-seconds",
        type=int,
        default=25,
        help="Seconds to wait before saving cookies when non-interactive (default: 25)",
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


def load_env_credentials(path: str) -> dict:
    creds = {}
    if not path:
        return creds
    try:
        with open(path, "r", encoding="utf-8") as f:
            for line in f:
                raw = line.strip()
                if not raw or raw.startswith("#") or "=" not in raw:
                    continue
                key, value = raw.split("=", 1)
                creds[key.strip()] = value.strip()
    except FileNotFoundError:
        return {}
    return creds


def try_auto_login(page, username: str, password: str) -> bool:
    try:
        page.goto("https://www.techliquidators.com/account/sign_in/", wait_until="domcontentloaded")
        sign_in_selector = "a.header-nav-link--account[href*='sign_in']"
        if page.query_selector(sign_in_selector):
            page.click(sign_in_selector)
            page.wait_for_load_state("domcontentloaded", timeout=15000)

        email_selector = "input[type='email'], input[name*='email' i], input[id*='email' i]"
        password_selector = "input[type='password'], input[name*='password' i], input[id*='password' i]"
        page.wait_for_selector(email_selector, timeout=15000)
        page.fill(email_selector, username)
        page.wait_for_selector(password_selector, timeout=15000)
        page.fill(password_selector, password)
        submit_selector = "button[type='submit'], input[type='submit']"
        if page.query_selector(submit_selector):
            page.click(submit_selector)
        else:
            page.keyboard.press("Enter")
        page.wait_for_load_state("networkidle", timeout=30000)
        account_selector = "a.header-nav-link--account.dropdown-toggle"
        orders_selector = "a.account-dropdown-link[href*='/orders']"
        if page.query_selector(account_selector):
            page.click(account_selector)
            page.wait_for_timeout(500)
            if page.query_selector(orders_selector):
                page.click(orders_selector)
                page.wait_for_load_state("networkidle", timeout=30000)
        return True
    except Exception:
        return False


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

        creds = load_env_credentials(args.creds_file or "")
        username = creds.get("TL_USERNAME", "")
        password = creds.get("TL_PASSWORD", "")
        auto_used = False
        if username and password:
            auto_used = try_auto_login(page, username, password)

        if not auto_used and not sys.stdin.isatty():
            print(f"Waiting {args.auto_save_seconds}s for login, then saving cookies...", file=sys.stderr)
            time.sleep(args.auto_save_seconds)
        elif not auto_used:
            input("Log in to TechLiquidators, then press Enter here to save cookies... ")

        cookies = context.cookies()
        write_netscape_cookie_file(out_path, cookies)
        browser.close()

    print(f"Saved cookies to {out_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
