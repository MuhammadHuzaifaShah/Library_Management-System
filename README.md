# Library Management System

A FastAPI backend for members, books, and borrowing, using PostgreSQL, SQLAlchemy, JWT authentication, and Alembic migrations. Interactive API documentation is available at `/docs` and `/redoc`.

## Features

- Register and log in; members manage their own accounts and administrators can manage all accounts.
- Administrator book creation, updates, deletion, and single-book lookup; authenticated catalog search and pagination.
- Borrow available copies, view personal borrowing history, and return books once.
- Configurable borrowing limit, due dates, overdue filters, and fines.
- Transactional PostgreSQL row locks prevent concurrent loans from overselling inventory or exceeding a member's limit.
- Database constraints, migration tests, API tests, and PostgreSQL concurrency tests.

## Setup on Windows (PowerShell)

Requires Python 3.10+ and a running PostgreSQL server. Python 3.12 is used in CI.

```powershell
git clone https://github.com/MuhammadHuzaifaShah/Library_Management-System.git
cd Library_Management-System
py -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
Copy-Item .env.example .env
.\.venv\Scripts\python.exe -c "import secrets; print(secrets.token_hex(32))"
```

Put the generated value in `SECRET_KEY` in `.env`. Set the database username, password, hostname, and port for your local PostgreSQL installation. Create an empty database named `library_management` using pgAdmin or:

```sql
CREATE DATABASE library_management;
```

Then initialize and start the application:

```powershell
.\.venv\Scripts\python.exe -m alembic upgrade head
.\.venv\Scripts\python.exe -m app.manage create-admin admin@example.com --name "Administrator"
.\.venv\Scripts\python.exe -m uvicorn app.main:app --reload
```

The admin command prompts for a password when creating an account; if the email already exists, it promotes that account without changing its password. This is a local operator command, not a public API endpoint.

Open http://127.0.0.1:8000/docs. Click **Authorize**, use your email in the **username** field, and enter your password. `/login` accepts form data, not JSON.

On Linux/macOS use `python3 -m venv .venv` and `.venv/bin/python` instead of the Windows executable path.

For a local single-user demo, set `DATABASE_URL=sqlite:///./library.db` in `.env` and run the same migration command. PostgreSQL is required for concurrent production use; SQLite does not implement the row locks used by the lending workflow. Application startup does not create or change database tables.

## Configuration

| Variable | Default / purpose |
| --- | --- |
| `DATABASE_URL` | Optional complete SQLAlchemy URL, overriding individual database settings |
| `DATABASE_HOSTNAME`, `DATABASE_PORT` | `localhost`, `5432` |
| `DATABASE_USERNAME`, `DATABASE_PASSWORD`, `DATABASE_NAME` | `postgres`, empty password, `library_management`; configure locally |
| `SECRET_KEY` | Required, at least 32 characters; generate a random value |
| `ALGORITHM` | `HS256`; also supports `HS384` and `HS512` |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | `60` |
| `LOAN_DAYS` | `14` |
| `MAX_ACTIVE_BORROWINGS` | `5` |
| `DAILY_FINE` | `10.00` currency units per started overdue 24-hour period |

Keep `.env` private. Older repository commits contained a database password; rotate that password if it is still used. It has been removed from the current source, but remains in Git history.

## API endpoints

| Method | Route | Access / behavior |
| --- | --- | --- |
| POST | `/users/` | Public member registration; cannot assign admin privileges |
| POST | `/login` | Email/password form login; returns bearer token |
| GET | `/users/me` | Current member profile; never returns password hashes |
| GET | `/users/` | Admin; `skip`, `limit` |
| GET, PUT, DELETE | `/users/{id}` | Account owner or admin; PUT replaces name, email, password |
| GET | `/books/` | Authenticated; `search`, `author`, `available`, `skip`, `limit` |
| POST | `/books/` | Admin; title, author, unique ISBN, nonnegative quantity |
| GET, PUT, DELETE | `/books/{id}` | Admin; PUT replaces book fields |
| POST | `/borrowings/` | Authenticated; JSON `{"book_id": 1}` |
| GET | `/borrowings/my` | Own history; `returned`, `overdue`, `skip`, `limit` |
| PUT | `/borrowings/{id}/return` | Borrowing owner; returns 200 and updated loan |
| GET | `/borrowings/` | Admin; `user_id`, `returned`, `overdue`, `skip`, `limit` |
| GET | `/health` | Database connectivity; 503 when unavailable |

List endpoints default to 20 items, with a maximum of 100. They return arrays ordered by ID. Invalid input returns 422, authentication failure 401, forbidden access 403, missing resources 404, and conflicting operations 409.

A book's `quantity` is total copies; `available_quantity` is unborrowed copies. Increasing or decreasing total quantity preserves checked-out copies. Books and users with borrowing history cannot be deleted, preserving that history. Return all copies and use a book quantity of zero to remove it from available inventory.

Borrowing responses include `due_date`, `fine_amount`, and `overdue`. An active loan's fine is a live estimate using the current `DAILY_FINE`. Returning the loan freezes its final fine. Exactly at the due date there is no fine; one second late counts as one overdue day. This project calculates fines; it does not process payments. Changing `LOAN_DAYS` affects new loans only.

## Existing database upgrade

Back up an existing database before migrating. The original migration ID `f5ad6bab5c44` is retained. A baseline predecessor now enables fresh installs.

- If `alembic current` reports `f5ad6bab5c44`, run `alembic upgrade head`.
- If tables were created by the old app with no Alembic version, inspect their schema first. If `books.available` is boolean and `books.available_quantity` exists, stamp `f5ad6bab5c44`, then upgrade. If availability is integer and `available_quantity` is absent, stamp `0001_baseline`, then upgrade. Do not stamp a revision unless the schema matches it.
- The upgrade preserves loans, normalizes email case, sets historical due dates to issue time plus 14 days, and reconciles available stock against active loans. If recorded total quantity is below the number of active loans, total quantity is raised to that number.
- Historical returned loans start with zero fine because the old system did not record fines. Active loans use the new policy.
- Duplicate active loans for the same member/book or emails differing only in case stop the upgrade with an error. Resolve these records explicitly and rerun; migration does not delete them.

Migrations require a live database connection. Downgrades remove due dates/fines and cannot reverse data normalization or inventory reconciliation.

## Tests

```powershell
.\.venv\Scripts\python.exe -m pip install -r requirements-dev.txt
.\.venv\Scripts\python.exe -m pytest -q
```

Default tests use disposable SQLite databases, including a fresh migration round trip, model/schema comparison, and a legacy data upgrade. PostgreSQL-only concurrency tests are skipped without `TEST_DATABASE_URL`.

To test PostgreSQL, create a **separate empty test database**, then set `TEST_DATABASE_URL` to its URL and run `python -m pytest -q`. The test suite creates and drops application tables in that database. Never point it at a database containing data you need. GitHub Actions runs the suite on SQLite and PostgreSQL and verifies PostgreSQL migration upgrades/downgrades.

Import `postman/Library_Management.postman_collection.json` into Postman for a guided register → login → create book → borrow → return sequence. Set its email/password variables locally. Run the admin provisioning command for the registered email before trying admin requests. The collection captures token, book ID, and borrowing ID from responses automatically.
