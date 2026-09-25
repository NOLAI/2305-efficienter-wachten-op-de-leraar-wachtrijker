"use strict";
$.ajaxSetup({ headers: { 'X-CSRFToken': $('meta[name="csrf-token"]').attr('content') } });

let scrolling = false;
function scrollDown() {
    let chatBox = $("#chat-box");
    let scrollTo = chatBox[0].scrollTopMax;
    if (chatBox.attr("scrolled") < scrollTo) {
        if (scrolling) {
            chatBox.stop(true);
        }
        scrolling = true;

        chatBox.animate({ scrollTop: scrollTo }, 400, function () {
            chatBox.attr("scrolled", scrollTo);
            scrolling = false;
        });
    }
}

function addMessage(message, justify) {
    $("#chat-messages").append(`
      <div class="d-flex flex-row position-relative message justify-content-${justify}">
        <div class="message-container p-3">
          <div class="message-content small mb-0">${message}</div>
        </div>
      </div>
    `);
    scrollDown();
}

let messageForm = $("#chat-send-message");
messageForm.on("submit", function (event) {
    let message = messageForm.find("[name='question']").val().trim();

    if (message.length !== 0) {
        addMessage(message, "end");

        messageForm.find("[name='question']").val("");
        messageForm.find("button[type='submit']").attr("disabled", "disabled");

        $.post({
            url: "",
            data: {
                message: message
            }
        })
        .done(function(data) {
            if (typeof data === 'object') {
                $("textarea[name='question']", "#ask-question").val(data.summary);
                $("textarea[name='question']", "#ask-question").attr("disabled", "disabled");
                $("button[name='edit']", "#ask-question").removeClass("d-none");
                $("td:last-child", "#question-scores").each(function (i) {
                    let scores = "";
                    for (let j = 1; j <= 5; j++) {
                        if (data.scores[i] === j) {
                            scores += `<i class="bi bi-${j}-circle-fill"></i> `;
                        } else {
                            scores += `<i class="bi bi-${j}-circle"></i> `;
                        }
                    }
                    $(this).html(scores);
                });
                $("button", "#ask-question").removeAttr("disabled");
                if (data.complete) {
                    $("button[name='ask']", "#ask-question").addClass("btn-primary");
                    $("button[name='ask']", "#ask-question").removeClass("btn-secondary");
                    $("#ask-question-card").addClass("has-success");
                } else {
                    $("button[name='ask']", "#ask-question").removeClass("btn-primary");
                    $("button[name='ask']", "#ask-question").addClass("btn-secondary");
                    $("#ask-question-card").removeClass("has-success");
                }
                addMessage(data.feedback, "start");
            } else {
                location.reload();
            }
        })
        .fail(function(data) {
            addMessage(data.responseText, "start");
        })
        .always(function() {
            messageForm.find("button[type='submit']").removeAttr("disabled");
        });
    }
    event.preventDefault();
});

messageForm.on("keypress", function(event) {
    if (event.keyCode === 13 && !event.shiftKey) {
        event.preventDefault();
        if (messageForm.find("button[type='submit']").attr("disabled") === undefined) {
            messageForm.submit();
        }
    }
});

$("button[name='ask']", "#ask-question").click(function () {
    if ($("button[name='ask']", "#ask-question").hasClass("btn-secondary")) {
        new bootstrap.Modal('#question-incomplete-modal').show();
    } else {
        $("#ask-question").trigger("submit");
    }
});

$("button[name='ask']", "#question-incomplete-modal").click(function() {
    $("#ask-question").append('<input type="hidden" name="ask" value="' + $(this).val() + "'");
    $("#ask-question").trigger("submit");
});

$("button[name='restart']", "#ask-question").click(function () {
    new bootstrap.Modal('#question-restart-modal').show() ;
});

$("button[name='restart']", "#question-restart-modal").click(function() {
    $("#ask-question").append('<input type="hidden" name="restart" value="' + $(this).val() + '">');
    $("#ask-question").trigger("submit");
});

$("button[name='edit']", "#ask-question").click(function () {
    new bootstrap.Modal('#question-edit-modal').show() ;
});

$("button[name='edit']", "#question-edit-modal").click(function() {
    $("textarea[name='question']", "#ask-question").removeAttr("disabled");
    $("button[name='edit']", "#ask-question").addClass("d-none");
});

const popoverTriggerList = document.querySelectorAll('[data-bs-toggle="popover"]');
[...popoverTriggerList].map(popoverTriggerEl => new bootstrap.Popover(popoverTriggerEl));
const tooltipTriggerList = document.querySelectorAll('[data-bs-toggle="tooltip"]');
[...tooltipTriggerList].map(tooltipTriggerEl => new bootstrap.Tooltip(tooltipTriggerEl));

scrollDown();
