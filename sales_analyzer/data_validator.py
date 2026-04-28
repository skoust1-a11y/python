from sales_analyzer.exceptions import InvalidDataError
# from sales_analyzer.logger_config import setup_logger

def data_valiadtor(res: list,logging):
    if len(res) != 3:
        raise InvalidDataError('Each line should contain exactly 3 values')

    name = res[0]

    try:
        qty = int(res[1])
    except ValueError:
        raise InvalidDataError(f"Quantity should be numeric for: {name}")

    if qty <= 0:
        raise InvalidDataError(f"Quantity must be > 0 for: {name}")

    try:
        amount = float(res[2])
    except ValueError:
        raise InvalidDataError(f"Amount should be numeric for: {name}")

    if amount <= 0:
        raise InvalidDataError(f"Amount must be > 0 for: {name}")

    logging.debug(f'Validated Record: {name} - {qty} units - ₹{amount}')
    return (name, qty, amount)
