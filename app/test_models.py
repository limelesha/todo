import unittest

import sqlalchemy

from . import models


class TestModels(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.database = models.Database("sqlite:///:memory:")

    def test_write(self):
        mike = models.User.create_dummy("Mike")
        kim = models.User.create_dummy("Kim")
        summer = models.Project(title="Summer Project")
        winter = models.Project(title="Winter Project")
        membership = models.Membership(user=mike, project=summer)
        alpha = models.Task(title="alpha", description="This is a very good task.", project=summer)
        bravo = models.Task(title="bravo", project=summer)
        charlie = models.Task(title="charlie", project=summer)
        one = models.Task(title="one", project=summer, supertask=bravo)
        two = models.Task(title="two", project=summer, supertask=bravo)
        with self.database.new_session() as session:
            session.add_all([mike, kim, summer, winter, membership,
                             alpha, bravo, charlie, one, two])
            session.commit()

    def test_read(self):
        with self.database.new_session() as session:
            all_mikes = list(session.scalars(sqlalchemy.select(models.User).where(models.User.name == 'Mike')))
            all_summers = list(session.scalars(sqlalchemy.select(models.Project).where(models.Project.title == 'Summer Project')))
            self.assertEqual(len(all_mikes), 1)
            mike, = all_mikes
            self.assertEqual(mike.name, 'Mike')
            self.assertEqual(mike.email, 'mike@example.com')
            self.assertEqual(len(all_summers), 1)
            summer, = all_summers
            mike_memberships = list(mike.projects)
            self.assertEqual(len(mike_memberships), 1)
            mike_membership, = mike_memberships
            self.assertEqual(mike_membership.project, summer)


if __name__ == '__main__':
    unittest.main()
