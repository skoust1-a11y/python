def main():
    # 1. Accept input from the user
    # We keep it as a string initially to make reversing easier
    num_str = input("Enter a number: ")

    # 2. Reverse the string using slicing [::-1]
    # The syntax [start:stop:step] with -1 step reverses the sequence
    reversed_str = num_str[::-1]

    # 3. Convert back to an integer to store it as a number
    reversed_num = int(reversed_str)

    # 4. Print the result
    print(reversed_num)

if __name__ == "__main__":
    main()