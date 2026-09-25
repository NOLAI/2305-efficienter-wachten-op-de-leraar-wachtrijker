from types import SimpleNamespace
from unittest import mock

from django.test import SimpleTestCase

from wachtrijker.model.feedback import feedback


def _completion(content="Kun je wat meer details geven?"):
    return {"choices": [{"message": {"content": content}}]}


def _score(context=3, problem=3, goal=3, attempts=3, terminology=3, summary="Een samenvatting"):
    return SimpleNamespace(
        context=context,
        problem=problem,
        goal=goal,
        attempts=attempts,
        terminology=terminology,
        summary=summary,
    )


class GiveFeedbackTests(SimpleTestCase):
    @mock.patch("wachtrijker.model.openai.openai_call")
    def test_returns_completion_content(self, call):
        call.return_value = _completion("Meer context graag")

        result = feedback.give_feedback(_score(context=1))

        self.assertEqual(result, "Meer context graag")

    @mock.patch("builtins.open", wraps=open)
    @mock.patch("wachtrijker.model.openai.openai_call")
    def test_selects_single_lowest_category(self, call, open_spy):
        call.return_value = _completion()

        feedback.give_feedback(_score(goal=1))

        rubric_reads = [c.args[0] for c in open_spy.call_args_list if "rubric/" in str(c.args[0])]
        self.assertEqual(rubric_reads, ["wachtrijker/model/feedback/prompts/rubric/goal.md"])

        user_prompt = call.call_args.kwargs["user_prompt"]
        self.assertIn("Verwachte uitkomst", user_prompt)

    @mock.patch("builtins.open", wraps=open)
    @mock.patch("wachtrijker.model.openai.openai_call")
    def test_tie_breaks_on_priority_order(self, call, open_spy):
        call.return_value = _completion()

        # context and problem are both the lowest -> context wins (listed first)
        feedback.give_feedback(_score(context=1, problem=1))

        rubric_reads = [c.args[0] for c in open_spy.call_args_list if "rubric/" in str(c.args[0])]
        self.assertEqual(rubric_reads, ["wachtrijker/model/feedback/prompts/rubric/context.md"])

        user_prompt = call.call_args.kwargs["user_prompt"]
        self.assertIn("Context", user_prompt)
