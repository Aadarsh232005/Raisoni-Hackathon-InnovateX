from functools import wraps
from flask import session, redirect, url_for, flash

users = [
    {"id": 1, "username": "admin",   "password": "admin123",  "role": "ADMIN",   "name": "System Admin"},
    {"id": 2, "username": "doctor1", "password": "doctor123", "role": "DOCTOR",  "name": "Dr. Priya Sharma",  "doctor_id": 1},
    {"id": 3, "username": "doctor2", "password": "doctor123", "role": "DOCTOR",  "name": "Dr. Arjun Mehta",   "doctor_id": 2},
    {"id": 4, "username": "patient", "password": "pass123",   "role": "PATIENT", "name": "Demo Patient", "phone": "9999999999"},
]

def authenticate(username, password):
    return next((u for u in users if u["username"] == username and u["password"] == password), None)

def register_user(username, password, name, phone):
    if any(u["username"] == username for u in users):
        return None, "Username already exists."
    user = {"id": len(users)+1, "username": username, "password": password,
            "role": "PATIENT", "name": name, "phone": phone}
    users.append(user)
    return user, None

def login_required(f):
    @wraps(f)
    def wrapped(*a, **kw):
        if "user_id" not in session:
            return redirect(url_for("login"))
        return f(*a, **kw)
    return wrapped

def role_required(*roles):
    def decorator(f):
        @wraps(f)
        def wrapped(*a, **kw):
            if "user_id" not in session:
                return redirect(url_for("login"))
            if session.get("role") not in roles:
                flash("Access denied for your role.", "danger")
                return redirect(url_for("login"))
            return f(*a, **kw)
        return wrapped
    return decorator