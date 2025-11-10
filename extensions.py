from flask_seasurf import SeaSurf
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address

csrf = SeaSurf()
limiter = Limiter(key_func=get_remote_address) # Initialize without app here

def init_app(app):
    csrf.init_app(app)
    limiter.init_app(app) # Initialize limiter with app here
