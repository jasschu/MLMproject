from functools import wraps
from flask import redirect,session

def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if session.get("id") is None:
            return redirect('/')
        return f(*args, **kwargs)
    return decorated_function

#validate form data
def form_filled(form_data):
    for field in form_data:
        print(field,form_data[field])
        if not form_data[field]:
            return False
    return True

    