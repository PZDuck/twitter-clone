import os
from unittest import TestCase

from models import db, connect_db, Message, User

os.environ['DATABASE_URL'] = "postgresql://postgres:password@localhost:5432/warbler_test"

from app import app, CURR_USER_KEY

db.create_all()

app.config['WTF_CSRF_ENABLED'] = False


class MessageViewTestCase(TestCase):
    """Test views for messages."""

    def setUp(self):
        """Create test client, add sample data."""

        User.query.delete()
        Message.query.delete()

        self.client = app.test_client()

        self.testuser = User.signup(username="testuser",
                                    email="test@test.com",
                                    password="testuser",
                                    image_url=None)

        db.session.commit()

    def test_add_message(self):

        with self.client as c:
            with c.session_transaction() as sess:
                sess[CURR_USER_KEY] = self.testuser.id

            resp = c.post("/messages/new", data={"text": "Hello"})

            self.assertEqual(resp.status_code, 302)

            msg = Message.query.one()
            self.assertEqual(msg.text, "Hello")

    def test_message_404(self):
        with self.client as c:
            with c.session_transaction() as sess:
                sess[CURR_USER_KEY] = self.testuser.id
            
            resp = c.get('/messages/0')

            self.assertEqual(resp.status_code, 404)

    def test_message_show(self):

        msg = Message(text="test", user_id=self.testuser.id)

        db.session.add(msg)
        db.session.commit()

        with self.client as c:
            with c.session_transaction() as sess:
                sess[CURR_USER_KEY] = self.testuser.id
            
            msg = Message.query.filter(Message.text=="test").first()

            resp = c.get(f'/messages/{msg.id}')

            self.assertEqual(resp.status_code, 200)
            self.assertIn(msg.text, str(resp.data))
    
    def test_message_delete(self):

        msg = Message(text="test", user_id=self.testuser.id)

        db.session.add(msg)
        db.session.commit()

        with self.client as c:
            with c.session_transaction() as sess:
                sess[CURR_USER_KEY] = self.testuser.id
            
            msg = Message.query.filter(Message.text=="test").first()

            resp = c.post(f'/messages/{msg.id}/delete', follow_redirects=True)
            self.assertEqual(resp.status_code, 200)
    
