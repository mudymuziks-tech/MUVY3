from app.services.tmdb import search_movies


def main():
    titles = [
        "Reckless",
        "Michael",
        "Enola Holmes 3",
    ]

    for title in titles:
        print()
        print("=" * 60)
        print(f"SEARCH: {title}")
        print("=" * 60)

        results = search_movies(title)

        for movie in results[:5]:
            print(
                f"TMDB ID: {movie.get('id')}"
            )
            print(
                f"Title: {movie.get('title')}"
            )
            print(
                f"Release date: "
                f"{movie.get('release_date')}"
            )
            print()


if __name__ == "__main__":
    main()