import json
import uuid
from unittest import mock

from django.test import TransactionTestCase
from django.urls import reverse
from django.utils.timezone import now

from wachtrijker import messages
from wachtrijker.model.openai import OpenAICallFailed
from wachtrijker.models import Message, Score, Session


class IndexViewTests(TransactionTestCase):
    def test_creates_session_with_opening_message_and_redirects(self):
        response = self.client.get(reverse("index"))

        self.assertEqual(response.status_code, 302)
        self.assertEqual(Session.objects.count(), 1)
        opening = Message.objects.get()
        self.assertEqual(opening.user, "B")
        self.assertEqual(opening.text, str(messages.CONVERSATION_START))
        session = Session.objects.get()
        self.assertEqual(response.url, reverse("chat", kwargs={"chat_session": session.id}))


class ChatGetViewTests(TransactionTestCase):
    def setUp(self):
        self.session = Session.objects.create()
        Message.objects.create(session=self.session, user="B", text=messages.CONVERSATION_START)

    def test_valid_session_renders_chat(self):
        response = self.client.get(reverse("chat", kwargs={"chat_session": self.session.id}))

        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "wachtrijker/chat.html")

    def test_ended_session_redirects_to_index(self):
        self.session.ended = now()
        self.session.save()

        response = self.client.get(reverse("chat", kwargs={"chat_session": self.session.id}))

        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, reverse("index"))

    def test_unknown_session_redirects_to_index(self):
        response = self.client.get(reverse("chat", kwargs={"chat_session": uuid.uuid4()}))

        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, reverse("index"))


class ChatPostViewTests(TransactionTestCase):
    def setUp(self):
        self.session = Session.objects.create()
        Message.objects.create(session=self.session, user="B", text=messages.CONVERSATION_START)
        self.url = reverse("chat", kwargs={"chat_session": self.session.id})

    @mock.patch("wachtrijker.views.feedback.give_feedback", return_value="Meer info graag")
    @mock.patch("wachtrijker.views.classifier.classify", return_value=1)
    @mock.patch("wachtrijker.views.summarizer.summarize", return_value="SAMENVATTING")
    def test_incomplete_question_stores_score_and_feedback(self, summarize, classify, give_feedback):
        response = self.client.post(self.url, {"message": "Mijn code werkt niet"})

        self.assertEqual(response.status_code, 200)
        body = json.loads(response.content)
        self.assertEqual(body["scores"], [1, 1, 1, 1, 1])
        self.assertFalse(body["complete"])
        self.assertEqual(body["summary"], "SAMENVATTING")
        self.assertEqual(body["feedback"], "Meer info graag")

        score = Score.objects.get()
        self.assertFalse(score.complete)
        self.assertTrue(Message.objects.filter(session=self.session, user="B", text="Meer info graag").exists())

    @mock.patch("wachtrijker.views.feedback.give_feedback")
    @mock.patch("wachtrijker.views.classifier.classify", return_value=3)
    @mock.patch("wachtrijker.views.summarizer.summarize", return_value="SAMENVATTING")
    def test_complete_question_uses_completion_message(self, summarize, classify, give_feedback):
        response = self.client.post(self.url, {"message": "Een hele duidelijke vraag"})

        self.assertEqual(response.status_code, 200)
        body = json.loads(response.content)
        self.assertTrue(body["complete"])
        self.assertEqual(body["feedback"], str(messages.CONVERSATION_COMPLETE))
        give_feedback.assert_not_called()
        self.assertTrue(Score.objects.get().complete)

    def test_post_when_not_bots_turn_is_bad_request(self):
        Message.objects.create(session=self.session, user="U", text="Al een bericht")

        response = self.client.post(self.url, {"message": "Nog een bericht"})

        self.assertEqual(response.status_code, 400)

    @mock.patch(
        "wachtrijker.views.summarizer.summarize",
        side_effect=OpenAICallFailed("boom", "Iets ging mis, probeer opnieuw"),
    )
    def test_openai_failure_marks_message_failed(self, summarize):
        response = self.client.post(self.url, {"message": "Mijn code werkt niet"})

        self.assertEqual(response.status_code, 400)
        self.assertIn("Iets ging mis", response.content.decode())
        user_message = Message.objects.get(session=self.session, user="U")
        self.assertTrue(user_message.failed)


class AskViewTests(TransactionTestCase):
    def setUp(self):
        self.session = Session.objects.create()
        Message.objects.create(session=self.session, user="B", text=messages.CONVERSATION_START)
        self.url = reverse("ask", kwargs={"chat_session": self.session.id})

    def test_restart_answered_ends_session_and_starts_new(self):
        response = self.client.post(self.url, {"restart": "answered"})

        self.session.refresh_from_db()
        self.assertIsNotNone(self.session.ended)
        self.assertEqual(self.session.restarted, 1)
        self.assertEqual(Session.objects.count(), 2)
        self.assertEqual(response.status_code, 302)

    def test_restart_restarted_marks_zero(self):
        self.client.post(self.url, {"restart": "restarted"})

        self.session.refresh_from_db()
        self.assertEqual(self.session.restarted, 0)

    def test_question_defaults_to_last_summary(self):
        message = Message.objects.create(session=self.session, user="U", text="vraag")
        Score.objects.create(
            message=message,
            summary="De opgeslagen samenvatting",
            context=2,
            problem=2,
            goal=2,
            attempts=2,
            terminology=2,
            complete=True,
        )

        response = self.client.post(self.url, {})

        self.assertEqual(response.status_code, 200)
        self.assertIn("De opgeslagen samenvatting", response.content.decode())
