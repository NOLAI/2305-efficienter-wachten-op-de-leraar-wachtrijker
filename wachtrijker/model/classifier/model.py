import logging

import torch
from transformers import AutoTokenizer, BertForSequenceClassification

logger = logging.getLogger(__name__)

# Global variables for the model
model_cache = {}
tokenizer_cache = {}


def load_model(model_path):
    global model_cache

    if model_path in model_cache:
        return model_cache[model_path]

    logger.info(f"Loading classification model from path '{model_path}'")

    model = BertForSequenceClassification.from_pretrained(model_path, num_labels=1)
    model.config.classifier_dropout = 0.2
    model.to("cuda" if torch.cuda.is_available() else "cpu")

    model_cache[model_path] = model

    return model


def load_tokenizer(model_path):
    global tokenizer_cache

    if model_path in tokenizer_cache:
        return tokenizer_cache[model_path]

    logger.info(f"Loading tokenizer model from path '{model_path}'")

    tokenizer = AutoTokenizer.from_pretrained(model_path)

    tokenizer_cache[model_path] = tokenizer

    return tokenizer
