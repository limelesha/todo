import dataclasses
import datetime
import enum
import typing

import argon2
import flask


TaskId = typing.NewType('TaskId', int)
UserId = typing.NewType('UserId', int)
ProjectId = typing.NewType('ProjectId', int)
MembershipId = typing.NewType('MembershipId', int)


@dataclasses.dataclass(slots=True)
class Task:
    """A single task entry in a project."""
    id: TaskId
    title: str
    description: typing.Optional[str] = None
    due: typing.Optional[datetime.datetime] = None
    supertask: typing.Optional[typing.Self] = None
    subtasks: list[typing.Self] = dataclasses.field(default_factory=list, init=False)
    is_done: bool = dataclasses.field(default=False, init=False)


@dataclasses.dataclass(slots=True)
class Project(list):
    """Project is a container of tasks."""
    id: ProjectId
    title: str

    def remove_done(self) -> None:
        """Remove all tasks marked as done."""
        self[:] = [task for task in self if not task.is_done]


@dataclasses.dataclass(slots=True)
class User:
    """Registered user of the app."""
    id: UserId
    name: str
    email: str
    password_hash: str

    _hasher: typing.ClassVar[argon2.PasswordHasher] = argon2.PasswordHasher()

    @classmethod
    def create_with_cleartext_password(cls, id: int, name: str, cleartext_password: str) -> typing.Self:
        """Create a user with a cleartext password.

        This method hashes the password and creates a new user object
        which stores the hash of a salted password."""

        return cls(id, name, cls._hasher.hash(cleartext_password))


class AccessLevel(enum.IntEnum):
    """Access levels of a user to a project.

    Constants that describe the access level (and corresponding
    permissions) of a user in a project. Relevent in shared lists to
    limit permissions of invited users."""

    READ = enum.auto()  # this access level grants permission to read the contents of a project
    EDIT = enum.auto()  # edit project contents, that is add and remove tasks, change task status, edit task details
    MANAGE = enum.auto()  # manage a project itself, like rename, delete and manage the team


@dataclasses.dataclass(slots=True)
class Membership:
    """Representation of a user's membership in some project team."""
    id: MembershipId
    user: UserId
    project: ProjectId
    access_level: AccessLevel


def create_app():
    app = flask.Flask(__name__)
    return app
