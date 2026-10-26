from unittest.mock import Mock, patch

from fastapi.testclient import TestClient

import api


client = TestClient(api.app)


@patch("api.search_movies")
def test_tmdb_search_returns_movie_candidates(mock_search):
    mock_search.return_value = [
        {
            "id": 9761,
            "title": "Elephants Dream",
            "release_date": "2006-03-24",
            "overview": "An open movie.",
            "poster_path": "/poster.jpg",
        }
    ]

    response = client.get(
        "/tmdb/search",
        params={"q": "Elephants Dream"},
        headers={"Accept-Language": "en-US"},
    )

    assert response.status_code == 200
    assert response.json()[0]["id"] == 9761
    mock_search.assert_called_once_with("Elephants Dream", language="en-US")


def test_tmdb_search_rejects_short_queries():
    response = client.get("/tmdb/search", params={"q": "a"})

    assert response.status_code == 422


def test_tmdb_search_rejects_whitespace_queries():
    response = client.get("/tmdb/search", params={"q": "  "})

    assert response.status_code == 422


@patch("api.supabase")
@patch("api.get_movie_details")
def test_catalog_request_saves_only_tmdb_metadata(mock_get_movie, mock_supabase):
    mock_get_movie.return_value = {
        "id": 9761,
        "title": "Elephants Dream",
        "release_date": "2006-03-24",
    }
    existing_response = Mock()
    existing_response.data = []
    (
        mock_supabase.table.return_value
        .select.return_value
        .eq.return_value
        .limit.return_value
        .execute.return_value
    ) = existing_response
    insert_response = Mock()
    insert_response.data = [{"id": 1}]
    mock_supabase.table.return_value.insert.return_value.execute.return_value = (
        insert_response
    )

    response = client.post(
        "/catalog-requests",
        json={"tmdb_id": 9761},
    )

    assert response.status_code == 200
    assert response.json()["submitted"] is True
    assert response.json()["already_submitted"] is False
    assert mock_supabase.table.call_count == 2
    mock_supabase.table.return_value.insert.assert_called_once_with(
        {
            "tmdb_id": 9761,
            "title": "Elephants Dream",
            "release_date": "2006-03-24",
        }
    )


@patch("api.supabase")
@patch("api.get_movie_details")
def test_catalog_request_returns_existing_pending_suggestion(
    mock_get_movie,
    mock_supabase,
):
    existing_response = Mock()
    existing_response.data = [{"title": "Elephants Dream", "status": "pending"}]
    (
        mock_supabase.table.return_value
        .select.return_value
        .eq.return_value
        .limit.return_value
        .execute.return_value
    ) = existing_response

    response = client.post(
        "/catalog-requests",
        json={"tmdb_id": 9761},
    )

    assert response.status_code == 200
    assert response.json()["already_submitted"] is True
    assert response.json()["message"] == (
        "Elephants Dream has already been suggested and is pending."
    )
    mock_get_movie.assert_not_called()
    mock_supabase.table.return_value.insert.assert_not_called()


@patch("api.supabase")
@patch("api.get_movie_details", return_value=None)
def test_catalog_request_rejects_unknown_tmdb_id(mock_get_movie, mock_supabase):
    existing_response = Mock()
    existing_response.data = []
    (
        mock_supabase.table.return_value
        .select.return_value
        .eq.return_value
        .limit.return_value
        .execute.return_value
    ) = existing_response

    response = client.post(
        "/catalog-requests",
        json={"tmdb_id": 987654321},
    )

    assert response.status_code == 404
    mock_get_movie.assert_called_once_with(987654321)
