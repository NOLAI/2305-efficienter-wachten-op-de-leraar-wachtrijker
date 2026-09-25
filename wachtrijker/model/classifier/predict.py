import logging
import os

import torch
from django.conf import settings

from wachtrijker.model.classifier.dataset import create_data_loader
from wachtrijker.model.classifier.model import load_model, load_tokenizer

logger = logging.getLogger(__name__)


def predict(category, messages, batch_size=16):
    logger.info(f"Classifying message for '{category}': {messages}")

    model = load_model(os.path.join(settings.MODEL_DIR, category))
    tokenizer = load_tokenizer(os.path.join(settings.MODEL_DIR, category))

    data_loader = create_data_loader(messages, None, tokenizer, batch_size)

    all_outputs = []
    for _i, batch in enumerate(data_loader):
        batch = {k: v.to("cuda" if torch.cuda.is_available() else "cpu") for k, v in batch.items()}

        with torch.no_grad():
            outputs = model(**batch)
            all_outputs.append(outputs.logits)

    all_outputs = torch.cat(all_outputs)

    logger.info(f"Classification result for '{category}': {all_outputs}")

    return all_outputs
