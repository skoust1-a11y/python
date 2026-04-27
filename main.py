def main():
    # 1. Get the 8-digit number as a string
    number_str = input("Enter an eight-digit number: ")

    # 2. Initialize sum variables
    even_sum = 0
    odd_sum = 0

    # 3. Iterate through each digit
    for digit_char in number_str:
        # Convert the character back to an integer
        digit = int(digit_char)
        
        # 4. Check if even or odd using the modulo operator (%)
        if digit % 2 == 0:
            even_sum += digit
        else:
            odd_sum += digit

    # 5. Display the results
    print(even_sum)
    print(odd_sum)

if __name__ == "__main__":
    main()