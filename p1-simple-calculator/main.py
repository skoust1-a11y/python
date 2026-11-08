def main():
    # 1. Accept two numbers from the user
    # We use float() so the calculator can handle decimals as well as integers
    num1 = float(input("Enter the first number: "))
    num2 = float(input("Enter the second number: "))

    # 2. Perform arithmetic operations and display results
    print(f"\nResults for {num1} and {num2}:")
    
    # Addition
    print(f"Addition (+): {num1 + num2}")
    
    # Subtraction
    print(f"Subtraction (-): {num1 - num2}")
    
    # Multiplication
    print(f"Multiplication (*): {num1 * num2}")
    
    # Division (returns a float)
    if num2 != 0:
        print(f"Division (/): {num1 / num2}")
    else:
        print("Division (/): Cannot divide by zero")
        
    # Modulus (remainder)
    print(f"Modulus (%): {num1 % num2}")
    
    # Exponentiation (power)
    print(f"Exponentiation (**): {num1 ** num2}") 
    
    # Floor Division (division rounded down to the nearest whole number)
    print(f"Floor Division (//): {num1 // num2}")

if __name__ == "__main__":
    main()
