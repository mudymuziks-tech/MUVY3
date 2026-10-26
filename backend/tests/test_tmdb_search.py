from unittest.mock import Mock, patch

import pytest

import tmdb


@patch("tmdb.TMDB_API_KEY", "test-api-key")
@patch("tmdb.requests.get")
def test_search_movies_returns_tmdb_results(mock_get):
    response = Mock()
    response.status_code = 200
    response.json.return_value = {
        "results": [{"id": 9761, "title": "Elephants Dream"}]
    }
    mock_get.return_value = response

    results = tmdb.search_movies("Elephants Dream", language="en-US")

    assert results == [{"id": 9761, "title": "Elephants Dream"}]
    mock_get.assert_called_once_with(
        "https://api.themoviedb.org/3/search/movie",
        params={
            "api_key": "test-api-key",
            "query": "Elephants Dream",
            "language": "en-US",
            "include_adult": False,
        },
        timeout=10,
    )


@patch("tmdb.TMDB_API_KEY", "test-api-key")
@patch("tmdb.requests.get")
def test_search_movies_surfaces_http_errors(mock_get):
    response = Mock()
    response.status_code = 401
    response.text = "Unauthorized"
    mock_get.return_value = response

    with pytest.raises(tmdb.TMDBError, match="HTTP 401"):
        tmdb.search_movies("Elephants Dream")


@patch("tmdb.TMDB_API_KEY", "test-api-key")
@patch("tmdb.requests.get")
def test_search_movies_rejects_invalid_json(mock_get):
    response = Mock()
    response.status_code = 200
    response.json.side_effect = ValueError("invalid JSON")
    mock_get.return_value = response

    with pytest.raises(tmdb.TMDBError, match="invalid JSON"):
        tmdb.search_movies("Elephants Dream")
