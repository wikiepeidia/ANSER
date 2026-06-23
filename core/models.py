# core/models.py
"""
Model miền cho ứng dụng.

User được định nghĩa ở đây (không phải trong app.py) để các tệp Blueprint và
route handler có thể import mà không tạo vòng import ngược về app.py.

Cách dùng:
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
