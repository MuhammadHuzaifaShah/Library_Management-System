import os
os.environ['SECRET_KEY'] = 'test-only-secret-key-that-is-at-least-32-characters'
os.environ['DATABASE_URL'] = os.environ.get('TEST_DATABASE_URL', 'sqlite://')

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool
from app.database import Base, get_db
from app.main import app
from app import models, utils


@pytest.fixture
def database():
    url = os.environ['DATABASE_URL']
    sqlite = url.startswith('sqlite')
    engine = create_engine(url, **({'connect_args': {'check_same_thread': False}, 'poolclass': StaticPool} if sqlite else {}))
    if sqlite:
        @event.listens_for(engine, 'connect')
        def fk(connection, _):
            connection.execute('PRAGMA foreign_keys=ON')
    Base.metadata.create_all(engine)
    factory = sessionmaker(bind=engine)
    yield factory
    Base.metadata.drop_all(engine)
    engine.dispose()


@pytest.fixture
def client(database):
    def override():
        with database() as db:
            yield db
    app.dependency_overrides[get_db] = override
    with TestClient(app) as client:
        yield client
    app.dependency_overrides.clear()


@pytest.fixture
def accounts(client, database):
    password = 'StrongPass123!'
    users = {}
    for name in ('admin', 'alice', 'bob'):
        response = client.post('/users/', json={'name': name, 'email': f'{name}@example.com', 'password': password})
        assert response.status_code == 201, response.text
        users[name] = response.json()
    with database() as db:
        db.get(models.User, users['admin']['id']).isadmin = True
        db.commit()
    for name in users:
        response = client.post('/login', data={'username': f'{name}@example.com', 'password': password})
        assert response.status_code == 200, response.text
        users[name]['headers'] = {'Authorization': 'Bearer ' + response.json()['access_token']}
    return users
