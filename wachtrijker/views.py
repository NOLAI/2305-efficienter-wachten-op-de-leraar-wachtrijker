import asyncio
import logging

from asgiref.sync import sync_to_async
from django.http import HttpResponse, HttpResponseBadRequest, JsonResponse
from django.shortcuts import redirect
from django.template import loader
from django.urls import reverse
from django.utils.timezone import now
from django.utils.translation import gettext_lazy as _
from django.views import View
from django.views.generic import TemplateView

from wachtrijker import messages
from wachtrijker.model.classifier import classifier
from wachtrijker.model.feedback import feedback
from wachtrijker.model.openai import OpenAICallFailed
from wachtrijker.model.summarizer import summarizer
from wachtrijker.models import Message, Score, Session

logger = logging.getLogger(__name__)


class Index(TemplateView):
    template_name = "wachtrijker/home.html"

    def dispatch(self, request, *args, **kwargs):
        chat_session = Session.objects.create()
        Message.objects.create(
            session=chat_session,
            user="B",
            text=messages.CONVERSATION_START,
        )
        return redirect(reverse("chat", kwargs={"chat_session": chat_session.id}))


class Chat(View):
    template_name = "wachtrijker/chat.html"

    async def dispatch(self, request, *args, **kwargs):
        # Check if a chat session already exists and was specified
        self.chat_session = None
        if kwargs.get("chat_session"):
            self.chat_session = await Session.objects.filter(id=kwargs.get("chat_session")).afirst()
            if self.chat_session and self.chat_session.ended:
                self.chat_session = None

        # If not, create one and redirect the user
        if not kwargs.get("chat_session") or not self.chat_session:
            return redirect(reverse("index"))

        return await super().dispatch(request, *args, **kwargs)

    async def get_context_data(self, **kwargs):
        score = await Score.objects.filter(message__session=self.chat_session).order_by("-id").afirst()
        scores = (0, 0, 0, 0, 0)
        if score:
            scores = (
                score.context,
                score.problem,
                score.goal,
                score.attempts,
                score.terminology,
            )
        return {
            "chat_messages": await sync_to_async(list)(self.chat_session.message_set.all()),
            "score": score,
            "fields": zip(
                (
                    _("Context"),
                    _("Probleemanalyse"),
                    _("Verwachte uitkomst"),
                    _("Ondernomen stappen"),
                    _("Terminologie"),
                ),
                scores,
                (
                    _(
                        "De vraag moet voldoende achtergrondinformatie bieden zodat de docent begrijpt waarover het probleem gaat."
                    ),
                    _(
                        "De vraag moet een duidelijke afbakening van doelen, grenzen en beperkingen van het probleem bevatten."
                    ),
                    _(
                        "De vraag moet duidelijk maken wat de leerling had verwacht dat er zou gebeuren en wat er daadwerkelijk is gebeurd."
                    ),
                    _(
                        "De vraag moet beschrijven welke pogingen de leerling al heeft ondernomen om het probleem op te lossen."
                    ),
                    _(
                        "De vraag moet aangeven of de leerling gebruikmaakt van relevante, specifieke en nauwkeurige terminologie om het probleem te beschrijven."
                    ),
                ),
                strict=False,
            ),
            "chat_session": self.chat_session.id,
        }

    async def get(self, request, *args, **kwargs):
        template = loader.get_template(self.template_name)
        context = await self.get_context_data(**kwargs)
        return HttpResponse(template.render(context, request))

    async def post(self, request, *args, **kwargs):
        if request.POST.get("message"):
            last_message = await self.chat_session.message_set.alast()
            if last_message.user == "B":
                message = None
                try:
                    # Store the message in the database
                    message = await Message.objects.acreate(
                        session=self.chat_session,
                        user="U",
                        text=request.POST.get("message"),
                    )

                    # Make a summary of the chat
                    summarized_message = await sync_to_async(summarizer.summarize)(
                        self.chat_session.message_set.filter(failed=False).all()
                    )

                    # Calculate the scores for all categories
                    scores = await asyncio.gather(
                        sync_to_async(classifier.classify)("context", summarized_message),
                        sync_to_async(classifier.classify)("problem", summarized_message),
                        sync_to_async(classifier.classify)("goal", summarized_message),
                        sync_to_async(classifier.classify)("attempts", summarized_message),
                        sync_to_async(classifier.classify)("terminology", summarized_message),
                    )

                    # Decide if the question is good enough
                    complete = min(scores) >= 2

                    score = await Score.objects.acreate(
                        message=message,
                        summary=summarized_message,
                        context=scores[0],
                        problem=scores[1],
                        goal=scores[2],
                        attempts=scores[3],
                        terminology=scores[4],
                        complete=complete,
                    )

                    # Generate personalised feedback
                    if complete and (await self.chat_session.message_set.filter(score__complete=True).acount()) == 1:
                        feedback_message = messages.CONVERSATION_COMPLETE
                    else:
                        feedback_message = await sync_to_async(feedback.give_feedback)(score)

                    # Store the feedback in the database
                    await Message.objects.acreate(session=self.chat_session, user="B", text=feedback_message)

                    return JsonResponse(
                        {
                            "scores": scores,
                            "complete": complete,
                            "summary": summarized_message,
                            "feedback": feedback_message,
                        }
                    )
                except OpenAICallFailed as e:
                    logger.error(e)
                    if message:
                        message.failed = True
                        await message.asave()
                    return HttpResponseBadRequest(e.user_message)
        return HttpResponseBadRequest(_("Er is iets fout gegaan, probeer het opnieuw of ververs de pagina!"))


class Ask(View):
    template_name = "wachtrijker/home.html"

    def dispatch(self, request, *args, **kwargs):
        # Check if a chat session already exists and was specified
        self.chat_session = None
        if kwargs.get("chat_session"):
            self.chat_session = Session.objects.filter(id=kwargs.get("chat_session")).first()

        # If not, create one and redirect the user
        if not kwargs.get("chat_session") or not self.chat_session:
            return redirect(reverse("index"))

        return super().dispatch(request, *args, **kwargs)

    def post(self, request, *args, **kwargs):
        if request.POST.get("restart"):
            return self.restart_session(request.POST.get("restart"))
        template = loader.get_template(self.template_name)

        question = request.POST.get("question")
        if question is None:
            question = Score.objects.filter(message__session=self.chat_session).last().summary

        context = {"question": question}
        return HttpResponse(template.render(context, request))

    def restart_session(self, reason):
        self.chat_session.ended = now()
        self.chat_session.restarted = 1 if reason == "answered" else 0
        self.chat_session.save()

        chat_session = Session.objects.create()
        Message.objects.create(
            session=chat_session,
            user="B",
            text=messages.CONVERSATION_START,
        )

        return redirect(reverse("chat", kwargs={"chat_session": chat_session.id}))
