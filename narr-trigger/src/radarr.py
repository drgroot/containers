from typing import Any, Iterable, List, Mapping, cast

from pyarr import RadarrAPI

from src import Item


def _normalize_movie_response(values: Any) -> Iterable[Mapping[str, Any]]:
    if isinstance(values, dict):
        return [values]

    if isinstance(values, list):
        return [value for value in values if isinstance(value, dict)]

    return []


def _cast_int(value: Any) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return 0


def _movie_filename(series: Mapping[str, Any]) -> str:
    movie_file = series.get("movieFile")
    if isinstance(movie_file, Mapping):
        return str(movie_file.get("relativePath", "")).lower()
    return ""


def get_radarr_items(narr: RadarrAPI) -> List[Item]:
    items: List[Item] = []

    for series in _normalize_movie_response(narr.get_movie()):
        percent = 0.0
        if series.get("sizeOnDisk"):
            percent = 100.0
            filename = _movie_filename(series)

            if "remux" not in filename:
                percent *= 0.5
            if _cast_int(series.get("year")) > 2014 and "2160p" not in filename:
                percent *= 0.5

        items.append(
            {
                "name": str(series.get("sortTitle", "")),
                "id": str(series.get("id", "")),
                "percent": percent,
            }
        )
    return items


def search_radarr_item(narr: RadarrAPI, item: Item) -> str:
    params = {"movieIds": [int(item["id"])]}
    response = cast(Any, narr).post_command(name="MoviesSearch", **params)
    return str(response["status"]).lower()
