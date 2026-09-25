import logging

import transformers
from django.core.management.base import BaseCommand

from wachtrijker.model.classifier.predict import predict

logger = logging.getLogger(__name__)
transformers.logging.set_verbosity_error()


class Command(BaseCommand):
    help = "Predict the score using the trained classifier."

    def add_arguments(self, parser):
        parser.add_argument("-t", "--text", action="append")
        parser.add_argument("-c", "--column", type=str, default=None)

    def handle(self, *args, **options):
        expected_columns = ["context", "problem", "goal", "attempts", "terminology"]

        if options["column"] and options["column"] in expected_columns:
            expected_columns = [options["column"]]

        for col in expected_columns:
            logger.info(f"Predicting score for the category '{col}'")

            scores = predict(col, options["text"]).cpu().numpy()

            logger.info(f"Score from '{col}': {scores}")
        logger.info("Finished scoring all models")
