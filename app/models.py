import enum
import textwrap
import typing

import argon2
import sqlalchemy
from sqlalchemy import orm
from sqlalchemy.orm import Mapped


class Base(orm.DeclarativeBase):
    pass


class Task(Base):
    """A single task entry in a project."""
    __tablename__ = 'task'

    id: Mapped[int] = orm.mapped_column(primary_key=True)
    title: Mapped[str] = orm.mapped_column()
    description: Mapped[str | None] = orm.mapped_column()
    due_timestamp: Mapped[float | None] = orm.mapped_column()
    project_id: Mapped[int] = orm.mapped_column(sqlalchemy.ForeignKey("project.id"))
    supertask_id: Mapped[int | None] = orm.mapped_column(sqlalchemy.ForeignKey("task.id"))
    is_done: Mapped[bool] = orm.mapped_column(default=False)

    project: Mapped["Project"] = orm.relationship(back_populates="content")
    subtasks: Mapped[list["Task"]] = orm.relationship(back_populates="supertask")
    supertask: Mapped["Task"] = orm.relationship(back_populates="subtasks", remote_side=[id])

    def __repr__(self):
        return f"Task(id={self.id!r}"\
               f", title={self.title!r}"\
               f", description={(self.description and textwrap.shorten(self.description, 24))!r}"\
               f", due_timestamp={self.due_timestamp!r}"\
               f", project_id={self.project_id!r}"\
               f", supertask_id={self.supertask_id!r}"\
               f", is_done={self.is_done!r})"


class Project(Base):
    """Project is a container of tasks."""
    __tablename__ = 'project'

    id: Mapped[int] = orm.mapped_column(primary_key=True)
    title: Mapped[str] = orm.mapped_column()

    content: Mapped[list["Task"]] = orm.relationship(back_populates="project")
    team: Mapped[list["Membership"]] = orm.relationship(back_populates="project")

    def __repr__(self):
        return f"Project(id={self.id!r}"\
               f", title={self.title!r})"

    # def remove_done(self) -> None:
    #     """Remove all tasks marked as done."""
    #     self[:] = [task for task in self if not task.is_done]


class User(Base):
    """Registered user of the app."""
    __tablename__ = 'user'

    id: Mapped[int] = orm.mapped_column(primary_key=True)
    name: Mapped[str] = orm.mapped_column()
    email: Mapped[str] = orm.mapped_column()
    password_hash: Mapped[str] = orm.mapped_column()

    projects: Mapped[list["Membership"]] = orm.relationship(back_populates="user")

    _hasher: typing.ClassVar[argon2.PasswordHasher] = argon2.PasswordHasher()

    def __repr__(self):
        return f"User(id={self.id!r}"\
               f", name={self.name!r}"\
               f", email={self.email!r}"\
               f", password_hash={self.password_hash!r})"

    @classmethod
    def create_with_cleartext_password(cls, name: str, email: str, cleartext_password: str):
        """Create a user with a cleartext password.

        This method hashes the password and creates a new user object
        which stores the hash of a salted password."""

        password_hash = cls._hasher.hash(cleartext_password)
        return cls(name=name, email=email, password_hash=password_hash)

    @classmethod
    def create_dummy(cls, name: str):
        """Create a dummy user for debugging."""
        email = name.lower() + '@example.com'
        passwd = name.lower() + '123'
        return cls.create_with_cleartext_password(name=name, email=email, cleartext_password=passwd)


class AccessLevel(enum.IntEnum):
    """Access levels of a user to a project.

    Constants that describe the access level (and corresponding
    permissions) of a user in a project. Relevent in shared lists to
    limit permissions of invited users."""

    READER = enum.auto()  # this access level grants permission to read the contents of a project
    EDITOR = enum.auto()  # edit project contents, that is add and remove tasks, change task status, edit task details
    MANAGER = enum.auto()  # manage a project itself, like rename, delete and manage the team


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


engine = sqlalchemy.create_engine('sqlite:///:memory:')
Base.metadata.create_all(engine)
session = orm.Session(engine)


if __name__ == '__main__':
    test = True
else:
    test = False


if test:
    mike = User.create_dummy("Mike")
    kim = User.create_dummy("Kim")
    summer = Project(title="Summer Project")
    winter = Project(title="Winter Project")
    membership = Membership(user=mike, project=summer)
    alpha = Task(title="alpha", description="This is a very good task.", project=summer)
    bravo = Task(title="bravo", project=summer)
    charlie = Task(title="charlie", project=summer)
    one = Task(title="one", project=summer, supertask=bravo)
    two = Task(title="two", project=summer, supertask=bravo)
    session.add_all([
        mike,
        kim,
        summer,
        winter,
        alpha,
        bravo,
        charlie,
        one,
        two
    ])
    session.flush()
