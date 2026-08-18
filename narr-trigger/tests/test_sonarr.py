from typing import Any, Dict, List

from src.sonarr import get_sonarr_items, search_sonarr_item


def _series(*, statistics: Dict[str, float] | None = None, **kwargs):
    base_stats = {"percentOfEpisodes": 30.0}
    if statistics:
        base_stats.update(statistics)

    defaults = {
        "sortTitle": "Sample",
        "id": 2,
        "statistics": base_stats,
    }
    defaults.update(kwargs)
    return defaults


class DummySonarr:
    def __init__(self, series: List[dict], response_status: str = "ok"):
        self._series = series
        self.response_status = response_status
        self.last_command: dict[str, Any] | None = None

    def get_series(self):
        return self._series

    def post_command(self, name: str, seriesId: int):
        self.last_command = {"name": name, "seriesId": seriesId}
        return {"status": self.response_status}


def test_get_sonarr_items_returns_percent():
    narr = DummySonarr(
        [_series(statistics={"percentOfEpisodes": 75.5})]
    )

    items = get_sonarr_items(narr)

    assert items == [
        {"name": "Sample", "id": "2", "percent": 75.5}
    ]


def test_search_sonarr_item_invokes_post():
    narr = DummySonarr([], response_status="InProgress")

    status = search_sonarr_item(
        narr, {"id": "5", "name": "Test", "percent": 0.0}
    )

    assert status == "inprogress"
    assert narr.last_command == {"name": "SeriesSearch", "seriesId": 5}
