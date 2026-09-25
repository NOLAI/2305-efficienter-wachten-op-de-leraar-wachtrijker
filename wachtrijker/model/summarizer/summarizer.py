import logging

from wachtrijker.model import openai

logger = logging.getLogger(__name__)


def summarize(messages):
    logger.info("Summarizing chat messages")

    transcript = []
    # Skip the first message: it is the fixed bot greeting, not part of the student's actual question.
    for message in list(messages[1:]):
        user = "Leerling" if message.user == "U" else "Docent"
        transcript.append(f"{user}: {message.text}")

    logger.debug(openai.create_prompt("wachtrijker/model/summarizer/prompts/system_prompt.md"))
    logger.debug(
        openai.create_prompt(
            "wachtrijker/model/summarizer/prompts/user_prompt.md",
            transcript="\n".join(transcript),
        )
    )

    data = openai.openai_call(
        system_prompt=openai.create_prompt("wachtrijker/model/summarizer/prompts/system_prompt.md"),
        user_prompt=openai.create_prompt(
            "wachtrijker/model/summarizer/prompts/user_prompt.md",
            transcript="\n".join(transcript),
        ),
    )

    logger.debug(data)

    message = data["choices"][0]["message"]

    logger.info("Summarization complete")

    return message["content"]
