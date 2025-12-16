## Practice Exercise: Modular Product Catalog & Discount Engine

### Problem Statement

- Develop a modular Python program to manage a small product catalog and discount system for an online store.​
- The program should allow users to store product information, apply various discounts using closure-based functions, and perform quick analysis using higher-order functions like `map()` and `filter()`   .​
- Each functional component should be organized into separate modules to ensure the program is reusable, scalable, and easy to maintain.

### Context

An online retailer wants to manage its growing product catalog efficiently. The retailer frequently runs promotional campaigns such as student discounts, festival offers, and bulk purchase deals.​

They need a program that can:​
    - Store multiple product details (name, price, category, stock).​
    - Filter and analyze products based on conditions (e.g., price range or category).​
    - Apply different discounts dynamically without hardcoding them.​
    - Structure the solution into modules so each task (product management, discount logic, filtering, etc.) is reusable and maintainable.​

Your task is to help the retailer design and implement this modular product catalog and discount system using functions, closures, and functional programming tools in Python.

### Task Details

Following steps should be performed to build the solution for this practice. ​

#### Step 1: Add products to the catalog​
- Define a reusable function `add_product()` to add a single product with details like name, price, and category.​
- Use `**kwargs` to handle optional details (e.g., stock, rating, brand).​
- Create another function add_products() using `*args` to add multiple products at once.​
- Store all products in a list of dictionaries (each dictionary represents one product).​

#### Step 2: Create and apply discount calculators using closures.​
- Define a closure function `discount_calculator(percent)` that returns an inner function `apply_discount(price)` which remembers the discount percentage.​
- Use this closure to apply different discount schemes (e.g., 10%, 20%) without using global variables.

#### Step 3: Filter and analyze products using lambda, map, and filter​
- Use `filter()` with lambda to select products above a certain price or belonging to a particular category.​
- Use `map()` with lambda to apply discounts to filtered products and calculate their final price.​
- Display the list of filtered and discounted products neatly formatted.

#### Step 4: Organize the program into modules​.​
- Split your code logically into the following Python modules:​
    - `products.py` → handles adding and storing products.​
    - `discounts.py` → defines closure-based discount calculators.​
    - `filters.py` → handles filtering and mapping operations.​
    - `main.py` → imports functions from the above modules, coordinates the workflow,
and displays results.

#### Expected Program Behavior

When the program runs:​
    - Several products are added to the catalog.​
    - A discount closure is created for “Festival Discount (20%)”.​
    - Products priced above ₹2000 are filtered.​
    - The 20% discount is applied to these products.​
    - Both the filtered and discounted product lists are displayed.

#### Project Structure

```
p1_product_catalog_app/
├── products.py
├── discounts.py
├── filters.py
└── main.py
```

#### Instructions:

- Use boilerplate.
- Ensure your code is well-organized and includes comments for clarity.
- Test your code thoroughly to ensure it meets the requirements.


