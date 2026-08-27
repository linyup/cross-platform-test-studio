from __future__ import annotations

import argparse
import json
from pathlib import Path

from .models import Flow, validate_flow
from .runner import FlowRunner
from .simulated import SimulatedDriver


def create_driver(args):
    if args.driver == "simulated":
        return SimulatedDriver()
    if args.driver == "playwright":
        from .drivers.playwright import PlaywrightDriver

        return PlaywrightDriver(args.base_url, headless=not args.headed, cdp_url=args.cdp_url)
    if args.driver == "adb":
        from .drivers.adb import AdbDriver

        if not args.serial:
            raise ValueError("--serial is required for adb")
        return AdbDriver(args.serial, args.package)
    if args.driver == "wda":
        from .drivers.wda import WdaDriver

        return WdaDriver(args.wda_url, args.bundle_id)
    raise ValueError(f"unsupported driver: {args.driver}")


def main() -> int:
    parser = argparse.ArgumentParser()
    subparsers = parser.add_subparsers(dest="command", required=True)
    validate_parser = subparsers.add_parser("validate")
    validate_parser.add_argument("flow", type=Path)
    run_parser = subparsers.add_parser("run")
    run_parser.add_argument("flow", type=Path)
    run_parser.add_argument("--artifacts", type=Path, default=Path("artifacts"))
    run_parser.add_argument("--report", type=Path)
    run_parser.add_argument("--driver", choices=("simulated", "playwright", "adb", "wda"), default="simulated")
    run_parser.add_argument("--base-url", default="http://127.0.0.1:4173")
    run_parser.add_argument("--headed", action="store_true")
    run_parser.add_argument("--cdp-url", help="attach to an existing Chromium/Electron CDP endpoint")
    run_parser.add_argument("--serial")
    run_parser.add_argument("--package")
    run_parser.add_argument("--wda-url", default="http://127.0.0.1:8100")
    run_parser.add_argument("--bundle-id")
    serve_parser = subparsers.add_parser("serve")
    serve_parser.add_argument("--flow", type=Path, default=Path("examples/create-note.flow.json"))
    serve_parser.add_argument("--host", default="127.0.0.1")
    serve_parser.add_argument("--port", type=int, default=4174)
    args = parser.parse_args()

    if args.command == "serve":
        from .web import serve

        serve(args.flow, args.host, args.port)
        return 0

    flow = Flow.from_dict(json.loads(args.flow.read_text(encoding="utf-8")))
    if args.command == "validate":
        errors = validate_flow(flow)
        if errors:
            print("\n".join(f"ERROR: {item}" for item in errors))
            return 1
        print(f"OK: {len(flow.steps)} steps")
        return 0

    driver = create_driver(args)
    try:
        result = FlowRunner(driver, args.artifacts).run(flow)
    finally:
        close = getattr(driver, "close", None)
        if close:
            close()
    rendered = json.dumps(result.to_dict(), indent=2)
    if args.report:
        args.report.parent.mkdir(parents=True, exist_ok=True)
        args.report.write_text(rendered + "\n", encoding="utf-8")
    print(rendered)
    return 0 if result.status == "passed" else 1


if __name__ == "__main__":
    raise SystemExit(main())
