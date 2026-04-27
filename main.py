def main():
    # --- Step 1: Store movie details in a list of tuples ---
    # Format: (Title, Year, Duration, Genre)
    movies_list = [
        ("Inception", 2010, 148, "Sci-Fi"),
        ("Titanic", 1997, 195, "Romance"),
        ("Avatar", 2009, 162, "Sci-Fi"),
        ("Inception", 2010, 148, "Sci-Fi")  # Adding a duplicate to test the set
    ]

    # --- Step 2: Create a collection of unique movie titles ---
    # A set automatically removes duplicates
    unique_titles = {movie[0] for movie in movies_list}
    print(f"Unique Movie Titles: {unique_titles}\n")

    # --- Step 3: Store movie details with title–detail mapping ---
    # Dictionary format: {Title: (Year, Duration, Genre)}
    movie_repo = {movie[0]: (movie[1], movie[2], movie[3]) for movie in movies_list}

    # --- Step 4: Display details by title search ---
    search_title = input("Enter movie title to search: ")
    if search_title in movie_repo:
        details = movie_repo[search_title]
        print(f"Details for '{search_title}': Year: {details[0]}, Duration: {details[1]}m, Genre: {details[2]}")
    else:
        print("Movie not found.")

    # --- Step 5: Update movie genre ---
    update_title = "Inception"
    if update_title in movie_repo:
        year, duration, old_genre = movie_repo[update_title]
        new_genre = "Action/Sci-Fi"
        # Since tuples are immutable, we create a new one and reassign it to the key
        movie_repo[update_title] = (year, duration, new_genre)
        print(f"\nUpdated '{update_title}' genre from {old_genre} to {new_genre}.")

    # --- Step 6: Analyze movie collection ---
    print("\n--- Collection Analysis ---")
    
    # Total unique movies
    print(f"Total Unique Movies: {len(movie_repo)}")

    # Unique genres using set comprehension
    unique_genres = {details[2] for details in movie_repo.values()}
    print(f"Unique Genres: {unique_genres}")

    # Filtered list: Movies released after 2000 using list comprehension
    modern_movies = [title for title, details in movie_repo.items() if details[0] > 2000]
    print(f"Movies released after 2000: {modern_movies}")

if __name__ == "__main__":
    main()