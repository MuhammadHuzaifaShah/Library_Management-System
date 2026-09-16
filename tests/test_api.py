from datetime import datetime, timedelta, timezone
from decimal import Decimal
import pytest
from jose import jwt
from app import models
from app.config import settings
from app.routers.borrowings import fine_at


def book(client, accounts, quantity=2, isbn='978-1234567890', title='Python Basics'):
    response = client.post('/books/', headers=accounts['admin']['headers'],
                           json={'title': title, 'author': 'Shah', 'isbn': isbn, 'quantity': quantity})
    assert response.status_code == 201, response.text
    return response.json()


def borrow(client, accounts, book_id, member='alice'):
    return client.post('/borrowings/', headers=accounts[member]['headers'], json={'book_id': book_id})


def test_health_and_openapi(client):
    assert client.get('/health').json() == {'status': 'ok'}
    assert client.get('/').status_code == 200
    assert '/borrowings/{id}/return' in client.get('/openapi.json').json()['paths']


def test_accounts_are_private_and_never_expose_passwords(client, accounts):
    alice = accounts['alice']
    assert client.get('/users/').status_code == 401
    assert client.get('/users/', headers=alice['headers']).status_code == 403
    assert client.get('/users/', headers=accounts['admin']['headers']).status_code == 200
    me = client.get('/users/me', headers=alice['headers'])
    assert me.status_code == 200 and 'password' not in me.json()
    for method in ('get', 'delete'):
        assert getattr(client, method)(f"/users/{accounts['bob']['id']}", headers=alice['headers']).status_code == 403
    payload = {'name': 'New', 'email': 'alice@example.com', 'password': 'NewStrongPass123!'}
    assert client.put(f"/users/{accounts['bob']['id']}", headers=alice['headers'], json=payload).status_code == 403
    updated = client.put(f"/users/{alice['id']}", headers=alice['headers'], json=payload)
    assert updated.status_code == 200 and 'password' not in updated.json()
    assert client.post('/login', data={'username': 'alice@example.com', 'password': 'NewStrongPass123!'}).status_code == 200


def test_duplicate_and_invalid_registration(client, accounts):
    payload = {'name': 'Alice', 'email': 'ALICE@example.com', 'password': 'StrongPass123!'}
    assert client.post('/users/', json=payload).status_code == 409
    payload['email'] = 'new@example.com'
    payload['isadmin'] = True
    assert client.post('/users/', json=payload).status_code == 422
    del payload['isadmin']
    payload['password'] = 'é' * 40
    assert client.post('/users/', json=payload).status_code == 422
    payload['password'] = 'short'
    assert client.post('/users/', json=payload).status_code == 422
    assert client.post('/login', data={'username': 'alice@example.com', 'password': 'wrong'}).status_code == 401
    assert client.post('/login', data={'username': 'ALICE@example.com', 'password': 'StrongPass123!'}).status_code == 200


@pytest.mark.parametrize('payload', [
    {'user_id': {'invalid': 1}, 'exp': 9999999999},
    {'user_id': 1, 'exp': 1}, {'user_id': 1}, {'exp': 9999999999},
])
def test_invalid_tokens_return_401(client, payload):
    token = jwt.encode(payload, settings.secret_key, algorithm=settings.algorithm)
    assert client.get('/users/me', headers={'Authorization': f'Bearer {token}'}).status_code == 401


def test_book_permissions_search_and_validation(client, accounts):
    first = book(client, accounts, quantity=3)
    assert first['available_quantity'] == 3
    empty = book(client, accounts, quantity=0, isbn='empty', title='Unavailable')
    assert not empty['available']
    headers = accounts['alice']['headers']
    assert client.get(f"/books/{first['id']}", headers=headers).status_code == 403
    assert client.post('/books/', headers=headers, json={'title':'X', 'author':'Y', 'isbn':'Z', 'quantity':1}).status_code == 403
    assert client.delete(f"/books/{first['id']}", headers=headers).status_code == 403
    result = client.get('/books/?search=python&author=shah&available=true', headers=headers).json()
    assert [b['id'] for b in result] == [first['id']]
    assert len(client.get('/books/?limit=1&skip=1', headers=headers).json()) == 1
    assert client.get('/books/?limit=0', headers=headers).status_code == 422
    payload = {'title':'X', 'author':'Y', 'isbn':first['isbn'], 'quantity':1}
    assert client.post('/books/', headers=accounts['admin']['headers'], json=payload).status_code == 409
    payload['quantity'] = -1
    assert client.post('/books/', headers=accounts['admin']['headers'], json=payload).status_code == 422


def test_borrow_return_stock_and_history(client, accounts):
    b = book(client, accounts, quantity=1)
    loan = borrow(client, accounts, b['id'])
    assert loan.status_code == 201
    data = loan.json()
    assert data['due_date'] and Decimal(data['fine_amount']) == 0
    assert borrow(client, accounts, b['id']).status_code == 409
    assert borrow(client, accounts, b['id'], 'bob').status_code == 409
    assert client.get('/borrowings/', headers=accounts['alice']['headers']).status_code == 403
    assert client.get('/borrowings/my', headers=accounts['bob']['headers']).json() == []
    assert client.put(f"/borrowings/{data['id']}/return", headers=accounts['bob']['headers']).status_code == 404
    assert client.delete(f"/books/{b['id']}", headers=accounts['admin']['headers']).status_code == 409
    assert client.delete(f"/users/{accounts['alice']['id']}", headers=accounts['alice']['headers']).status_code == 409
    returned = client.put(f"/borrowings/{data['id']}/return", headers=accounts['alice']['headers'])
    assert returned.status_code == 200 and returned.json()['returned']
    assert client.put(f"/borrowings/{data['id']}/return", headers=accounts['alice']['headers']).status_code == 409
    assert client.get(f"/books/{b['id']}", headers=accounts['admin']['headers']).json()['available_quantity'] == 1
    assert borrow(client, accounts, b['id']).status_code == 201


def test_quantity_update_preserves_checked_out_copies(client, accounts):
    b = book(client, accounts, quantity=2)
    borrow(client, accounts, b['id'])
    payload = {k: b[k] for k in ('title','author','isbn','quantity')}
    payload['quantity'] = 0
    assert client.put(f"/books/{b['id']}", headers=accounts['admin']['headers'], json=payload).status_code == 409
    payload['quantity'] = 4
    result = client.put(f"/books/{b['id']}", headers=accounts['admin']['headers'], json=payload)
    assert result.status_code == 200 and result.json()['available_quantity'] == 3


def test_borrow_limit(client, accounts, monkeypatch):
    monkeypatch.setattr(settings, 'max_active_borrowings', 1)
    one = book(client, accounts, isbn='one')
    two = book(client, accounts, isbn='two')
    loan = borrow(client, accounts, one['id']).json()
    assert borrow(client, accounts, two['id']).status_code == 409
    client.put(f"/borrowings/{loan['id']}/return", headers=accounts['alice']['headers'])
    assert borrow(client, accounts, two['id']).status_code == 201


def test_overdue_fine_and_filters(client, accounts, database):
    b = book(client, accounts)
    loan = borrow(client, accounts, b['id']).json()
    with database() as db:
        db.get(models.Borrowing, loan['id']).due_date = datetime.now(timezone.utc) - timedelta(days=2, hours=1)
        db.commit()
    rows = client.get('/borrowings/my?overdue=true', headers=accounts['alice']['headers']).json()
    assert len(rows) == 1 and rows[0]['overdue']
    assert Decimal(rows[0]['fine_amount']) == settings.daily_fine * 3
    returned = client.put(f"/borrowings/{loan['id']}/return", headers=accounts['alice']['headers']).json()
    assert Decimal(returned['fine_amount']) == settings.daily_fine * 3
    assert not returned['overdue']
    assert client.get('/borrowings/my?overdue=true', headers=accounts['alice']['headers']).json() == []
    assert len(client.get('/borrowings/?returned=true', headers=accounts['admin']['headers']).json()) == 1


def test_fine_boundaries():
    due = datetime(2026, 1, 1, tzinfo=timezone.utc)
    record = models.Borrowing(due_date=due)
    assert fine_at(record, due) == 0
    assert fine_at(record, due - timedelta(seconds=1)) == 0
    assert fine_at(record, due + timedelta(seconds=1)) == settings.daily_fine
    assert fine_at(record, due + timedelta(days=1)) == settings.daily_fine
    assert fine_at(record, due + timedelta(days=1, seconds=1)) == settings.daily_fine * 2


def test_delete_unused_records_and_deleted_user_token(client, accounts):
    b = book(client, accounts)
    assert client.delete(f"/books/{b['id']}", headers=accounts['admin']['headers']).status_code == 204
    assert client.get(f"/books/{b['id']}", headers=accounts['admin']['headers']).status_code == 404
    assert client.delete(f"/users/{accounts['bob']['id']}", headers=accounts['bob']['headers']).status_code == 204
    assert client.get('/users/me', headers=accounts['bob']['headers']).status_code == 401
