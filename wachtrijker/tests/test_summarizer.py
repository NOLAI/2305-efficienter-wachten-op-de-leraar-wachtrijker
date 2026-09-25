from types import SimpleNamespace
from unittest import mock

from django.test import SimpleTestCase

from wachtrijker.model.summarizer import summarizer


def _completion(content="SUMMARY"):
    return {"choices": [{"message": {"content": content}}]}


class SummarizeTests(SimpleTestCase):
    def _messages(self):
        return [
            SimpleNamespace(user="B", text="Openingsbericht van de bot"),
            SimpleNamespace(user="U", text="Mijn code werkt niet"),
            SimpleNamespace(user="B", text="Wat gebeurt er precies?"),
            SimpleNamespace(user="U", text="Ik krijg een foutmelding"),
        ]

    @mock.patch("wachtrijker.model.openai.openai_call")
    def test_returns_completion_content(self, call):
        call.return_value = _completion("SAMENVATTING")

        result = summarizer.summarize(self._messages())

        self.assertEqual(result, "SAMENVATTING")

    @mock.patch("wachtrijker.model.openai.openai_call")
    def test_transcript_skips_first_message_and_maps_roles(self, call):
        call.return_value = _completion()

        summarizer.summarize(self._messages())

        user_prompt = call.call_args.kwargs["user_prompt"]
        self.assertNotIn("Openingsbericht van de bot", user_prompt)
        self.assertIn("Leerling: Mijn code werkt niet", user_prompt)
        self.assertIn("Docent: Wat gebeurt er precies?", user_prompt)
        self.assertIn("Leerling: Ik krijg een foutmelding", user_prompt)
