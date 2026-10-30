"""Small explicit commands; live collection never runs merely by importing a module."""
import argparse
import json
import shutil
from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4

from .maintenance import backup_baseline
from .models import CollectionResult, Query
from .pipeline import collect, replay
from .registry import PROJECT_ROOT, load_registry
from .reporting import slug, verify_report, write_report
from .direct_browser import DirectChromeSession

VISIBLE_BROWSER_ADAPTERS = frozenset({"cleanchoice", "american_power_and_gas", "direct_energy"})


def browser_state_key(query: Query) -> str | None:
    """Only Direct reuses public-site state, and only within the current run."""
    return query.adapter if query.adapter == "direct_energy" else None


def direct_retry_indexes(results: list[CollectionResult]) -> list[int]:
    """Retry only access-blocked Direct results after the shared session warms."""
    return [
        index for index, result in enumerate(results)
        if result.query.adapter == "direct_energy" and result.status == "blocked"
    ]


def direct_retry_is_substantive(previous: CollectionResult,
                                retry: CollectionResult) -> bool:
    """Accept a retry only when it proves the same market's live disposition."""
    if previous.query != retry.query or retry.query.adapter != "direct_energy":
        return False
    if not retry.context_verified or not retry.live_data_verified:
        return False
    if retry.status in {"success", "partial", "needs_review"}:
        return bool(retry.offers)
    if retry.status in {"empty", "unsupported"}:
        return not retry.offers
    return False


def select_direct_retry(previous: CollectionResult,
                        retry: CollectionResult) -> CollectionResult:
    """Retain an auditable summary whether the bounded retry wins or loses."""
    if direct_retry_is_substantive(previous, retry):
        retry.attempts = [*previous.attempts, {
            "kind": "initial_direct_attempt", "status": previous.status,
            "offers": len(previous.offers), "errors": len(previous.errors),
            "selected": False,
        }, {
            "kind": "bounded_direct_retry", "status": retry.status,
            "offers": len(retry.offers), "errors": len(retry.errors),
            "selected": True,
        }, *retry.attempts]
        return retry
    previous.attempts.extend([{
        "kind": "initial_direct_attempt", "status": previous.status,
        "offers": len(previous.offers), "errors": len(previous.errors),
        "selected": True,
    }, {
        "kind": "bounded_direct_retry", "status": retry.status,
        "offers": len(retry.offers), "errors": len(retry.errors),
        "selected": False,
        "reason": "retry did not prove a verified live same-market disposition",
    }])
    return previous


def browser_plan(query: Query, requested_headed: bool, requested_channel: str) -> tuple[str, bool, str | None]:
    """Return pool name, headless flag, and Playwright channel for a query."""
    channel = None if requested_channel == "chromium" else requested_channel
    if query.adapter == "direct_energy":
        # Direct currently accepts an ordinary Chrome process but rejects a
        # process launched by Playwright. Attach to a scraper-owned Chrome
        # profile through Chrome's local debugging interface instead.
        return "direct_cdp", False, "chrome"
    if requested_headed:
        return "primary", False, channel
    if query.adapter in VISIBLE_BROWSER_ADAPTERS:
        # These public shopping flows depend on ordinary visible Chrome (bot
        # handling or address autocomplete). Keep them in a dedicated pool so
        # the remainder of a broad run stays headless.
        return "visible", False, channel or "chrome"
    return "primary", True, channel


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description="NJ supplier evidence-first collector")
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("list", help="List configured supplier/utility combinations; no network")
    sub.add_parser("backup", help="Create/verify the pre-v2 source and CSV baseline")
    for command in ("collect", "discover"):
        child = sub.add_parser(command, help="Live public shopping collection" if command == "collect" else "Capture candidate responses; skip contract downloads")
        child.add_argument("--supplier", action="append", help="Exact supplier name; repeatable")
        child.add_argument("--utility", help="Exact registry utility name")
        child.add_argument("--commodity", choices=["electric", "gas"])
        child.add_argument("--zip", action="append", help="Exact configured test ZIP; repeatable")
        child.add_argument("--limit", type=int, default=1, help="Maximum ZIP-level queries; default 1")
        child.add_argument("--all", action="store_true", help="Run every configured ZIP-level query")
        child.add_argument("--headed", action="store_true", help="Show browser for manual verification")
        child.add_argument("--browser-channel", choices=["chromium", "chrome", "msedge"], default="chromium",
                           help="Browser executable to use; chromium is Playwright's bundled browser")
        child.add_argument("--output", type=Path, help="New output directory; must not exist")
    child = sub.add_parser("replay", help="Offline extraction from one fixture or a directory of fixtures")
    child.add_argument("fixture", type=Path)
    child.add_argument("--output", type=Path)
    child = sub.add_parser("verify", help="Validate result schema and artifact hashes; not live data correctness")
    child.add_argument("directory", type=Path)
    child = sub.add_parser("consolidate", help="Replace rows in a base run with focused retry runs")
    child.add_argument("base", type=Path)
    child.add_argument("--retry", type=Path, action="append", required=True)
    child.add_argument("--output", type=Path, required=True)
    child = sub.add_parser("freeze-fixture", help="Freeze one result.json and its existing public artifacts; review before committing")
    child.add_argument("result", type=Path)
    child.add_argument("destination", type=Path)
    args = parser.parse_args(argv)
    if args.command == "freeze-fixture":
        from .fixtures import freeze_fixture
        print(freeze_fixture(args.result, args.destination))
        return 0
    if args.command == "backup":
        print(backup_baseline())
        return 0
    if args.command == "verify":
        problems = verify_report(args.directory)
        print("\n".join(problems) if problems else "Result schemas and artifact hashes verified. Review report.md for collection status.")
        return 1 if problems else 0
    if args.command == "consolidate":
        if args.output.exists():
            parser.error("Output directory already exists; choose a new directory to preserve evidence")
        selected = {}
        sources = {}
        for directory in [args.base, *args.retry]:
            report = directory / "results.json"
            if not report.is_file():
                parser.error(f"Missing results.json: {directory}")
            for item in json.loads(report.read_text(encoding="utf-8")):
                result = CollectionResult.model_validate(item)
                key = slug(result.query)
                selected[key], sources[key] = result, directory
        args.output.mkdir(parents=True)
        for key, source in sources.items():
            source_query = source / key
            if not source_query.is_dir():
                parser.error(f"Missing per-query evidence directory: {source_query}")
            shutil.copytree(source_query, args.output / key)
        results = list(selected.values())
        write_report(results, args.output)
        problems = verify_report(args.output)
        print(f"Output: {args.output.resolve()}")
        print("\n".join(problems) if problems else "Result schemas and artifact hashes verified.")
        return 1 if problems else 0
    if args.command == "list":
        for query in load_registry():
            print(f"{query.supplier} | {query.utility} | {query.commodity} | {query.zip} | {query.adapter}" + (" | SKIP: " + query.skip_reason if query.skip_reason else ""))
        return 0
    root = args.output or PROJECT_ROOT / "data/runs" / (datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ") + "-" + uuid4().hex[:8])
    if root.exists():
        parser.error("Output directory already exists; choose a new directory to preserve evidence")
    root.mkdir(parents=True)
    if args.command == "replay":
        fixtures = sorted(args.fixture.glob("*.json")) if args.fixture.is_dir() else [args.fixture]
        if not fixtures:
            parser.error("No JSON fixtures found")
        results, seen = [], set()
        for fixture in fixtures:
            data = json.loads(fixture.read_text(encoding="utf-8"))
            query = Query.model_validate(data["query"])
            if slug(query) in seen:
                parser.error("Fixture directory contains duplicate supplier/utility queries; replay separately")
            seen.add(slug(query))
            results.append(replay(fixture, root / slug(query)))
    else:
        queries = [q for q in load_registry() if (not args.supplier or q.supplier in args.supplier)
                   and (not args.utility or q.utility == args.utility)
                   and (not args.commodity or q.commodity == args.commodity)
                   and (not args.zip or q.zip in args.zip)]
        if args.all and args.limit != 1:
            parser.error("Use either --all or --limit, not both")
        if args.limit < 1 or not queries:
            parser.error("No matching combinations or invalid limit; use 'nj-switch list' for exact names")
        backup_baseline()
        from playwright.sync_api import sync_playwright
        results = []
        with sync_playwright() as playwright:
            browsers = {}
            browser_contexts = {}
            direct_session = None
            try:
                selected_queries = queries if args.all else queries[:args.limit]
                for query in selected_queries:
                    pool, headless, channel = browser_plan(query, args.headed, args.browser_channel)
                    if pool not in browsers:
                        if pool == "direct_cdp":
                            print("Opening isolated standard Chrome for Direct Energy", flush=True)
                            direct_session = DirectChromeSession.launch(
                                playwright, PROJECT_ROOT / "data/browser-profiles/direct-energy-v2"
                            )
                            browsers[pool] = direct_session.browser
                            browser_contexts["direct_energy"] = direct_session.context
                        elif pool == "visible" and not args.headed:
                            print("Opening visible Chrome for suppliers that reject fresh headless sessions", flush=True)
                            browsers[pool] = playwright.chromium.launch(headless=headless, channel=channel)
                        else:
                            browsers[pool] = playwright.chromium.launch(headless=headless, channel=channel)
                    print(f"Collecting {query.supplier} / {query.utility}", flush=True)
                    state_key = browser_state_key(query)
                    if state_key and state_key not in browser_contexts:
                        # This is a new temporary context, never the user's Chrome
                        # profile. Reuse it only for Direct queries in this run so
                        # public regional/session state survives territory changes.
                        browser_contexts[state_key] = browsers[pool].new_context(
                            accept_downloads=True, viewport={"width": 1360, "height": 900}
                        )
                    result = collect(
                        query,
                        browsers[pool],
                        root / slug(query),
                        discovery=args.command == "discover",
                        shared_context=browser_contexts.get(state_key) if state_key else None,
                    )
                    results.append(result)
                    # Checkpoint each combination independently before the run report.
                    path = root / slug(query)
                    path.mkdir(parents=True, exist_ok=True)
                    (path / "result.json").write_text(result.model_dump_json(indent=2), encoding="utf-8")
                    print(f"  {result.status}: {len(result.offers)} offer(s), {len(result.contracts)} contract(s)", flush=True)

                # One bounded second chance for Direct markets that encountered
                # the access layer before the run-scoped session was established.
                # This is not a historical fallback and never retries valid empty,
                # unsupported, partial, or successful results.
                for index in direct_retry_indexes(results):
                    previous = results[index]
                    query = previous.query
                    print(f"Retrying blocked Direct session / {query.utility}", flush=True)
                    retry = collect(
                        query,
                        browsers[browser_plan(query, args.headed, args.browser_channel)[0]],
                        root / slug(query),
                        discovery=args.command == "discover",
                        shared_context=browser_contexts["direct_energy"],
                    )
                    selected = select_direct_retry(previous, retry)
                    results[index] = selected
                    if selected is retry:
                        path = root / slug(query)
                        (path / "result.json").write_text(retry.model_dump_json(indent=2), encoding="utf-8")
                    else:
                        path = root / slug(query)
                        (path / "result.json").write_text(previous.model_dump_json(indent=2), encoding="utf-8")
                    print(f"  {retry.status}: {len(retry.offers)} offer(s), {len(retry.contracts)} contract(s)", flush=True)
            finally:
                for key, context in browser_contexts.items():
                    if key != "direct_energy":
                        context.close()
                for pool, browser in browsers.items():
                    if pool != "direct_cdp":
                        browser.close()
                if direct_session is not None:
                    direct_session.close()
    write_report(results, root)
    print(f"Output: {root.resolve()}")
    return 0 if all(r.status == "success" for r in results) else 2


if __name__ == "__main__":
    raise SystemExit(main())
