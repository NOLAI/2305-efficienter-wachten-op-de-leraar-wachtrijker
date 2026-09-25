import json
import logging
import re
import time

import requests

from django.utils.translation import gettext_lazy as _

from wachtrijker.settings import OPENAI_BASE, OPENAI_MODEL, OPENAI_VERSION, OPENAI_KEY


logger = logging.getLogger(__name__)


def openai_call(
    messages=None,
    system_prompt=None,
    user_prompt=None,
    response_format=None,
    temperature=0.5,
    retried=False,
):
    if not messages and not (system_prompt and user_prompt):
        raise OpenAICallFailed(
            "No messages or system_prompt and user_prompt provided",
            _("Oeps, er is iets fout gegaan!"),
        )

    if not messages:
        messages = [
            {
                "role": "system",
                "content": system_prompt,
            },
            {"role": "user", "content": user_prompt},
        ]

    data = {
        "messages": messages,
        "temperature": temperature,
        "stop": None,
    }
    if response_format:
        data["response_format"] = response_format

    response = requests.post(
        f"{OPENAI_BASE}{OPENAI_MODEL}{OPENAI_VERSION}",
        headers={"Content-Type": "application/json", "api-key": OPENAI_KEY},
        data=json.dumps(data),
    )

    data = response.json()
    if "error" in data:
        if data["error"]["code"] == "429":
            sleep_time = re.findall(
                r"Please retry after ([0-9]+) second", data["error"]["message"]
            )
            if sleep_time:
                logger.info(f"Hit limit, sleeping for {sleep_time[0]} seconds...")
                time.sleep(int(sleep_time[0]))
        if not retried:
            return openai_call(
                messages=messages,
                system_prompt=system_prompt,
                user_prompt=user_prompt,
                response_format=response_format,
                retried=True,
            )
        raise OpenAICallFailed(
            data,
            _(
                "Ik begrijp niet helemaal wat je bedoelt, zou je het anders kunnen formuleren?"
            ),
        )

    message = data["choices"][0]["message"]
    if "refusal" in message and message["refusal"]:
        raise OpenAICallFailed(
            data,
            _(
                "Ik begrijp niet helemaal wat je bedoelt, zou je het anders kunnen formuleren?"
            ),
        )

    return data


def create_prompt(prompt_path, **kwargs):
    with open(prompt_path, "r") as file:
        prompt = file.read()
        for key, value in kwargs.items():
            prompt = prompt.replace(f"<<{key}>>", value)
        return prompt


class OpenAICallFailed(Exception):
    def __init__(self, message, user_message):
        # Call the base class constructor with the parameters it needs
        super().__init__(message)
        self.message = message
        self.user_message = user_message
