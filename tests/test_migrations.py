import os
import subprocess
import sys
from datetime import datetime
from sqlalchemy import create_engine, inspect, text


def migrate(url, *args):
    env = {**os.environ, 'DATABASE_URL': url}
    return subprocess.run([sys.executable, '-m', 'alembic', *args], env=env, capture_output=True, text=True)


def successful(result):
    assert result.returncode == 0, result.stdout + result.stderr


def test_fresh_upgrade_matches_models_and_downgrades(tmp_path):
    url = 'sqlite:///' + str(tmp_path / 'fresh.db')
    successful(migrate(url, 'upgrade', 'head'))
    successful(migrate(url, 'check'))
    successful(migrate(url, 'downgrade', 'base'))
    engine = create_engine(url)
    assert set(inspect(engine).get_table_names()) == {'alembic_version'}
    engine.dispose()
    successful(migrate(url, 'upgrade', 'head'))


def test_legacy_upgrade_preserves_loans_and_repairs_inventory(tmp_path):
    url = 'sqlite:///' + str(tmp_path / 'legacy.db')
    successful(migrate(url, 'upgrade', 'f5ad6bab5c44'))
    engine = create_engine(url)
    with engine.begin() as connection:
        connection.execute(text("INSERT INTO users (id,name,email,password,isadmin) VALUES (1,'Member','MEMBER@example.com','hashed',null)"))
        connection.execute(text("INSERT INTO books (id,title,author,isbn,quantity,available,available_quantity) VALUES (1,'Book','Author','isbn',3,1,1)"))
        connection.execute(text("INSERT INTO borrowings (id,user_id,book_id,issue_date,returned) VALUES (1,1,1,'2026-01-01 00:00:00',0)"))
    successful(migrate(url, 'upgrade', 'head'))
    with engine.connect() as connection:
        assert connection.execute(text('SELECT available_quantity FROM books')).scalar_one() == 2
        assert connection.execute(text('SELECT email FROM users')).scalar_one() == 'member@example.com'
        due = connection.execute(text('SELECT due_date FROM borrowings')).scalar_one()
        assert datetime.fromisoformat(due) == datetime(2026, 1, 15)
    successful(migrate(url, 'check'))
    engine.dispose()


def test_duplicate_legacy_loans_fail_before_schema_changes(tmp_path):
    url = 'sqlite:///' + str(tmp_path / 'duplicates.db')
    successful(migrate(url, 'upgrade', 'f5ad6bab5c44'))
    engine = create_engine(url)
    with engine.begin() as connection:
        connection.execute(text("INSERT INTO users (id,name,email,password) VALUES (1,'Member','member@example.com','hashed')"))
        connection.execute(text("INSERT INTO books (id,title,author,isbn,quantity) VALUES (1,'Book','Author','isbn',3)"))
        for id in (1, 2):
            connection.execute(text('INSERT INTO borrowings (id,user_id,book_id,returned) VALUES (:id,1,1,0)'), {'id':id})
    result = migrate(url, 'upgrade', 'head')
    assert result.returncode != 0 and 'Duplicate active loans exist' in result.stderr
    assert 'due_date' not in {column['name'] for column in inspect(engine).get_columns('borrowings')}
    engine.dispose()
