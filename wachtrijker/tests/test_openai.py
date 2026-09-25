import json
import os
import tempfile
from unittest import mock

from django.test import SimpleTestCase

from wachtrijker.model.openai import OpenAICallFailed, create_prompt, openai_call


def _make_response(payload):
    response = mock.Mock()
    response.json.return_value = payload
    return response


def _ok_payload(content="Hallo", refusal=None):
    message = {"content": content}
    if refusal is not None:
        message["refusal"] = refusal
    return {"choices": [{"message": message}]}


def _error_payload(code, message="boom"):
    return {"error": {"code": code, "message": message}}


class CreatePromptTests(SimpleTestCase):
    def _write_prompt(self, text):
        handle = tempfile.NamedTemporaryFile("w", suffix=".md", delete=False)
        handle.write(text)
        handle.close()
        self.addCleanup(os.unlink, handle.name)
        return handle.name

    def test_single_placeholder(self):
        path = self._write_prompt("Hallo <<name>>!")
        self.assertEqual(create_prompt(path, name="Leerling"), "Hallo Leerling!")

    def test_multiple_placeholders(self):
        path = self._write_prompt("<<greeting>> <<name>>, <<greeting>> nogmaals")
        self.assertEqual(
            create_prompt(path, greeting="Hoi", name="Leerling"),
            "Hoi Leerling, Hoi nogmaals",
        )

    def test_no_placeholders_returns_file_verbatim(self):
        path = self._write_prompt("Geen placeholders hier")
        self.assertEqual(create_prompt(path), "Geen placeholders hier")

    def test_unsupplied_key_left_literal(self):
        path = self._write_prompt("Hallo <<name>>, <<missing>>")
        self.assertEqual(create_prompt(path, name="Leerling"), "Hallo Leerling, <<missing>>")


class OpenAICallTests(SimpleTestCase):
    def test_requires_messages_or_both_prompts(self):
        with self.assertRaises(OpenAICallFailed):
            openai_call()
        with self.assertRaises(OpenAICallFailed):
            openai_call(system_prompt="only system")

    @mock.patch("wachtrijker.model.openai.requests.post")
    def test_builds_message_list_from_prompts(self, post):
        post.return_value = _make_response(_ok_payload())

        openai_call(system_prompt="sys", user_prompt="usr")

        sent = json.loads(post.call_args.kwargs["data"])
        self.assertEqual(
            sent["messages"],
            [
                {"role": "system", "content": "sys"},
                {"role": "user", "content": "usr"},
            ],
        )

    @mock.patch("wachtrijker.model.openai.requests.post")
    def test_success_returns_parsed_data(self, post):
        payload = _ok_payload(content="Klaar")
        post.return_value = _make_response(payload)

        result = openai_call(messages=[{"role": "user", "content": "hi"}])

        self.assertEqual(result, payload)
        self.assertEqual(result["choices"][0]["message"]["content"], "Klaar")

    @mock.patch("wachtrijker.model.openai.requests.post")
    def test_refusal_raises(self, post):
        post.return_value = _make_response(_ok_payload(refusal="I cannot"))

        with self.assertRaises(OpenAICallFailed) as ctx:
            openai_call(messages=[{"role": "user", "content": "hi"}])

        self.assertTrue(str(ctx.exception.user_message))

    @mock.patch("wachtrijker.model.openai.time.sleep")
    @mock.patch("wachtrijker.model.openai.requests.post")
    def test_429_then_success_retries_once(self, post, sleep):
        post.side_effect = [
            _make_response(_error_payload("429", "Please retry after 3 seconds")),
            _make_response(_ok_payload(content="na retry")),
        ]

        result = openai_call(messages=[{"role": "user", "content": "hi"}])

        self.assertEqual(result["choices"][0]["message"]["content"], "na retry")
        self.assertEqual(post.call_count, 2)
        sleep.assert_called_once_with(3)

    @mock.patch("wachtrijker.model.openai.time.sleep")
    @mock.patch("wachtrijker.model.openai.requests.post")
    def test_429_twice_raises(self, post, sleep):
        post.return_value = _make_response(_error_payload("429", "Please retry after 1 second"))

        with self.assertRaises(OpenAICallFailed):
            openai_call(messages=[{"role": "user", "content": "hi"}])

        self.assertEqual(post.call_count, 2)


class OpenAICallFailedTests(SimpleTestCase):
    def test_exposes_user_message(self):
        exc = OpenAICallFailed("internal detail", "vriendelijke tekst")
        self.assertEqual(exc.user_message, "vriendelijke tekst")
        self.assertEqual(exc.message, "internal detail")
