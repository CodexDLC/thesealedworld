import json
from typing import Annotated

from fastapi import APIRouter, Depends, Request
from fastapi.responses import RedirectResponse
from sqlalchemy.ext.asyncio import AsyncSession

from src.frontend.core.database import get_db
from src.frontend.core.renderer import UIRenderer, get_ui_renderer
from src.frontend.features.surveys.repositories.survey_repository import SurveyRepository
from src.frontend.features.surveys.services.survey_service import SurveyService

router = APIRouter(tags=["Surveys"])


@router.get("/survey/{token}", name="survey_respond")
async def survey_respond(
    token: str,
    db: Annotated[AsyncSession, Depends(get_db)],
    ui: Annotated[UIRenderer, Depends(get_ui_renderer)],
):
    repo = SurveyRepository(session=db)
    service = SurveyService(repo=repo)
    send = await service.get_survey_by_token(token)

    if send is None:
        return await ui.render("surveys/not_found.html", status_code=404)

    if send.response is not None:
        return await ui.render("surveys/thanks.html", context={"survey": send.survey})

    questions = send.survey.questions
    parsed_questions = []
    for q in questions:
        choices = json.loads(q.choices_json) if q.choices_json else None
        parsed_questions.append(
            {
                "id": q.id,
                "text": q.text,
                "type": q.question_type,
                "choices": choices,
            }
        )

    return await ui.render(
        "surveys/respond.html",
        context={"survey": send.survey, "questions": parsed_questions, "token": token},
    )


@router.post("/survey/{token}", name="survey_submit")
async def survey_submit(
    token: str,
    request: Request,
    db: Annotated[AsyncSession, Depends(get_db)],
    ui: Annotated[UIRenderer, Depends(get_ui_renderer)],
):
    repo = SurveyRepository(session=db)
    service = SurveyService(repo=repo)

    form_data = await request.form()
    answers = {}
    for key, value in form_data.items():
        if key.startswith("q_"):
            answers[key] = str(value)

    try:
        await service.submit_response(token=token, answers=answers)
    except Exception:
        return await ui.render("surveys/not_found.html", status_code=404)

    return await ui.render("surveys/thanks.html")


@router.get("/account/surveys", name="account_surveys")
async def account_surveys(
    request: Request,
    db: Annotated[AsyncSession, Depends(get_db)],
    ui: Annotated[UIRenderer, Depends(get_ui_renderer)],
):
    user = getattr(request.state, "user", None)
    if user is None:
        return RedirectResponse(url="/login", status_code=303)

    repo = SurveyRepository(session=db)
    service = SurveyService(repo=repo)
    sends = await service.get_user_surveys(user.id)

    items = []
    for s in sends:
        items.append(
            {
                "title": s.survey.title,
                "sent_at": s.sent_at.strftime("%d.%m.%Y"),
                "completed": s.response is not None,
                "token": s.token,
            }
        )

    return await ui.render("account/surveys/list.html", context={"surveys": items})
