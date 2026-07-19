import os
print('PORT:', os.environ.get('PORT', 'NOT SET'))
print('DATABASE_URL:', os.environ.get('DATABASE_URL', 'NOT SET')[:60] if os.environ.get('DATABASE_URL') else 'NOT SET')

from app import app
print('App loaded')

with app.test_client() as client:
    r = client.get('/')
    print('Status:', r.status_code)
    print('Location:', r.headers.get('Location'))
