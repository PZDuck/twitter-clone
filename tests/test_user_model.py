import os
from unittest import TestCase

from models import db, User, Message, Follows

os.environ['DATABASE_URL'] = "postgresql://postgres:password@localhost:5432/warbler_test"

from app import app

db.create_all()


class UserModelTestCase(TestCase):
    """Test views for messages."""

    def setUp(self):
        """Create test client, add sample data."""

        User.query.delete()
        Message.query.delete()
        Follows.query.delete()

        user1 = User.signup("user1", "testtest@test.com", "testpass", None)
        user2 = User.signup("user2", "newmail@test.com", "password", None)

        db.session.commit()

        self.user1 = user1
        self.user1_id = User.query.filter(User.username=="user1").first().id

        self.user2 = user2
        self.user2_id = User.query.filter(User.username=="user2").first().id

        self.client = app.test_client()

    def test_user_model(self):
        """Does basic model work?"""

        u = User(
            email="test@test.com",
            username="testuser",
            password="HASHED_PASSWORD"
        )

        db.session.add(u)
        db.session.commit()

        self.assertEqual(len(u.messages), 0)
        self.assertEqual(len(u.followers), 0)
    
    def test_is_following(self):
        self.user1.following.append(self.user2)

        db.session.commit()

        self.assertTrue(self.user1.is_following(self.user2))
        self.assertFalse(self.user2.is_following(self.user1))

    def test_is_followed_by(self):
        self.user1.following.append(self.user2)

        db.session.commit()

        self.assertTrue(self.user2.is_followed_by(self.user1))
        self.assertFalse(self.user1.is_followed_by(self.user2))
    
    def test_signup(self):
        test_user = User.signup("test_user", "test@new.com", "password", None)

        db.session.commit()

        test_user = User.query.filter(User.username=="test_user").first()
        self.assertIsNotNone(test_user)
        self.assertEqual(test_user.username, "test_user")
        self.assertEqual(test_user.email, "test@new.com")
        self.assertNotEqual(test_user.password, "password")
        self.assertTrue(test_user.password.startswith("$2b$"))
    
    def test_authentication(self):
        user = User.authenticate(self.user1.username, "testpass")
        self.assertIsNotNone(user)
        self.assertEqual(user.id, self.user1_id)

