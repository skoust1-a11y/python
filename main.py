def main():
    # 1. Get input from the user
    char = input("Enter an alphabet: ").lower()

    # 2. Check if the input is a single letter (optional but good practice)
    if len(char) != 1 or not char.isalpha():
        print("Please enter a single alphabet.")
        return

    # 3. Define vowels and check
    vowels = "aeiou"
    
    if char in vowels:
        print("Vowel")
    else:
        print("Consonant")

if __name__ == "__main__":
    main()