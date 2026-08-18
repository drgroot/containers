from typing import List, Tuple

import pyiceberg.types as types
from pyiceberg.schema import Schema
from servc.svc.com.storage.iceberg import IceBerg
from servc.svc.com.storage.lake import LakeTable, Medallion
from servc.svc.config import Config

TABLE_SCHEMA: LakeTable = {
    "name": "search_history",
    "medallion": Medallion.GOLD,
    "partitions": ["host_url"],
    "schema": Schema(
        types.NestedField(
            field_id=1, name="host_url", type=types.StringType(), required=True
        ),
        types.NestedField(
            field_id=2, name="name", type=types.StringType(), required=True
        ),
        types.NestedField(
            field_id=3, name="id", type=types.StringType(), required=True
        ),
        types.NestedField(
            field_id=4, name="searchcount", type=types.IntegerType(), required=True
        ),
        types.NestedField(
            field_id=5, name="percentfound", type=types.FloatType(), required=True
        ),
        types.NestedField(
            field_id=6, name="indexers", type=types.IntegerType(), required=True
        ),
    ),
}

config = Config()
MY_TABLE = IceBerg(config.get("conf.lake"), TABLE_SCHEMA)


def upsert_row(
    host_url: str, name: str, id: str, percent: float, indexers: int, increment: int = 0
):
    rows = MY_TABLE.read(
        columns=["percentfound", "searchcount", "indexers"],
        partitions={"host_url": [host_url], "id": [id]},
    ).to_pylist()

    if len(rows) == 0:
        return MY_TABLE.insert(
            [
                {
                    "host_url": host_url,
                    "name": name,
                    "id": id,
                    "searchcount": increment,
                    "percentfound": percent,
                    "indexers": indexers,
                }
            ],
        )

    if increment == 0:
        if rows[0]["percentfound"] == percent and rows[0]["indexers"] == indexers:
            return

    searchcount: int = rows[0]["searchcount"]
    MY_TABLE.overwrite(
        [
            {
                "host_url": host_url,
                "name": name,
                "id": id,
                "searchcount": searchcount + increment,
                "percentfound": percent,
                "indexers": rows[0]["indexers"] if increment == 0 else indexers,
            }
        ],
        partitions={"host_url": [host_url], "id": [id]},
    )


def get_items(host_url: str, indexers: int):
    # get the series to search for
    conn = MY_TABLE.readRaw(
        columns=["*"], partitions={"host_url": [host_url]}
    ).to_duckdb(table_name="search_history")
    rows: List[Tuple[str, int, float, str]] = conn.execute(
        f"""
            SELECT id, searchcount, percentfound, name
            FROM search_history
            WHERE
                percentfound < 100
                AND (
                    searchcount < 10
                    OR (
                        searchcount >= 10
                        AND indexers != {indexers}
                    )
                )
                AND host_url = '{host_url}'
            ORDER BY searchcount ASC, percentfound ASC
            LIMIT 3
        """
    ).fetchall()
    return rows
