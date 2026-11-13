"""Run the free-source merchant batch into a new, dated review directory.

Run from the repository root. This never replaces an earlier snapshot and never
interprets a missing record as a closure. No proxy or paid API is used.
"""

import argparse
import json
import os
from datetime import datetime, timezone
from pathlib import Path

from scrapy.crawler import CrawlerProcess
from scrapy.utils.project import get_project_settings


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--spiders", nargs="+", help="Run only these registered spiders")
    args = parser.parse_args()
    if os.environ.get("ZYTE_API_KEY"):
        parser.error("Unset ZYTE_API_KEY: this runner is for direct, free requests only")
    registry = json.loads(Path("contrib/free_merchant_sources.json").read_text())
    selected = registry
    if args.spiders:
        unknown = set(args.spiders) - {row["spider"] for row in selected}
        if unknown:
            parser.error(f"Unknown spiders: {sorted(unknown)}")
        selected = [row for row in selected if row["spider"] in args.spiders]
    args.output.mkdir(parents=True, exist_ok=False)
    settings = get_project_settings()
    settings.update(
        {
            "HTTPCACHE_ENABLED": False,
            "REQUESTS_CACHE_ENABLED": False,
            "ROBOTSTXT_OBEY": True,
            "DOWNLOAD_TIMEOUT": 30,
            "CLOSESPIDER_TIMEOUT": 240,
            "CONCURRENT_REQUESTS_PER_DOMAIN": 2,
            "RETRY_TIMES": 1,
            "LOG_LEVEL": "WARNING",
            "LOG_FILE": str(args.output / "crawl.log"),
        },
        priority="cmdline",
    )
    process = CrawlerProcess(settings)
    crawlers = []
    for source in selected:
        crawler = process.create_crawler(source["spider"])
        crawler.settings.set(
            "FEEDS",
            {str(args.output / f'{source["spider"]}.geojson'): {"format": "geojson", "store_empty": False}},
            priority="cmdline",
        )
        crawlers.append((source, crawler))
        process.crawl(crawler)
    process.start()
    results = []
    for source, crawler in crawlers:
        stats = crawler.stats.get_stats() if crawler.stats else {}
        path = args.output / f'{source["spider"]}.geojson'
        features = json.loads(path.read_text())["features"] if path.exists() and path.stat().st_size else []
        exception_count = sum(value for key, value in stats.items() if key.startswith("spider_exceptions/"))
        success = (
            bool(features)
            and not exception_count
            and not stats.get("httperror/response_ignored_count")
            and not stats.get("downloader/exception_count")
            and not stats.get("feedexport/failed_count/LocalFileFeedStorage")
            and stats.get("finish_reason") == "finished"
        )
        result = {
            **source,
            "run_status": "collected_for_review" if success else "failed_or_incomplete",
            "locations": len(features),
            "with_geometry": sum(bool(row.get("geometry")) for row in features),
            "stats": stats,
        }
        results.append(result)
    report = {"collected_at": datetime.now(timezone.utc).isoformat(), "results": results}
    (args.output / "run.json").write_text(json.dumps(report, indent=2, default=str) + "\n")
    if any(row["run_status"] != "collected_for_review" for row in results):
        raise SystemExit(
            "Some sources failed or were incomplete. Inspect run.json and crawl.log before accepting data."
        )


if __name__ == "__main__":
    main()
