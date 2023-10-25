import enum
import textwrap
import typing

import argon2
import sqlalchemy
from sqlalchemy import orm
from sqlalchemy.orm import Mapped


class AccessLevel(enum.IntEnum):
    """Access levels of a user to a project.

    Constants that describe the access level (and corresponding
    permissions) of a user in a project. Relevent in shared lists to
    limit permissions of invited users."""

    READER = enum.auto()  # this access level grants permission to read the contents of a project
    EDITOR = enum.auto()  # edit project contents, that is add and remove tasks, change task status, edit task details
    MANAGER = enum.auto()  # manage a project itself, like rename, delete and manage the team


class Base(orm.DeclarativeBase):
    pass


class Task(Base):
    """A single task entry in a project."""
    __tablename__ = 'task'

    # internal exposed fields
    id: Mapped[int] = orm.mapped_column(primary_key=True)

    # userland relations fields
    project_id: Mapped[int] = orm.mapped_column(sqlalchemy.ForeignKey("project.id"))
    supertask_id: Mapped[int | None] = orm.mapped_column(sqlalchemy.ForeignKey("task.id"))

    # userland raw data fields
    title: Mapped[str] = orm.mapped_column()
    description: Mapped[str | None] = orm.mapped_column()
    due_timestamp: Mapped[float | None] = orm.mapped_column()
    is_done: Mapped[bool] = orm.mapped_column(default=False)

    # orm relationships
    project: Mapped["Project"] = orm.relationship(back_populates="tasks")
    subtasks: Mapped[list["Task"]] = orm.relationship(back_populates="supertask")
    supertask: Mapped["Task"] = orm.relationship(back_populates="subtasks", remote_side=[id])

    def __repr__(self):
        return f"Task(id={self.id!r}"\
               f", project_id={self.project_id!r}"\
               f", supertask_id={self.supertask_id!r}"\
               f", title={self.title!r}"\
               f", description={(self.description and textwrap.shorten(self.description, 24))!r}"\
               f", due_timestamp={self.due_timestamp!r}"\
               f", is_done={self.is_done!r})"

    def shallow_repr(self) -> dict:
        return {
            "id": self.id,
            "title": self.title,
            "description": self.description,
            "due_timestamp": self.due_timestamp,
            "is_done": self.is_done,
            "subtasks": [task.as_dict() for task in self.subtasks],
        }

    def full_repr(self) -> dict:
        return {
            "id": self.id,
            "project_id": self.project_id,
            "title": self.title,
            "description": self.description,
            "due_timestamp": self.due_timestamp,
            "is_done": self.is_done,
            "subtasks": [task.as_dict() for task in self.subtasks],
        }


class Project(Base):
    """Project is a container of tasks."""
    __tablename__ = 'project'

    # internal exposed fields
    id: Mapped[int] = orm.mapped_column(primary_key=True)

    # userland raw data fields
    title: Mapped[str] = orm.mapped_column()
    default_access_level_int: Mapped[int] = orm.mapped_column(default=AccessLevel.READER.real)

    # orm relationships
    tasks: Mapped[list["Task"]] = orm.relationship(back_populates="project")
    team: Mapped[set["Membership"]] = orm.relationship(back_populates="project")

    def __repr__(self):
        return f"Project(id={self.id!r}"\
               f", title={self.title!r})"\
               f", default_access_level={AccessLevel(self.default_access_level_int)}"

    def shallow_repr(self) -> dict:
        return {
            "id": self.id,
            "title": self.title,
        }

    def full_repr(self) -> dict:
        return {
            "id": self.id,
            "title": self.title,
            "default_access_level_int": self.default_access_level_int,
            "tasks": [task.shallow_repr() for task in self.tasks],
            "team": [user.shallow_repr() for user in self.team],
        }


class User(Base):
    """Registered user of the app."""
    __tablename__ = 'user'

    # internal exposed fields
    id: Mapped[int] = orm.mapped_column(primary_key=True)

    # internal secret fields
    password_hash: Mapped[str] = orm.mapped_column()

    # userland raw data fields
    name: Mapped[str] = orm.mapped_column()
    email: Mapped[str] = orm.mapped_column(unique=True)

    # orm relationships
    projects: Mapped[list["Membership"]] = orm.relationship(back_populates="user")

    _hasher: typing.ClassVar[argon2.PasswordHasher] = argon2.PasswordHasher()

    def __repr__(self):
        return f"User(id={self.id!r}"\
               f", name={self.name!r}"\
               f", email={self.email!r}"\
               f", password_hash={self.password_hash!r})"

    @classmethod
    def create_with_cleartext_password(cls, name: str, email: str, cleartext_password: str) -> typing.Self:
        """Create a user with a cleartext password.

        This method hashes the password and creates a new user object
        which stores the hash of a salted password."""

        password_hash = cls._hasher.hash(cleartext_password)
        return cls(name=name, email=email, password_hash=password_hash)

    @classmethod
    def create_dummy(cls, name: str) -> typing.Self:
        """Create a dummy user for debugging."""
        email = name.lower() + '@example.com'
        passwd = name.lower() + '123'
        return cls.create_with_cleartext_password(name=name, email=email, cleartext_password=passwd)

    def verify_password(self, cleartext_password: str) -> bool:
        try:
            self._hasher.verify(self.password_hash, cleartext_password)
        except argon2.exceptions.VerifyMismatchError:
            return False
        except argon2.exceptions.VerificationError:
            pass  # verification failed due to an unknown reason, should not happen
        except argon2.exceptions.InvalidHashError:
            pass  # hash is so clearly invalid, that it couldn’t be passed to Argon2
        if self._hasher.check_needs_rehash(self.password_hash):
            self.password_hash = self._hasher.hash(cleartext_password)
        return True

    def shallow_repr(self) -> dict:
        return {
            "id": self.id,
            "name": self.name,
        }

    def full_repr(self) -> dict:
        return {
            "id": self.id,
            "name": self.name,
            "email": self.email,
            "projects": [project.shallow_repr() for project in self.projects]
        }


class Membership(Base):
    """Representation of a user's membership in some project team."""
    __tablename__ = 'membership'

    id: Mapped[int] = orm.mapped_column(primary_key=True)
    user_id: Mapped[int] = orm.mapped_column(sqlalchemy.ForeignKey("user.id"))
    project_id: Mapped[int] = orm.mapped_column(sqlalchemy.ForeignKey("project.id"))
    access_level_int: Mapped[int] = orm.mapped_column(default=1)

    user: Mapped["User"] = orm.relationship(back_populates="projects")
    project: Mapped["Project"] = orm.relationship(back_populates="team")

    def __repr__(self):
        return f"Membership(id={self.id!r}"\
               f", user_id={self.user_id!r}"\
               f", project_id={self.project_id!r}"\
               f", access_level={self.access_level.name})"

    @property
    def access_level(self) -> AccessLevel:
        return AccessLevel(self.access_level_int)


class Database:

    def __init__(self, url: str):
        self.engine = sqlalchemy.create_engine(url)
        Base.metadata.create_all(self.engine)

    def new_session(self):
        return orm.Session(self.engine)
