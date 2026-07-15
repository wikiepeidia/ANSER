"""User model — same shape as ANSER's core/models.py so a decoded shared
session cookie maps onto an equivalent object here."""
from flask_login import UserMixin


class User(UserMixin):
    def __init__(self, id, email, first_name, last_name, role='user', avatar=None):
        self.id = id
        self.email = email
        self.first_name = first_name
        self.last_name = last_name
        self.role = role
        self.avatar = avatar

    @property
    def name(self):
        return f"{self.first_name} {self.last_name}".strip()
