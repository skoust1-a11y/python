def main():
    # 1. Define the variables
    customer_name = "Ravi Kumar"
    order_name = "ORD98765"
    shipping_address = (
        "A-12, Sunrise Apartments,\n"
        "Opp. M.G. Library,\n"
        "Mall Road, Indore - 450021"
    )
    delivery_date = "15-Jan-2025"

    # 2. Generate the message using an f-string
    message = f"""Hello {customer_name},

We are happy to inform you that your order {order_name} has been successfully shipped on {delivery_date} to:
{shipping_address}

Thank you for shopping with us!"""

    # 3. Print the output
    print(message)

if __name__ == "__main__":
    main()