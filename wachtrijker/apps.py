import logging
import os

from django.apps import AppConfig
from django.conf import settings

logger = logging.getLogger(__name__)


class WachtrijkerAppConfig(AppConfig):
    name = "wachtrijker"

    def ready(self):
        if os.environ.get("RUN_MAIN", None):
            if not settings.DUMMY_CLASSIFIERS:
                from wachtrijker.model.classifier import model

                for category in ["context", "problem", "goal", "attempts", "terminology"]:
                    model.load_model(os.path.join(settings.MODEL_DIR, category))
            if settings.DUMMY_CLASSIFIERS:
                from wachtrijker.model.classifier import classifier
                from wachtrijker.model.feedback import feedback
                from wachtrijker.model.summarizer import summarizer

                logger.info("Overwriting with dummy classifiers")

                classifier.load_models = lambda: logger.info("Skipping model loading")

                def classify(category, message):
                    logger.info("CLASSIFIER IS OVERWRITTEN")
                    return min(5, max(1, round(len(message) / 10)))

                classifier.classify = classify

                def give_feedback(score):
                    logger.info("FEEDBACK IS OVERWRITTEN")
                    return "Kun je wat meer details geven?"

                feedback.give_feedback = give_feedback

                def summarize(messages):
                    logger.info("SUMMARIZER IS OVERWRITTEN")
                    return " ".join([x.text for x in messages if x.user == "U"])

                summarizer.summarize = summarize
