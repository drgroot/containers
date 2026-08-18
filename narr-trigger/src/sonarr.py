from typing import Any, Iterable, List, Mapping, cast

from pyarr import SonarrAPI

from src import Item


def _normalize_series_response(values: Any) -> Iterable[Mapping[str, Any]]:
    if isinstance(values, dict):
        return [values]

    if isinstance(values, list):
        return [value for value in values if isinstance(value, dict)]

    return []


def _percent_from_statistics(stats: Any) -> float:
    if not isinstance(stats, Mapping):
        return 0.0
    return float(stats.get("percentOfEpisodes") or 0.0)


def get_sonarr_items(narr: SonarrAPI) -> List[Item]:
    items: List[Item] = []

    for series in _normalize_series_response(narr.get_series()):
        items.append(
            {
                "name": str(series.get("sortTitle", "")),
                "id": str(series.get("id", "")),
                "percent": _percent_from_statistics(
                    series.get("statistics")  # type: ignore[arg-type]
                ),
            }
        )
    return items


def search_sonarr_item(narr: SonarrAPI, item: Item) -> str:
    response = cast(Any, narr).post_command(
        name="SeriesSearch", seriesId=int(item["id"])
    )
    return str(response["status"]).lower()
