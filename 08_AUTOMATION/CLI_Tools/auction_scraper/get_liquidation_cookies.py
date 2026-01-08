#!/usr/bin/env python3
import argparse
import sys
from http.cookiejar import MozillaCookieJar

import browser_cookie3


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Export Liquidation.com cookies to a Netscape cookie jar file."
    )
    parser.add_argument(
        "--browser",
        default="chrome",
        choices=["chrome", "chromium", "edge", "firefox", "safari"],
        help="Browser to read cookies from (default: chrome)",
    )
    parser.add_argument(
        "--domain",
        default="liquidation.com",
        help="Domain filter (default: liquidation.com)",
    )
    parser.add_argument(
        "--out",
        default="liquidation_cookies.txt",
        help="Output cookie jar path (default: liquidation_cookies.txt)",
    )
    return parser.parse_args()


def load_cookies(browser: str, domain: str):
    if browser == "chrome":
        return browser_cookie3.chrome(domain_name=domain)
    if browser == "chromium":
        return browser_cookie3.chromium(domain_name=domain)
    if browser == "edge":
        return browser_cookie3.edge(domain_name=domain)
    if browser == "firefox":
        return browser_cookie3.firefox(domain_name=domain)
    if browser == "safari":
        return browser_cookie3.safari(domain_name=domain)
    raise ValueError(f"Unsupported browser: {browser}")


def main() -> int:
    args = parse_args()
    try:
        jar = load_cookies(args.browser, args.domain)
        output = MozillaCookieJar(args.out)
        for cookie in jar:
            output.set_cookie(cookie)
        output.save(ignore_discard=True, ignore_expires=True)
    except Exception as exc:
        print(f"Failed to export cookies: {exc}", file=sys.stderr)
        return 1

    print(args.out)
    return 0


if __name__ == "__main__":
    sys.exit(main())
