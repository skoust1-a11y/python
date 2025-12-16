## Practice Exercise: Sales Analyzer App

### Problem Statement

- Design a Python application to process and validate retail sales records efficiently while maintaining clear logs and robust error handling.​
- The program should read sales data from a text file, validate each record for correctness, handle exceptions gracefully, and generate a summary report of total sales. It should also log key events such as data validation, errors, and file operations for monitoring and debugging purposes.

### Context

In real-world retail environments, data validation and error management are essential to ensure accurate business insights. Sales records often contain inconsistent or incorrect entries that must be detected early to avoid faulty
analytics.​

Your task is to create a practical sales data analyzer that demonstrates how file handling, exception management, data validation, and logging work together to build a reliable and maintainable Python application.

### Task Details

Following steps should be performed to build the solution for this practice. ​

#### Step 1: Read and Process Sales Data (`file_operations.py`)
- Read sales information from a text file named `sales_data.txt`, where each line represents a record in the format:​
    `product_name`, `quantity`, `amount`.​
- Handle errors like missing files or incorrect formatting gracefully using exception handling.

#### Step 2: Validate Records and Handle Exceptions (`data_validator.py`, `exceptions.py`)
- Create a validation module to ensure that each sales record is accurate and meaningful.​
- Check that quantity and amount are numeric and greater than zero.​
- Raise custom exceptions like `InvalidDataError` or `FileProcessingError` for invalid or corrupted data.​
- Use try-except blocks to manage unexpected errors gracefully and display clear, user-friendly messages.​

This step ensures that only clean, valid data is used in the analysis process.

#### Step 3: Configure Logging and Track Events​ (`logger_config.py`)​
- Set up a logging system to capture both console and file-based logs.​
- Create a reusable logger configuration that includes timestamps, log levels, and module names.​
- Record important events such as file reads, data validation status, and exceptions.​
- Ensure that logs are stored in a dedicated logs folder for future reference.​

Logging helps monitor the application flow and simplifies debugging in long-running or production environmen

#### Step 4: Generate and Write Summary Report​ (`main.py`)
- Integrate all modules to produce a final summary report.​
- Read and validate data from the input file.​
- Compute total sales and count of valid transactions.​
- Write a formatted summary report to an output file (e.g., `sales_summary.txt`).​
- Log completion messages and any issues encountered during execution​

​This step demonstrates how to combine file I/O, validation, and logging to create a robust and traceable application.

#### Instructions:

- Use boilerplate
- Ensure your code is well-organized and includes comments for clarity.
- Test your code thoroughly to ensure it meets the requirements.


