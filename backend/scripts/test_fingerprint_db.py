from app.db.supabase import supabase
from matcher.matcher import FingerprintDB


def main():
    movie_id = "muvy-test-movie"

    # Create the movie first.
    supabase.table("movies").upsert({
        "id": movie_id,
        "title": "MUVY Test Movie",
    }).execute()

    # Now fingerprints can reference it.
    db = FingerprintDB()

    db.add(
        hash_=123456789,
        movie_id=movie_id,
        timestamp_ms=5000,
    )

    rows = db.all_rows()

    print("Fingerprint rows:")
    for row in rows:
        print(row)


if __name__ == "__main__":
    main()