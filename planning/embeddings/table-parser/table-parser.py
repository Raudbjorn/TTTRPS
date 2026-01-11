#!/usr/bin/env python3
"""
Table Parser - HTML Table Parsing and SQLite Persistence

Parses HTML tables and related pages, extracts structured data,
and persists to SQLite database. Designed as a foundation for
embedding generation pipelines.
"""

import re
import os.path
import sqlite3
from datetime import datetime
from bs4 import BeautifulSoup


# Data structures
elements_list_db: list[int] = []  # Element IDs from DB
elements_dict_db: dict[int, dict] = {}  # Elements from DB {elem_ID: {field: value}}
elements_list: list[int] = []  # Element IDs from parsed HTML
elements_dict: dict[int, dict] = {}  # Elements from parsed HTML {elem_ID: {field: value}}
new_elements_list: list[int] = []  # New elements not yet in DB


def parse_html_table(raw_html: str) -> None:
    """
    Parse HTML table and extract structured data into elements_dict.

    Extracts from each table row:
    - elem_ID: integer identifier
    - name1, name2, name3: text fields
    - date_and_time: datetime object

    Args:
        raw_html: Raw HTML string containing a table
    """
    soup = BeautifulSoup(raw_html, 'html.parser')
    trows = soup.find_all('tr')
    for row in trows:
        cells = row.find_all('td')
        if len(cells) > 0:
            element = {}
            element['elem_ID'] = int(cells[0].text.strip())
            element['name1'] = cells[1].text.strip()
            element['name2'] = cells[2].text.strip()
            element['name3'] = cells[3].text.strip()
            element['date_and_time'] = datetime.strptime(cells[4].text.strip(), '%Y-%m-%d %H:%M')
            elements_dict[element['elem_ID']] = element
            elements_list.append(element['elem_ID'])
    elements_list.sort()


def parse_element_details(elem_id: int, raw_html: str) -> dict:
    """
    Parse additional details from an element's detail page.

    Extracts:
    - somecontent: text from a specific div
    - somelinks: list of anchor elements
    - somedata: regex-extracted data

    Args:
        elem_id: The element ID
        raw_html: Raw HTML of the detail page

    Returns:
        Dict with extracted fields
    """
    # Regex extraction example (non-greedy, multiline)
    elem_data_regex = re.compile(r'<p id="someid">.*?</p>', flags=re.DOTALL)
    match = elem_data_regex.search(raw_html)
    elem_data = ""
    if match:
        elem_data = match.group().replace('<p id="someid">', '').replace('</p>', '').strip()

    soup = BeautifulSoup(raw_html, 'html.parser')

    content_div = soup.find('div', id="some_content_id")
    somecontent = content_div.text.strip() if content_div else ""
    somelinks = soup.find_all('a', class_="some_link_class")

    return {
        'somecontent': somecontent,
        'somelinks': somelinks,
        'somedata': elem_data
    }


def add_details_to_element(elem_id: int, details: dict) -> None:
    """
    Add parsed detail fields to an element in elements_dict.

    Args:
        elem_id: The element ID to update
        details: Dict with somecontent, somelinks, somedata
    """
    if elem_id in elements_dict:
        elements_dict[elem_id].update(details)


def find_new_elements() -> None:
    """Find elements in elements_list that are not in elements_list_db."""
    for elem_id in elements_list:
        if elem_id not in elements_list_db:
            new_elements_list.append(elem_id)
    new_elements_list.sort()


# --- Database Persistence Functions ---

def init_database(db_path: str = 'tablep.db') -> tuple[sqlite3.Connection, sqlite3.Cursor]:
    """
    Initialize SQLite database, creating table if needed.

    Args:
        db_path: Path to SQLite database file

    Returns:
        Tuple of (connection, cursor)
    """
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    cursor.execute('''
        CREATE TABLE IF NOT EXISTS elements (
            elem_ID INTEGER PRIMARY KEY,
            name1 TEXT,
            name2 TEXT,
            name3 TEXT,
            date_and_time TEXT,
            somecontent TEXT,
            somelinks TEXT,
            somedata TEXT
        )
    ''')
    conn.commit()
    return conn, cursor


def load_elements_from_db(cursor: sqlite3.Cursor) -> None:
    """
    Load existing elements from database into elements_dict_db and elements_list_db.

    Args:
        cursor: SQLite cursor
    """
    cursor.execute('SELECT * FROM elements ORDER BY elem_ID DESC')

    for row in cursor.fetchall():
        elem_id = row[0]
        elements_list_db.append(elem_id)

        element = {
            'elem_ID': row[0],
            'name1': row[1],
            'name2': row[2],
            'name3': row[3],
            'date_and_time': datetime.strptime(row[4], '%Y-%m-%d %H:%M') if row[4] else None,
            'somecontent': row[5],
            'somelinks': BeautifulSoup(row[6], 'html.parser').find_all('a') if row[6] else [],
            'somedata': row[7]
        }
        elements_dict_db[elem_id] = element

    elements_list_db.sort()


def insert_elements(cursor: sqlite3.Cursor, conn: sqlite3.Connection, elem_ids: list[int]) -> None:
    """
    Insert elements into database.

    Args:
        cursor: SQLite cursor
        conn: SQLite connection
        elem_ids: List of element IDs to insert
    """
    elements_to_add = []
    for elem_id in elem_ids:
        elem = elements_dict[elem_id]
        elements_to_add.append((
            elem['elem_ID'],
            elem.get('name1', ''),
            elem.get('name2', ''),
            elem.get('name3', ''),
            elem['date_and_time'].strftime('%Y-%m-%d %H:%M') if elem.get('date_and_time') else '',
            elem.get('somecontent', ''),
            str(elem.get('somelinks', [])),
            elem.get('somedata', '')
        ))
    cursor.executemany('INSERT INTO elements VALUES (?,?,?,?,?,?,?,?)', elements_to_add)
    conn.commit()


def delete_elements(cursor: sqlite3.Cursor, conn: sqlite3.Connection, elem_ids: list[int]) -> None:
    """
    Delete elements from database.

    Args:
        cursor: SQLite cursor
        conn: SQLite connection
        elem_ids: List of element IDs to delete
    """
    elements_to_delete = [(elem_id,) for elem_id in elem_ids]
    cursor.executemany('DELETE FROM elements WHERE elem_ID=?', elements_to_delete)
    conn.commit()


def update_element_data(cursor: sqlite3.Cursor, conn: sqlite3.Connection, elem_id: int, somedata: str) -> None:
    """
    Update somedata field for an element.

    Args:
        cursor: SQLite cursor
        conn: SQLite connection
        elem_id: Element ID to update
        somedata: New value for somedata field
    """
    cursor.execute('UPDATE elements SET somedata=? WHERE elem_ID=?', (somedata, elem_id))
    conn.commit()


def get_all_elements(cursor: sqlite3.Cursor) -> list[dict]:
    """
    Retrieve all elements from database.

    Args:
        cursor: SQLite cursor

    Returns:
        List of element dictionaries
    """
    cursor.execute('SELECT * FROM elements ORDER BY elem_ID')
    elements = []
    for row in cursor.fetchall():
        elements.append({
            'elem_ID': row[0],
            'name1': row[1],
            'name2': row[2],
            'name3': row[3],
            'date_and_time': row[4],
            'somecontent': row[5],
            'somelinks': row[6],
            'somedata': row[7]
        })
    return elements


def get_element_text_content(element: dict) -> str:
    """
    Extract text content from an element for embedding generation.

    Combines relevant text fields into a single string suitable
    for chunking and embedding.

    Args:
        element: Element dictionary

    Returns:
        Combined text content
    """
    parts = []
    for field in ['name1', 'name2', 'name3', 'somecontent', 'somedata']:
        if element.get(field):
            parts.append(str(element[field]))
    return '\n'.join(parts)


# --- Main execution example ---

if __name__ == '__main__':
    # Example usage demonstrating parsing and persistence workflow

    # Initialize database
    conn, cursor = init_database('tablep.db')

    # Load existing data from DB
    load_elements_from_db(cursor)

    # Example: Parse HTML from file or string
    # html_content = open('input.html').read()
    # parse_html_table(html_content)

    # Find new elements not yet in DB
    # find_new_elements()

    # For each new element, parse its detail page and add to dict
    # for elem_id in new_elements_list:
    #     detail_html = open(f'{elem_id}.html').read()
    #     details = parse_element_details(elem_id, detail_html)
    #     add_details_to_element(elem_id, details)

    # Insert new elements into database
    # insert_elements(cursor, conn, new_elements_list)

    # Retrieve all elements for embedding generation
    all_elements = get_all_elements(cursor)
    for elem in all_elements:
        text = get_element_text_content(elem)
        # Pass to embedding generation pipeline
        # embeddings = generate_embeddings(text)

    conn.close()
