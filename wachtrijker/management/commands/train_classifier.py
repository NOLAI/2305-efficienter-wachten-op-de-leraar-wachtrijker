import logging
from pathlib import Path

import pandas as pd
import transformers
from django.conf import settings
from django.core.management.base import BaseCommand, CommandError

from wachtrijker.model.classifier.dataset import create_train_test_loader
from wachtrijker.model.classifier.model import load_model, load_tokenizer
from wachtrijker.model.classifier.training import train_model

logger = logging.getLogger(__name__)
transformers.logging.set_verbosity_error()


class Command(BaseCommand):
    help = "Trains the classifier model based on a set of labelled input questions."

    def add_arguments(self, parser):
        parser.add_argument("input_file", type=str)
        parser.add_argument("-c", "--column", type=str)
        parser.add_argument("-b", "--batch_size", type=int, default=16)
        parser.add_argument("-e", "--max_epochs", type=int, default=20)
        parser.add_argument("-l", "--learning_rate", type=float, default=1e-5)
        parser.add_argument("-o", "--output_dir", type=str, default=settings.MODEL_DIR)
        parser.add_argument("-m", "--base-model", type=str, default="GroNLP/bert-base-dutch-cased")

    def handle(self, *args, **options):
        input_file = Path(options["input_file"])
        expected_columns = ["text", "context", "problem", "goal", "attempts", "terminology"]

        if not input_file.exists():
            raise CommandError(f"File '{options['input_file']}' does not exist")

        if options["column"] and options["column"] in expected_columns:
            expected_columns = ["text", options["column"]]

        # Check if we have all columns we need
        df = pd.read_csv(input_file)
        for col in expected_columns:
            if col not in df.columns:
                raise CommandError(
                    f"Input file '{options['input_file']}' should be in valid CSV format and contain the columns: {expected_columns}"
                )

        logger.info(f"Successfully loaded input file '{input_file}' with {len(df)} rows")

        for col in expected_columns[1:]:
            logger.info(f"Starting model training for the category '{col}'")

            # Change None values
            df["text"] = df["text"].apply(lambda x: "" if pd.isnull(x) else x)

            # Only use valid scores
            subset = df[(df[col] >= 1) & (df[col] <= 5)]

            logger.info(f"Using {len(subset)} rows for training")

            # Subtract 1 from the score for model training.
            target = subset[col].apply(lambda x: x - 1).astype(float)

            tokenizer = load_tokenizer(options["base_model"])
            train_loader, val_loader = create_train_test_loader(
                subset["text"], target, tokenizer, batch_size=options["batch_size"]
            )
            model = load_model(options["base_model"])

            train_model(
                train_loader,
                val_loader,
                model,
                tokenizer,
                f"{options['output_dir']}/{col}",
                max_epochs=options["max_epochs"],
                learning_rate=options["learning_rate"],
            )

            logger.info(f"Saved model output to '{options['output_dir']}/{col}'")
        logger.info("Finished training all models")
