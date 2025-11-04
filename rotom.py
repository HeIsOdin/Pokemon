"""
# Miscellaneous
Utility functions for the PokéPrint Inspector system.

This module provides helper functions used across the project, including:
- Colored terminal logging and message formatting
- Directory and file validation (including dataset extraction)
- Environment variable loading for external credentials
- Argument parsing for main execution scripts
- JSON configuration parsing to pass structured arguments

These utilities are designed to support the main PokéPrint pipeline,
which involves crawling card listings, processing images, and running machine learning models.

Dependencies:
- Standard Python libraries only (os, time, zipfile, json, argparse)

Note:
This module is intended to be imported by other scripts and should not
be run as a standalone executable.
"""

import os

def print_with_color(string: str, mode: int, quit: bool = True) -> None:
    """
    Print a colored message to the terminal.
    
    Args:
        - string (str): The message to display.
        - mode (int): 1 = ERROR, 2 = SUCCESS, 3 = WARNING, 4 = INFO.
        - quit (bool): If True, exits the program on ERROR.
    """
    def helper(mode: int) -> str:
        if mode == 1: return 'ERROR'
        elif mode == 2: return 'SUCCESS'
        elif mode == 3: return 'WARNING'
        elif mode == 4: return 'INFO'
        else: return ''
    
    # Print colored output
    print(f"\033[3{str(mode)}m[{helper(mode)}] {string}\033[0m")
    
    # Exit on error if specified
    if mode == 1 and quit:
        exit()

def enviromentals(*vars: str) -> tuple:
    """
    Retrieve environment variables.

    Args:
        - *vars (unknown number of strings): variables set in the environment
    
    Returns:
    - tuple (number of arguments passed): values of environmental variables
    """

    values = []
    for var in vars:
        value = os.getenv(var)
        if value: values.append(value)

    if len(values) != len(vars):
        print(f"\033[31m[ERROR] Some or all values in {vars} not set in environment.\033[0m")
        exit()
    return tuple(values)

def postgresql(sql: str,  table: tuple, template : tuple[str, ...] = (), pairs: dict = {}, limit: int = -1,):
    import psycopg2
    DATABASE, USER, PASSWORD, HOST, PORT = enviromentals(
    'POSTGRESQL_DBNAME',
    'POSTGRESQL_USER',
    'POSTGRESQL_PASSWD',
    'POSTGRESQL_HOST',
    'POSTGRESQL_PORT',
    )
    try:
        with psycopg2.connect(database=DATABASE, user=USER, password=PASSWORD, host=HOST, port=PORT) as conn:
            with conn.cursor() as cursor:

                columns = ', '.join(template); sql = sql.replace('columns', columns)
                values = ', '.join(['%s' for _ in template]); sql = sql.replace('values', values)
                table_name = ', '.join(table); sql = sql.replace('tables', table_name)

                data = []
                if pairs:
                    for key in template:
                        key = key.replace(' = %s', '') # Condition when UPDATE is in sql
                        if key in pairs.keys(): data.append(pairs.get(key, None))
                        else:
                            pass

                cursor.execute(sql, tuple(data))
            
                if sql.strip().lower().startswith("select"):
                    results = []
                    rows = cursor.fetchall() if limit == -1 else [cursor.fetchone()] if limit == 1 else cursor.fetchmany(limit)
                    if rows:
                        for row in rows:
                            if row and len(row) == len(template):
                                result = {}
                                for key, value in zip(template, row):
                                    result[key.replace(' = %s', '')] = value
                                results.append(result)
                    return results
                conn.commit()
                return []
    except psycopg2.OperationalError as e:
        with open('logs/pidgeotto.log', 'a') as fp: fp.write(f'{e}\n')
        return []
    except psycopg2.DatabaseError as e:
        with open('logs/pidgeotto.log', 'a') as fp: fp.write(f'{e}\n')
        return []
    except Exception as e:
        with open('logs/pidgeotto.log', 'a') as fp: fp.write(f'{e}\n')
        return []