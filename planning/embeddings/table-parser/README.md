# Table Parser

HTML table parsing and SQLite persistence module for embedding generation pipelines.

## Overview

This module provides functions to:
1. **Parse** HTML tables and extract structured data
2. **Persist** parsed elements to SQLite database
3. **Retrieve** elements for downstream embedding generation

## Requirements

- Python 3.10+
- BeautifulSoup4 (`pip install bs4`)

## Usage

```python
from table_parser import (
    init_database,
    parse_html_table,
    parse_element_details,
    add_details_to_element,
    insert_elements,
    get_all_elements,
    get_element_text_content,
)

# Initialize database
conn, cursor = init_database('data.db')

# Parse main HTML table
html = open('index.html').read()
parse_html_table(html)

# Parse detail pages for each element
for elem_id in elements_list:
    detail_html = open(f'{elem_id}.html').read()
    details = parse_element_details(elem_id, detail_html)
    add_details_to_element(elem_id, details)

# Persist to database
insert_elements(cursor, conn, elements_list)

# Retrieve for embedding generation
for elem in get_all_elements(cursor):
    text = get_element_text_content(elem)
    # Pass to embedding pipeline
```

## Data Schema

```python
element = {
    'elem_ID': int,           # Primary key
    'name1': str,             # Text field 1
    'name2': str,             # Text field 2
    'name3': str,             # Text field 3
    'date_and_time': datetime, # Timestamp
    'somecontent': str,       # Content from detail page
    'somelinks': list,        # Extracted links
    'somedata': str           # Additional extracted data
}
```

## Functions

### Parsing
- `parse_html_table(raw_html)` - Extract table rows into elements_dict
- `parse_element_details(elem_id, raw_html)` - Extract detail page content
- `add_details_to_element(elem_id, details)` - Merge details into element

### Persistence
- `init_database(db_path)` - Create/connect to SQLite database
- `load_elements_from_db(cursor)` - Load existing elements
- `insert_elements(cursor, conn, elem_ids)` - Insert new elements
- `delete_elements(cursor, conn, elem_ids)` - Remove elements
- `update_element_data(cursor, conn, elem_id, data)` - Update field

### Retrieval
- `get_all_elements(cursor)` - Retrieve all elements
- `get_element_text_content(element)` - Combine text fields for embedding
