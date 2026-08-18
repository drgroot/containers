from unittest.mock import MagicMock

from src.table import get_items, upsert_row


def _setup_table(monkeypatch, rows):
    mock_table = MagicMock()
    reader = MagicMock()
    reader.to_pylist.return_value = rows
    mock_table.read.return_value = reader
    monkeypatch.setattr("src.table.MY_TABLE", mock_table)
    return mock_table


def test_upsert_row_inserts_when_no_rows(monkeypatch):
    mock_table = _setup_table(monkeypatch, [])

    upsert_row("host", "name", "id", 60.0, 2)

    mock_table.insert.assert_called_once()
    inserted = mock_table.insert.call_args[0][0][0]
    assert inserted["searchcount"] == 0
    assert inserted["indexers"] == 2
    assert inserted["percentfound"] == 60.0


def test_upsert_row_overwrites_with_increment(monkeypatch):
    existing = {"searchcount": 3, "percentfound": 50.0, "indexers": 4}
    mock_table = _setup_table(monkeypatch, [existing])

    upsert_row("host", "show", "id", 70.0, 5, increment=2)

    mock_table.overwrite.assert_called_once()
    overwritten = mock_table.overwrite.call_args[0][0][0]
    assert overwritten["searchcount"] == 5
    assert overwritten["percentfound"] == 70.0
    assert overwritten["indexers"] == 5


def test_get_items_returns_query_results(monkeypatch):
    rows = [("id-1", 1, 40.0, "Series")]
    mock_conn = MagicMock()
    mock_conn.execute.return_value.fetchall.return_value = rows
    reader = MagicMock()
    reader.to_duckdb.return_value = mock_conn
    mock_table = MagicMock()
    mock_table.readRaw.return_value = reader
    monkeypatch.setattr("src.table.MY_TABLE", mock_table)

    result = get_items("host", 3)

    assert result == rows
    mock_conn.execute.assert_called_once()
