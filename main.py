from pathlib import Path
import sys


def _ensure_src_on_path() -> None:
    project_root = Path(__file__).resolve().parent
    src_dir = project_root / "src"
    src_path = str(src_dir)
    if src_path not in sys.path:
        sys.path.insert(0, src_path)


def main() -> int:
    _ensure_src_on_path()

    print("Ma-GGom crawler started: fetch + parse marathon events")
    try:
        from bootstrap.app import create_crawler_app

        runner = create_crawler_app()
        events = runner.run_once()
    except ModuleNotFoundError as exc:
        print(f"Dependency missing: {exc}")
        return 1
    except Exception as exc:  # CLI safety net
        print(f"Crawler failed: {exc}")
        return 1

    print(f"Found {len(events)} events")
    print("--- all events ---")
    for index, event in enumerate(events, start=1):
        print(f"[{index}] date: {event.date_text}")
        print(f"    title: {event.title}")
        print(f"    location: {event.location}")
        print(f"    link: {event.link_url}")
        print(f"    registration_period: {event.registration_period}")
        print(f"    official_website_url: {event.official_website_url}")
        print(f"    source: {event.source_name}")
        print(f"    crawled_at_kst: {event.crawled_at_kst}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())

