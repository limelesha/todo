import flask

from . import models


app = flask.Flask(__name__)


@app.route('/')
def hello():
    return 'Hello, world!'
