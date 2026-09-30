from app.services.tmdb import get_movie_details


def main():
    movie = get_movie_details(157336)

    print("TMDB connection successful.")
    print(f"Title: {movie.get('title')}")
    print(f"TMDB ID: {movie.get('id')}")
    print(f"Release date: {movie.get('release_date')}")
    print(f"Runtime: {movie.get('runtime')} minutes")


if __name__ == "__main__":
    main()