def test_frontend_and_assets_are_served(client):
    response = client.get('/')
    assert response.status_code == 200
    assert 'text/html' in response.headers['content-type']
    assert 'Leaf' in response.text
    assert '/assets/app.js' in response.text
    assert client.get('/assets/style.css').status_code == 200
    assert client.get('/assets/app.js').status_code == 200
    assert client.get('/docs').status_code == 200
    assert client.get('/assets/../../config.py').status_code == 404
