import logging

from django.utils.translation import gettext_lazy as _

from wachtrijker.model import openai

logger = logging.getLogger(__name__)


def give_feedback(score):
    logger.info("Creating feedback for chat message")

    lowest_score = min(score.context, score.problem, score.goal, score.attempts, score.terminology)

    # Also defines priority for asking follow-up questions
    selected_label = None
    for category, label in [
        ("context", _("Context")),
        ("problem", _("Probleemanalyse")),
        ("goal", _("Verwachte uitkomst")),
        ("attempts", _("Ondernomen stappen")),
        ("terminology", _("Terminologie")),
    ]:
        if getattr(score, category) == lowest_score:
            selected_label = label
            break

    with open(f"wachtrijker/model/feedback/prompts/rubric/{category}.md") as file:
        rubric = file.read()

    kwargs = {
        "summary": score.summary,
        "score": str(getattr(score, category)),
        "category": str(selected_label),
        "rubric": rubric,
    }

    logger.debug(openai.create_prompt("wachtrijker/model/feedback/prompts/system_prompt.md"))
    logger.debug(openai.create_prompt("wachtrijker/model/feedback/prompts/user_prompt.md", **kwargs))

    data = openai.openai_call(
        system_prompt=openai.create_prompt("wachtrijker/model/feedback/prompts/system_prompt.md"),
        user_prompt=openai.create_prompt("wachtrijker/model/feedback/prompts/user_prompt.md", **kwargs),
    )

    logger.debug(data)

    message = data["choices"][0]["message"]

    logger.info("Feedback creation complete")

    return message["content"]
