import functools
import secrets

import flask
import sqlalchemy

from . import models


app = flask.Flask(__name__)
app.secret_key = secrets.token_hex()

database = models.Database("sqlite:///data.db")


def require_login(func):
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        if 'user_id' in flask.session:
            return func(*args, **kwargs)
        else:
            flask.abort(401)
    return wrapper


def get_access_level(user, project) -> models.AccessLevel:
    statement = (
        sqlalchemy.select(models.Membership)
        .where(
            sqlalchemy.and_(
                models.Membership.user == user,
                models.Membership.project == project
            )
        )
    )
    with database.new_session() as session:
        membership = session.scalar(statement)
    if membership is None:
        flask.abort(403)  # not a member
    return membership.access_level


# TODO:
# - validate input data in create and update methods with some validation
#   library like marshmallow
# - validate email in user creation and update methods
# - remove projects when there is no one left in the team
# - when querying from the database, use a method other than `get` which will
#   raise an exception when the record cannot be found instead of returning
#   None, then learn how to handle such exceptions to abort with 404
# - add `leave` method that would allows members of the team to leave without
#   others' permission


@app.post('/login/')
def login():
    with database.new_session() as session:
        user = session.scalar(
            sqlalchemy.select(models.User)
            .where(models.User.email == flask.request.form['email'])
        )
        if user is None:
            flask.abort(404)
        if user.verify_password(flask.request.form['password']):
            flask.session['user_id'] = user.id
            return "OK", 200
        else:
            flask.abort(403)


# task-related api

@app.post('/task/')
@require_login
def create_task():
    with database.new_session() as session:
        project = session.get(models.Project, flask.request.json['project_id'])
        client_user = session.get(models.User, flask.session['user_id'])
        if project is None or client_user is None:
            flask.abort(404)
        if get_access_level(client_user, project) >= models.AccessLevel.EDITOR:
            task = models.Task(**flask.request.json)
            session.add(task)
            session.flush()
            repr = task.full_repr()
            session.commit()
        else:
            flask.abort(403)
    return repr


@app.get('/task/<int:task_id>')
@require_login
def get_task(task_id: int):
    with database.new_session() as session:
        client_user = session.get(models.User, flask.session['user_id'])
        task = session.get(models.Task, task_id)
        if client_user is None or task is None:
            flask.abort(404)
        if client_user in task.project.team:
            return task.full_repr()
        else:
            flask.abort(403)


@app.patch('/task/<int:task_id>')
@require_login
def update_task(task_id: int):
    with database.new_session() as session:
        client_user = session.get(models.User, flask.session['user_id'])
        task = session.get(models.Task, task_id)
        if client_user is None or task is None:
            flask.abort(404)
        if get_access_level(client_user, task.project) >= models.AccessLevel.EDITOR:
            assert isinstance(flask.request.json, dict)
            for key, value in flask.request.json.items():
                if key in ['title', 'description', 'due_timestamp', 'is_done']:
                    setattr(task, key, value)
            session.flush()
            repr = task.full_repr()
            session.commit()
            return repr


@app.delete('/task/<int:task_id>')
@require_login
def delete_task(task_id: int):
    with database.new_session() as session:
        client_user = session.get(models.User, flask.session['user_id'])
        task = session.get(models.Task, task_id)
        if client_user is None or task is None:
            flask.abort(404)
        if get_access_level(client_user, task.project) >= models.AccessLevel.EDITOR:
            session.delete(task)
            session.commit()
            return "OK", 200
        else:
            flask.abort(403)


# project-related api

@app.post('/project/')
@require_login
def create_project():
    with database.new_session() as session:
        client_user = session.get(models.User, flask.session['user_id'])
        if client_user is None:
            flask.abort(404)
        project = models.Project(**flask.request.json)
        membership = models.Membership(
            user=client_user,
            project=project,
            access_level_int=models.AccessLevel.MANAGER.real
        )
        session.add_all([project, membership])
        session.flush()
        repr = project.full_repr()
        session.commit()
    return repr


@app.get('/project/<int:project_id>')
@require_login
def get_project(project_id: int):
    with database.new_session() as session:
        client_user = session.get(models.User, flask.session['user_id'])
        project = session.get(models.Project, project_id)
        if client_user is None or project is None:
            flask.abort(404)
        if client_user in project.team:
            return project.full_repr()
        else:
            flask.abort(403)


@app.patch('/project/<int:project_id>')
def update_project(project_id: int):
    with database.new_session() as session:
        client_user = session.get(models.User, flask.session['user_id'])
        project = session.get(models.Project, project_id)
        if client_user is None or project is None:
            flask.abort(404)
        if get_access_level(client_user, project) >= models.AccessLevel.MANAGER:
            assert isinstance(flask.request.json, dict)
            for key, value in flask.request.json.items():
                if key in ['title', 'default_access_level_int']:
                    setattr(project, key, value)
            session.flush()
            repr = project.full_repr()
            session.commit()
            return repr


@app.delete('/project/<int:project_id>')
@require_login
def delete_project(*, project_id: int):
    with database.new_session() as session:
        client_user = session.get(models.User, flask.session['user_id'])
        project = session.get(models.Project, project_id)
        if client_user is None or project is None:
            flask.abort(404)
        if get_access_level(client_user, project) >= models.AccessLevel.MANAGER:
            session.delete(project)
            session.commit()
            return "OK", 200


# user-related api

@app.post('/user/')
def create_user():
    # TODO: verify email
    with database.new_session() as session:
        user = models.User.create_with_cleartext_password(**flask.request.json)
        session.add(user)
        session.flush()
        repr = user.full_repr()
        session.commit()
    return repr


@app.get('/user/<int:user_id>')
@require_login
def get_user(*, user_id: int):
    with database.new_session() as session:
        target_user = session.get(models.User, user_id)
        if target_user is None:
            flask.abort(404)
        return target_user.full_repr()


@app.patch('/user/')
@require_login
def update_user():
    with database.new_session() as session:
        client_user = session.get(models.User, flask.session['user_id'])
        if client_user is None:
            flask.abort(404)
        assert isinstance(flask.request.json, dict)
        for key, value in flask.request.json.items():
            if key in ['name', 'email']:
                setattr(client_user, key, value)
        session.flush()
        repr = client_user.full_repr()
        session.commit()
    return repr


@app.delete('/user/')
@require_login
def delete_user():
    with database.new_session() as session:
        client_user = session.get(models.User, flask.session['user_id'])
        if client_user is None:
            flask.abort(404)
        del flask.session['user_id']
        session.delete(client_user)
        session.commit()
    return "OK", 200


# project-related actions api

@app.post('/invite/<int:project_id>')
@require_login
def invite(project_id: int):
    with database.new_session() as session:
        client_user = session.get(models.User, flask.session['user_id'])
        project = session.get(models.Project, project_id)
        if client_user is None or project is None:
            flask.abort(404)
        if get_access_level(client_user, project) >= models.AccessLevel.MANAGER:
            assert isinstance(flask.request.json, list)
            party = [session.get(models.User, user_id) for user_id in flask.request.json]
            project.team.update(party)
            session.flush()
            repr = project.full_repr()
            session.commit()
            return repr


@app.post('/kick/<int:project_id>')
@require_login
def kick(project_id: int):
    with database.new_session() as session:
        client_user = session.get(models.User, flask.session['user_id'])
        project = session.get(models.Project, project_id)
        if client_user is None or project is None:
            flask.abort(404)
        if get_access_level(client_user, project) >= models.AccessLevel.MANAGER:
            assert isinstance(flask.request.json, list)
            party = [session.get(models.User, user_id) for user_id in flask.request.json]
            project.team.difference_update(party)
            session.flush()
            repr = project.full_repr()
            session.commit()
            return repr
