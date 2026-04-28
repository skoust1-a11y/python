from pathlib import Path
from sales_analyzer.exceptions import FileProcessingError,InvalidDataError
from sales_analyzer.data_validator import data_valiadtor
# from sales_analyzer.logger_config import setup_logger

class CustomException(Exception):
    pass

def file_ops(logging):
    validated_data = []
    try:
        fileName = Path('data/sales_data.txt')
        with open(fileName,'r',newline='') as f:
            logging.info('Reading sales data from file...')
            listOfLines = f.readlines()
            logging.info(f'Read {len(listOfLines)} records from {fileName}')
            logging.info('Validating sales data...')
            for line in listOfLines:
                try:
                    res = [x.strip() for x in line.split(',')]
                    result_validated = data_valiadtor(res,logging)
                    validated_data.append(result_validated)
                except InvalidDataError as e:
                    #  print(f"Invalid record -> {line.strip()} | Error: {e}")
                     logging.warning(f'Skipping invalid record: {e}')
    except FileNotFoundError as e:
        raise FileProcessingError('File Not Found in that given path')
    except Exception as e:
        raise FileProcessingError(f'Unexpected error : {e}')
    else:
        # print('Data is Analyazed..')
        logging.info('Data is Analyzed')
        return validated_data,len(listOfLines)
    finally:
        # print('File Processing Completed..')
        logging.info('File Reading Completed..')


       

