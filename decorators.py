from functools import wraps
from flask import g, redirect, flash

def login_required(f):
    @wraps(f)
    def login(*args, **kwargs):
        if not g.user:
            flash("Access unauthorized.", "danger")
            return redirect("/")
        return f(*args, **kwargs)
    return login
            