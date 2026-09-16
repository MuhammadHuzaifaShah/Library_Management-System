"""Real row-lock tests; run against a disposable PostgreSQL TEST_DATABASE_URL."""
import os
from concurrent.futures import ThreadPoolExecutor
import pytest
from fastapi.testclient import TestClient
from app.main import app
from app import models
from app.config import settings
from tests.test_api import book, borrow

pytestmark = pytest.mark.skipif(not os.environ.get('TEST_DATABASE_URL', '').startswith('postgresql'), reason='PostgreSQL required for row locks')


def parallel_requests(requests):
    def perform(request):
        method, url, headers, data = request
        with TestClient(app) as worker:
            return worker.request(method, url, headers=headers, json=data)
    with ThreadPoolExecutor(max_workers=len(requests)) as workers:
        return list(workers.map(perform, requests))


def test_last_copy_cannot_be_borrowed_twice(client, accounts, database):
    b = book(client, accounts, quantity=1)
    responses = parallel_requests([
        ('POST', '/borrowings/', accounts[name]['headers'], {'book_id': b['id']})
        for name in ('alice', 'bob')
    ])
    assert sorted(r.status_code for r in responses) == [201, 409]
    with database() as db:
        assert db.get(models.Book, b['id']).available_quantity == 0
        assert db.query(models.Borrowing).count() == 1


def test_parallel_returns_increment_stock_once(client, accounts, database):
    b = book(client, accounts, quantity=1)
    loan = borrow(client, accounts, b['id']).json()
    request = ('PUT', f"/borrowings/{loan['id']}/return", accounts['alice']['headers'], None)
    responses = parallel_requests([request, request])
    assert sorted(r.status_code for r in responses) == [200, 409]
    with database() as db:
        assert db.get(models.Book, b['id']).available_quantity == 1


def test_parallel_loans_respect_member_limit(client, accounts, monkeypatch):
    monkeypatch.setattr(settings, 'max_active_borrowings', 1)
    books = [book(client, accounts, isbn=str(n)) for n in range(2)]
    responses = parallel_requests([
        ('POST', '/borrowings/', accounts['alice']['headers'], {'book_id': b['id']}) for b in books
    ])
    assert sorted(r.status_code for r in responses) == [201, 409]
