from app.services.movies import create_movie_from_tmdb


def main():
    movie = create_movie_from_tmdb(
        movie_id="muvy-interstellar-test",
        tmdb_id=157336,
    )

    print("Movie successfully stored in Supabase.")
    print()
    print(f"Internal ID: {movie['id']}")
    print(f"TMDB ID: {movie['tmdb_id']}")
    print(f"Title: {movie['title']}")
    print(f"Release date: {movie['release_date']}")
    print(f"Runtime: {movie['runtime']}")


if __name__ == "__main__":
    main()