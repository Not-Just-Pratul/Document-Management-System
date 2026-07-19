import os
print('PORT:', os.environ.get('PORT', 'NOT SET'))
print('DATABASE_URL:', os.environ.get('DATABASE_URL', 'NOT SET')[:60] if os.environ.get('DATABASE_URL') else 'NOT SET')
print('SECRET_KEY:', os.environ.get('SECRET_KEY', 'NOT SET'))
print('FLASK_ENV:', os.environ.get('FLASK_ENV', 'NOT SET'))

try:
    import psycopg2
    url = os.environ.get('DATABASE_URL')
    if url:
        print('Connecting to DB...')
        conn = psycopg2.connect(url, connect_timeout=10)
        print('DB connection OK')
        conn.close()
    else:
        print('No DATABASE_URL')
except Exception as e:
    print('DB error:', e)

try:
    from app import app
    print('App import OK')
except Exception as e:
    print('App import error:', e)
    import traceback
    traceback.print_exc()
