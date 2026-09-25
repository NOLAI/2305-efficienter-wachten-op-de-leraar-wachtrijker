from django.contrib.admin import site

from wachtrijker.models import Session, Message, Score

site.register(Session)
site.register(Message)
site.register(Score)
