from typing import Any, List

from src.radarr import get_radarr_items, search_radarr_item


def _movie(**kwargs):
    defaults = {
        "sortTitle": "Test",
        "id": 1,
        "sizeOnDisk": 0,
        "movieFile": {"relativePath": "test.mkv"},
        "year": 2010,
    }
    defaults.update(kwargs)
    return defaults


class DummyRadarr:
    def __init__(self, movies: List[dict], response_status: str = "pending"):
        self._movies = movies
        self.response_status = response_status
        self.last_command: dict[str, Any] | None = None

    def get_movie(self):
        return self._movies

    def post_command(self, name: str, movieIds: List[int]):
        self.last_command = {"name": name, "movieIds": movieIds}
        return {"status": self.response_status}


def test_get_radarr_items_handles_empty_size():
    narr = DummyRadarr([_movie()])

    items = get_radarr_items(narr)

    assert items == [{"name": "Test", "id": "1", "percent": 0.0}]


def test_get_radarr_items_applies_percent_rules():
    narr = DummyRadarr(
        [
            _movie(
                sortTitle="Remix",
                id=99,
                sizeOnDisk=1,
                movieFile={"relativePath": "Sample 1080p.mkv"},
                year=2018,
            )
        ]
    )

    items = get_radarr_items(narr)

    assert items == [{"name": "Remix", "id": "99", "percent": 25.0}]


def test_search_radarr_item_lowercases_status():
    narr = DummyRadarr([], response_status="Queued")

    status = search_radarr_item(
        narr, {"id": "42", "name": "Foo", "percent": 0.0}
    )

    assert status == "queued"
    assert narr.last_command == {"name": "MoviesSearch", "movieIds": [42]}
