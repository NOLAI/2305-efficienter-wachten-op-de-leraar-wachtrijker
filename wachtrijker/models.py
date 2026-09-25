import uuid

from django.db import models
from django.utils.translation import gettext_lazy as _


class Session(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4)
    started = models.DateTimeField(auto_now_add=True)
    ended = models.DateTimeField(blank=True, null=True, default=None)
    restarted = models.IntegerField(
        choices=((0, _("Restarted")), (1, _("Answered"))),
        blank=True,
        null=True,
        default=None,
    )

    def __str__(self):
        return f"{self.id}"


class Message(models.Model):
    USER = (
        ("U", _("User")),
        ("B", _("Bot")),
    )
    session = models.ForeignKey(Session, on_delete=models.CASCADE)
    user = models.CharField(max_length=1, choices=USER)
    text = models.TextField()
    failed = models.BooleanField(default=False)
    date = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.session} - {self.date}"


class Score(models.Model):
    message = models.ForeignKey(Message, on_delete=models.CASCADE)
    summary = models.TextField()
    context = models.IntegerField()
    problem = models.IntegerField()
    goal = models.IntegerField()
    attempts = models.IntegerField()
    terminology = models.IntegerField()
    complete = models.BooleanField()
    date = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.message.session} - {self.date}"
