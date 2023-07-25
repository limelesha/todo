import dataclasses
import datetime
import enum
import typing

import argon2
import flask


@dataclasses.dataclass(slots=True)
class Task:
    """A single task entry in a task list."""
    id: int
    title: str
    description: str = ''
    due: typing.Optional[datetime.datetime] = None
    subtasks: list[typing.Self] = dataclasses.field(default_factory=list)
    is_done: bool = dataclasses.field(default=False, init=False)


@dataclasses.dataclass(slots=True)
class TaskList(list):
    """A task list, contains instances of `Task`."""
    id: int
    title: str

    def remove_done(self) -> None:
        """Remove all tasks marked as done."""
        self[:] = [task for task in self if not task.is_done]


@dataclasses.dataclass(slots=True)
class User:
    """Registered user of the app."""
    id: int
    name: str
    password_hash: str

    _hasher: typing.ClassVar[argon2.PasswordHasher] = argon2.PasswordHasher()

    @classmethod
    def create_with_cleartext_password(cls, id: int, name: str, cleartext_password: str) -> typing.Self:
        """Create a user with a cleartext password.

        This method hashes the password and creates a new user object
        which stores the hash of a salted password."""

        return cls(id, name, cls._hasher.hash(cleartext_password))


class AccessLevel(enum.IntEnum):
    """Access levels of a user to a task list.

    Constants that describe the access level (and corresponding
    permissions) of a user in a task list. Relevent in shared lists to
    limit permissions of invited users."""

    READ = enum.auto()  # this access level grants permission to read the contents of a task list
    EDIT = enum.auto()  # edit task list contents, that is add and remove tasks, change task status, edit task details
    MANAGE = enum.auto()  # manage a task list itself, like rename, delete and manage the team


@dataclasses.dataclass(slots=True)
class Membership:
    """Representation of a user's membership in some task list team."""
    id: int
    user: User
    task_list: TaskList
    access_level: AccessLevel


def create_app():
    app = flask.Flask(__name__)
    return app
