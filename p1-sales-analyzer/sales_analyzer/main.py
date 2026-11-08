from sales_analyzer.file_operations import file_ops
from sales_analyzer.logger_config import setup_logger
from pathlib import Path
from sales_analyzer.exceptions import FileProcessingError

def main():
    logger = setup_logger()

    logger.info(' === Sales Data Analyzer Started ===')

    try:
        validated_data,total_count = file_ops(logger)
    # print(validated_data)

        logger.info('Calculating total and average sales...')


        total_sales = sum(item[2] for item in validated_data)
        total_transactions = len(validated_data)

        fileName = Path('data/sales_summary.txt')

        with open(fileName,'w') as f:
            f.write("Sales Summary Report\n")
            f.write("---------------------\n")
            f.write(f"Total Valid Transactions: {total_transactions}\n")
            f.write(f"Total Sales Amount: {total_sales}\n")
            f.write(f"Total Skipped Invalid records:{total_count-total_transactions}\n")

            logger.info(f"Total Skipped Invalid records:{total_count-total_transactions}")

            logger.info(f'Summary report written to /sales_data_analyzer_app/{fileName}')
            logger.info(f'Sales summary written to /sales_data_analyzer_app/{fileName}')
        

    except FileProcessingError as e:
        print('File error:',str(e))
    
    logger.info(' === Sales Data Analyzer Completed ===')
  

if __name__ == "__main__":
    main()
