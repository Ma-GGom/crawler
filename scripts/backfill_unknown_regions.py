from __future__ import annotations

import argparse
from pathlib import Path
import sys

import psycopg

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_DIR = PROJECT_ROOT / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from app.settings import load_settings
from adapter.outbound.source.mara1080_detail_client import Mara1080DetailClient
from domain.rule.distance_rule import extract_distances_from_title
from domain.rule.location_rule import REGION_UNKNOWN, resolve_event_region


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Backfill unknown region / empty distances in marathon_event"
    )
    parser.add_argument("--limit", type=int, default=0, help="Process only N rows (0: all)")
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Do not update DB, only show counts",
    )
    args = parser.parse_args()

    settings = load_settings()
    if not settings.database_url:
        raise RuntimeError("CRAWLER_DATABASE_URL is required")

    select_region_sql = """
        SELECT id, title, link_url
        FROM marathon_event
        WHERE region = %s
        ORDER BY id
    """
    select_distance_sql = """
        SELECT id, title
        FROM marathon_event
        WHERE distances IS NULL
           OR BTRIM(distances::text) IN ('', '{}')
        ORDER BY id
    """
    params: tuple[object, ...]
    if args.limit > 0:
        select_region_sql += " LIMIT %s"
        select_distance_sql += " LIMIT %s"
        params = (REGION_UNKNOWN, args.limit)
        distance_params = (args.limit,)
    else:
        params = (REGION_UNKNOWN,)
        distance_params = ()

    with psycopg.connect(settings.database_url) as conn:
        with conn.cursor() as cur:
            mara1080_detail_client = Mara1080DetailClient()
            cur.execute(select_region_sql, params)
            region_rows = cur.fetchall()

            region_updates: list[tuple[str, int]] = []
            for row_id, title, link_url in region_rows:
                inferred = _infer_region_for_row(
                    title=title,
                    link_url=link_url,
                    mara1080_detail_client=mara1080_detail_client,
                )
                if inferred == REGION_UNKNOWN:
                    continue
                region_updates.append((inferred, row_id))

            cur.execute(select_distance_sql, distance_params)
            distance_rows = cur.fetchall()
            distance_updates: list[tuple[list[str], int]] = []
            for row_id, title in distance_rows:
                distances = extract_distances_from_title(title or "")
                if not distances:
                    continue
                distance_updates.append((distances, row_id))

            if not args.dry_run and region_updates:
                cur.executemany(
                    """
                    UPDATE marathon_event
                    SET region = %s, updated_at = NOW()
                    WHERE id = %s
                      AND region = %s
                    """,
                    [(region, row_id, REGION_UNKNOWN) for region, row_id in region_updates],
                )
            if not args.dry_run and distance_updates:
                is_array_column = _is_array_distance_column(cur)
                update_payload: list[tuple[object, int]]
                if is_array_column:
                    update_payload = [
                        (distances, row_id) for distances, row_id in distance_updates
                    ]
                else:
                    update_payload = [
                        (_as_text_array_literal(distances), row_id)
                        for distances, row_id in distance_updates
                    ]

                cur.executemany(
                    """
                    UPDATE marathon_event
                    SET distances = %s, updated_at = NOW()
                    WHERE id = %s
                      AND (distances IS NULL OR BTRIM(distances::text) IN ('', '{}'))
                    """,
                    update_payload,
                )
            if not args.dry_run and (region_updates or distance_updates):
                conn.commit()

    print(f"unknown_total={len(region_rows)}")
    print(f"unknown_updatable={len(region_updates)}")
    print(f"empty_distances_total={len(distance_rows)}")
    print(f"empty_distances_updatable={len(distance_updates)}")
    print(f"dry_run={args.dry_run}")
    return 0


def _is_array_distance_column(cur: psycopg.Cursor) -> bool:
    cur.execute(
        """
        SELECT data_type, udt_name
        FROM information_schema.columns
        WHERE table_schema = current_schema()
          AND table_name = 'marathon_event'
          AND column_name = 'distances'
        LIMIT 1
        """
    )
    row = cur.fetchone()
    if row is None:
        return False
    data_type = (row[0] or "").strip().lower()
    udt_name = (row[1] or "").strip().lower()
    return data_type == "array" or udt_name.startswith("_")


def _as_text_array_literal(distances: list[str]) -> str:
    if not distances:
        return "{}"
    return "{" + ",".join(distances) + "}"


def _infer_region_for_row(
    *,
    title: str,
    link_url: str,
    mara1080_detail_client: Mara1080DetailClient,
) -> str:
    inferred = resolve_event_region(
        REGION_UNKNOWN,
        title=title,
        link_url=link_url,
    )
    if inferred != REGION_UNKNOWN:
        return inferred

    detail = mara1080_detail_client.fetch_detail(link_url)
    if detail is None or not detail.location:
        return REGION_UNKNOWN
    return resolve_event_region(
        detail.location,
        title=title,
        link_url=link_url,
    )


if __name__ == "__main__":
    raise SystemExit(main())
