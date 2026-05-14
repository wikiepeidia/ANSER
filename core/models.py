# core/models.py
"""
Domain models for the application.

User is defined here (not in app.py) so that Blueprint files and route
handlers can import it without creating circular imports back to app.py.

Usage:
    from core.models import User
"""
from flask_login import UserMixin


class User(UserMixin):
    def __init__(self, id, email, first_name, last_name, role='user', google_token=None, avatar=None):
        self.id = id
        self.email = email
        self.first_name = first_name
        self.last_name = last_name
        self.role = role
        self.google_token = google_token
        self.avatar = avatar

    @property
    def name(self):
        return f"{self.first_name} {self.last_name}"
