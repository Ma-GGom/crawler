from pathlib import Path
import logging
import sys


def _ensure_src_on_path() -> None:
    project_root = Path(__file__).resolve().parent
    src_dir = project_root / "src"
    src_path = str(src_dir)
    if src_path not in sys.path:
        sys.path.insert(0, src_path)


def main() -> int:
    _ensure_src_on_path()

    from app.logging_config import configure_logging
    from app.settings import load_settings

    settings = load_settings()
    configure_logging(settings.log_level)
    logger = logging.getLogger(__name__)
    logger.info("crawler_started", extra={"env": settings.env})

    try:
        from app.app import create_crawler_app

        runner = create_crawler_app()
        events = runner.run_once()
    except ModuleNotFoundError as exc:
        logger.exception("dependency_missing", extra={"error": str(exc)})
        return 1
    except Exception as exc:
        logger.exception("crawler_failed", extra={"error": str(exc)})
        return 1

    logger.info("crawler_finished", extra={"event_count": len(events)})
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

