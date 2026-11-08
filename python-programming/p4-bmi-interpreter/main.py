def main():
    # 1. Get user input and convert to float for calculations
    weight = float(input("Enter your weight (in kg): "))
    height = float(input("Enter your height (in meters): "))

    # 2. Calculate BMI
    bmi = weight / (height ** 2)

    # 3. Classify based on the BMI value
    if bmi < 18.5:
        category = "Underweight"
    elif 18.5 <= bmi < 25:
        category = "Normal weight"
    elif 25 <= bmi < 30:
        category = "Overweight"
    else:
        category = "Obesity"

    # 4. Display the results
    # Using :.2f limits the output to 2 decimal places
    print(f"BMI value: {bmi:.2f}")
    print(f"Classification: {category}")

if __name__ == "__main__":
    main()