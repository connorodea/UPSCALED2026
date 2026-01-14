#!/usr/bin/env python3
import argparse
from http.cookiejar import MozillaCookieJar

import browser_cookie3


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
    raise SystemExit(f"Unsupported browser: {browser}")


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Export TechLiquidators cookies to a Netscape cookie jar file."
    )
    parser.add_argument("--browser", default="chrome")
    parser.add_argument("--domain", default="techliquidators.com")
    parser.add_argument(
        "--out",
        default="Upscaled_inv_processing/data/techliquidators/techliquidators_cookies.txt",
    )
    args = parser.parse_args()

    jar = load_cookies(args.browser, args.domain)
    output = MozillaCookieJar(args.out)
    for cookie in jar:
        output.set_cookie(cookie)
    output.save(ignore_discard=True, ignore_expires=True)
    print(f"Wrote {args.out}")


if __name__ == "__main__":
    main()
