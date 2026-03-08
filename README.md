# Salt-Mine: Generic Medicine Mapper

Flask-based DBMS project that maps branded medicines to chemically identical alternatives and highlights low-cost Jan Aushadhi options.

## Tech Stack

- Python + Flask
- SQL backend (MySQL supported via SQLAlchemy + PyMySQL, SQLite default for local run)
- TXT fallback backend for redundancy if SQL backend fails
- HTML, CSS, JavaScript frontend

## Core DBMS Concepts Used

- Normalized relational schema (`brands`, `salts`, `brand_salts`)
- Many-to-Many mapping between brands and salts
- Subquery-based exact composition matching logic
- Indexed columns for faster retrieval and price sorting

## Project Structure

```text
app.py
schema.sql
seed.sql
requirements.txt
services/
  sql_backend.py
  txt_backend.py
data/fallback/
  brands.txt
  salts.txt
  brand_salts.txt
templates/
  index.html
static/
  css/styles.css
  js/app.js
```

## Setup

```bash
pip install -r requirements.txt
```

## Run (Default SQLite SQL Backend)

```bash
python app.py
```

Open `http://127.0.0.1:5000`.

On first run with SQLite, the app auto-creates and seeds `salt_mine.db` from `schema.sql` + `seed.sql`.

## Run with MySQL Backend

Set `DATABASE_URL` before starting app:

```bash
set DATABASE_URL=mysql+pymysql://username:password@localhost:3306/salt_mine
python app.py
```

Create schema and seed data in MySQL using `schema.sql` and `seed.sql`.

## TXT Redundancy Mode

If SQL backend is unreachable or query execution fails, `/api/search` automatically falls back to:

- `data/fallback/brands.txt`
- `data/fallback/salts.txt`
- `data/fallback/brand_salts.txt`

The API response includes `backend_used` with values:

- `sql`
- `txt-fallback`

## Sample Search Inputs

- `Crocin Advance 500`
- `Augmentin 625`
- `Glycomet-GP 1`
- `Coughnil Forte`

## Health Endpoint

`GET /api/health`

Returns backend availability status for quick monitoring.
