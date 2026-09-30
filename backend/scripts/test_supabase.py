from app.db.supabase import supabase


def main():
    response = (
        supabase
        .table("movies")
        .select("id")
        .limit(1)
        .execute()
    )

    print("Supabase connection successful.")
    print(response.data)


if __name__ == "__main__":
    main()