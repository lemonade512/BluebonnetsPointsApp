"""`main` is the top level module for your Flask application."""

# Import the Flask Framework
from flask import Flask, request, redirect, render_template
app = Flask(__name__)
# Note: We don't need to call run() since our application is embedded within
# the App Engine WSGI application server.

from google.appengine.api import users


@app.route('/')
def index():
    user = users.get_current_user()
    return render_template("index.html", user=user, logout=users.create_logout_url("/"))

@app.route('/admin')
def admin():
    #return "Welcome to the admin screen!"
    user = users.get_current_user()
    return render_template("admin.html", user=user, logout=users.create_logout_url("/"))

@app.route('/hello')
def hello():
    """Return a friendly HTTP greeting."""
    user = users.get_current_user()
    if user:
        return "Hello " + user.nickname()
    else:
        return redirect(users.create_login_url(request.url))


@app.errorhandler(404)
def page_not_found(e):
    """Return a custom 404 error."""
    return 'Sorry, Nothing at this URL.', 404


#@app.errorhandler(500)
#def application_error(e):
#    """Return a custom 500 error."""
#    return 'Sorry, unexpected error: {}'.format(e), 500
