import functools
import secrets

import flask
import sqlalchemy

from . import models


app = flask.Flask(__name__)
app.secret_key = secrets.token_hex()

database = models.Database("sqlite:///:memory:")


# def unpack_request_body(func):
#     @functools.wraps(func)
#     def wrapper(*args, **kwargs):
#         return func(*args, **kwargs, **flask.request.get_json)
#     return wrapper


def update_instance_from_dict(obj, values: dict) -> None:
    for key, value in values.items():
        setattr(obj, key, value)


def require_login(func):
    """Decorator that checks whether a user is logged in."""
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        if 'user_id' in flask.session:
            return func(*args, **kwargs)
        flask.abort(403)  # TODO: otherwise, redirect to login page
    return wrapper


def require_self(func):
    """Decorator that ensures that user related actions are performed only by that user."""
    @functools.wraps(func)
    def wrapper(*, user_id, **kwargs):
        if flask.session.user_id == user_id:
            return func(user_id=user_id, **kwargs)
        else:
            flask.abort(403)
    return wrapper


def require_access_level(required_access_level: models.AccessLevel):
    """Decorator that ckecks whether a user has a sufficient access level to perform a project related action."""
    def decorator(func):
        @functools.wraps(func)
        def wrapper(*, project_id, **kwargs):
            with database.new_session() as session:
                membership = session.scalar(
                    sqlalchemy.select(models.Membership)
                    .where(
                        sqlalchemy.and_(
                            models.Membership.user_id == flask.session.user_id,
                            models.Membership.project_id == project_id
                        )
                    )
                )
                if membership is None:
                    flask.abort(403)  # not a member
                user_access_level = membership.access_level
                if user_access_level == required_access_level:
                    return func(project_id=project_id, **kwargs)
        return wrapper
    return decorator


# having at least some access level means being a member
# so, membership requirement is identical to a requirement of having at least the lowest access level
require_member = require_access_level(models.AccessLevel.READER)


@app.get('/task/<int:task_id>')
def get_task(*, task_id: int):
    with database.new_session() as session:
        task = session.get(models.Task, task_id)
        if session.get(models.User, flask.session.user_id) not in task.project.team:
            flask.abort(403)
        return task.as_dict()


@app.delete('/task/<int:task_id>')
def delete_task(*, task_id: int):
    with database.new_session() as session:
        session.delete(session.get(models.Task, task_id))
        session.commit()
    return "OK", 200


@app.post('/task/')
def create_task(project_id: int,
                supertask_id: int | None = None,
                title: str | None = None,
                description: str | None = None,
                due_timestamp: float| None = None):
    task = models.Task(project_id=project_id,
                       supertask_id=supertask_id,
                       title=title,
                       description=description,
                       due_timestamp=due_timestamp)
    with database.new_session() as session:
        session.add(task)
        session.commit()
    return "OK", 200


@app.patch('/task/<int:task_id>')
def update_task(*, task_id: int):
    with database.new_session() as session:
        task = session.scalar(sqlalchemy.select(models.Task).where(models.Task.id == task_id))
        update_instance_from_dict(task, flask.request.json)
        session.commit()
    return "OK", 200


@app.get('/project/<int:project_id>')
@require_member
def get_project(*, project_id: int):
    with database.new_session() as session:
        project = session.get(models.Project, project_id)
        return project.as_dict()


@app.patch('/project/<int:project_id>')
@require_access_level(models.AccessLevel.MANAGER)
def update_project(*, project_id: int):
    with database.new_session() as session:
        project = session.scalar(sqlalchemy.select(models.Project).where(models.Project.id == project_id))
        update_instance_from_dict(project, flask.request.json)
        session.commit()
    return "OK", 200


@app.delete('/project/<int:project_id>')
@require_access_level(models.AccessLevel.MANAGER)
def delete_project(*, project_id: int):
    with database.new_session() as session:
        session.delete(session.get(models.Project, project_id))
        session.commit()
    return "OK", 200


@app.get('/user/<int:user_id>')
def get_user(*, user_id: int):
    with database.new_session() as session:
        user = session.get(models.User, user_id)
        return user.as_dict()


@app.post('/user/')
def create_user(name: str, email: str, cleartext_password: str):
    # TODO: verify email
    user = models.User.create_with_cleartext_password(name=name,
                                                      email=email,
                                                      cleartext_password=cleartext_password)
    with database.new_session() as session:
        session.add(user)
        session.commit()
    return "OK", 200


@app.patch('/user/<int:user_id>')
@require_self
def update_user(*, user_id: int):
    with database.new_session() as session:
        user = session.scalar(
            sqlalchemy.select(models.User)
            .where(models.User.id == user_id)
        )
        update_instance_from_dict(user, flask.request.json)
        session.commit()
    return "OK", 200


@app.delete('/user/<int:user_id>')
@require_self
def delete_user(*, user_id: int):
    with database.new_session() as session:
        session.delete(session.get(models.User, user_id))
        session.commit()
    return "OK", 200


@app.post('/invite/<int:project_id>')
@require_access_level(models.AccessLevel.MANAGER)
def invite(*, project_id: int):
    with database.new_session() as session:
        project = session.get(models.Project, project_id)
        party = [session.get(models.User, user_id) for user_id in flask.request.json]
        project.team.update(party)
        session.commit()
    return "OK", 200


@app.post('/kick/<int:project_id>')
@require_access_level(models.AccessLevel.MANAGER)
def kick(*, project_id: int):
    with database.new_session() as session:
        project = session.get(models.Project, project_id)
        party = [session.get(models.User, user_id) for user_id in flask.request.json]
        project.team.difference_update(party)
    return "OK", 200
