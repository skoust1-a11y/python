"""
SQL Database Service - Provides SQLDatabase wrapper for hospital operations
"""
import os
from dotenv import load_dotenv
from llama_index.core import SQLDatabase
from sqlalchemy import create_engine
from typing import List,Optional

load_dotenv()


def get_db_engine():
    """
    Create a SQLAlchemy engine for the configured Postgres database.
    
    Returns:
        SQLAlchemy engine instance
    
    TODO: Implement the following steps:
    1. Retrieve database connection parameters from environment variables
    2. Construct the database connection URL string
    3. Create and return a SQLAlchemy engine using the connection URL
    """
    # TODO: Step 1 - Retrieve database connection parameters from environment variables
    # Hint: You need to retrieve all the database connection parameters using os.getenv. Get the database user with a default
    # value of "postgres", the password with a default value of "password", the host with a default value of "localhost", the port
    # with a default value of "5432", and the database name with a default value of "hospital_analytics_db". Store each value in
    # appropriately named variables.


    
    user = os.getenv('DB_USER','postgres')
    password = os.getenv('DB_PASSWORD','password')
    host = os.getenv('DB_HOST','localhost')
    port = os.getenv('DB_PORT','5432')
    dbname = os.getenv('DB_NAME','hospital_analytics_db')
    table_name = os.getenv('DB_TABLE_NAME')

    


    
    # TODO: Step 2 - Construct the database connection URL string
    # Hint: You need to build a PostgreSQL connection URL string in the format "postgresql://user:password@host:port/dbname".
    # Use an f-string to construct this URL by inserting the variables you retrieved in the previous step. Store the complete
    # connection URL string in a variable.
    CONNECTION_STRING = f'postgresql+psycopg2://{user}:{password}@{host}:{port}/{dbname}'
    
    # TODO: Step 3 - Create and return a SQLAlchemy engine
    # Hint: Use the create_engine function from sqlalchemy, passing in the connection URL string you constructed in the previous step.
    # The create_engine function will return a SQLAlchemy engine instance that can be used to connect to the database. Return this
    # engine instance from the function.
    db_engine = create_engine(CONNECTION_STRING)

    return db_engine


def get_sql_database(engine=None, include_tables : Optional[List] = None):
    """
    Return a LlamaIndex SQLDatabase wrapper over the Postgres engine.
    
    By default it exposes the hospital operations tables.
    
    Args:
        engine: Optional SQLAlchemy engine. If None, will be created automatically.
        include_tables: Optional list of table names to include. If None, defaults to hospital operations tables.
    
    Returns:
        SQLDatabase instance configured with the engine and tables
    
    TODO: Implement the following steps:
    1. Check if engine parameter is None and create one if needed
    2. Check if include_tables parameter is None and set default table list
    3. Create and return a SQLDatabase instance with the engine and tables
    """
    if engine is None:
        engine_load = get_db_engine()
    else:
        engine_load = engine
    # TODO: Step 1 - Check if engine parameter is None and create one if needed
    # Hint: Check whether the engine parameter passed to this function is None. If it is None, you need to create a database engine
    # by calling the get_db_engine function that is defined in this same file. Store the result in the engine variable so it can be
    # used in the subsequent steps.
    
    # TODO: Step 2 - Check if include_tables parameter is None and set default table list
    # Hint: Check whether the include_tables parameter passed to this function is None. If it is None, you need to set it to a list
    # containing the default table names that should be exposed. The default tables are "patients" and "department_capacity". Store
    # this list in the include_tables variable.
    default_tables = ["patients", "department_capacity"]

    if include_tables is None:
        tables_load = default_tables
    else:
        # Merge default tables with custom include_tables, keeping unique tables
        tables_load = list(set(default_tables + include_tables))

    
    # TODO: Step 3 - Create and return a SQLDatabase instance
    # Hint: Create a SQLDatabase instance from the llama_index.core module, passing in the engine and include_tables parameters.
    # The SQLDatabase class constructor takes the engine as the first argument and include_tables as a keyword argument. Return the
    # created SQLDatabase instance from the function.
    sql_database = SQLDatabase(
        engine=engine_load,
        include_tables=tables_load
    )

    return sql_database
