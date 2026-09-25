import logging

logger = logging.getLogger(__name__)


def classify(category, message):
    from wachtrijker.model.classifier.predict import predict

    score = predict(category, [message]).item()

    # The regression model outputs a 0-4 value because training subtracts 1 from the 1-5 rubric scores.
    score = min(5, max(1, round(score) + 1))

    return score
