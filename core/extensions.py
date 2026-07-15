from flask_login import LoginManager
from flask_wtf.csrf import CSRFProtect
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from core.database import Database

login_manager = LoginManager()
csrf = CSRFProtect()
limiter = Limiter(get_remote_address)
db_manager = Database()
