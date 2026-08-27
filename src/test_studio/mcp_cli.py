from __future__ import annotations

import argparse

from .cli import create_driver
from .mcp_server import create_mcp_server


def main() -> None:
    parser = argparse.ArgumentParser(prog="test-studio-mcp")
    parser.add_argument("--transport", choices=("stdio", "sse", "streamable-http"), default="stdio")
    parser.add_argument("--driver", choices=("simulated", "playwright", "adb", "wda"), default="simulated")
    parser.add_argument("--base-url", default="http://127.0.0.1:4173")
    parser.add_argument("--cdp-url")
    parser.add_argument("--headed", action="store_true")
    parser.add_argument("--serial")
    parser.add_argument("--package")
    parser.add_argument("--wda-url", default="http://127.0.0.1:8100")
    parser.add_argument("--bundle-id")
    args = parser.parse_args()
    driver = create_driver(args)
    try:
        create_mcp_server(driver).run(transport=args.transport)
    finally:
        close = getattr(driver, "close", None)
        if close:
            close()


if __name__ == "__main__":
    main()
