from typing import Annotated

from fastapi import APIRouter, Depends, Request
from fastapi.responses import RedirectResponse
from sqlalchemy.ext.asyncio import AsyncSession

from src.frontend.core.database import get_db
from src.frontend.core.renderer import UIRenderer, get_ui_renderer
from src.frontend.features.feedback.dto.feedback_dto import FeedbackCreate
from src.frontend.features.feedback.repositories.feedback_repository import FeedbackRepository
from src.frontend.features.feedback.services.feedback_service import FeedbackService
from src.frontend.features.feedback.view_models.feedback_vm import FeedbackFormVM, FeedbackItemVM, FeedbackListVM

router = APIRouter(prefix="/account/feedback", tags=["Feedback"])


def _require_user(request: Request):
    user = getattr(request.state, "user", None)
    if user is None:
        return None
    return user


@router.get("", name="feedback_list")
async def feedback_list(
    request: Request,
    db: Annotated[AsyncSession, Depends(get_db)],
    ui: Annotated[UIRenderer, Depends(get_ui_renderer)],
):
    user = _require_user(request)
    if user is None:
        return RedirectResponse(url="/login", status_code=303)

    repo = FeedbackRepository(session=db)
    service = FeedbackService(repo=repo)
    items = await service.list_user_feedback(user.id)

    vm = FeedbackListVM(
        items=[
            FeedbackItemVM(
                id=f.id,
                type=f.type,
                title=f.title,
                status=f.status,
                created_at=f.created_at.strftime("%d.%m.%Y %H:%M"),
                priority=f.priority,
            )
            for f in items
        ]
    )
    return await ui.render("account/feedback/list.html", context={"feedback_list": vm})


@router.get("/new", name="feedback_new")
async def feedback_new(
    request: Request,
    ui: Annotated[UIRenderer, Depends(get_ui_renderer)],
):
    user = _require_user(request)
    if user is None:
        return RedirectResponse(url="/login", status_code=303)

    form_vm = FeedbackFormVM()
    preselect = request.query_params.get("type", "")
    return await ui.render(
        "account/feedback/new.html",
        context={"form": form_vm, "preselect_type": preselect},
    )


@router.post("/new", name="feedback_submit")
async def feedback_submit(
    request: Request,
    db: Annotated[AsyncSession, Depends(get_db)],
    ui: Annotated[UIRenderer, Depends(get_ui_renderer)],
):
    user = _require_user(request)
    if user is None:
        return RedirectResponse(url="/login", status_code=303)

    form_data = await request.form()
    priority = form_data.get("priority") or None

    try:
        data = FeedbackCreate(
            type=str(form_data.get("type", "")),
            title=str(form_data.get("title", "")),
            body=str(form_data.get("body", "")),
            priority=priority,
        )
    except Exception:
        form_vm = FeedbackFormVM()
        return await ui.render(
            "account/feedback/new.html",
            context={"form": form_vm, "preselect_type": "", "error": "Проверьте заполнение полей"},
        )

    repo = FeedbackRepository(session=db)
    service = FeedbackService(repo=repo)
    await service.submit(user_id=user.id, data=data)

    return RedirectResponse(url="/account/feedback", status_code=303)


@router.get("/{feedback_id:int}", name="feedback_detail")
async def feedback_detail(
    request: Request,
    feedback_id: int,
    db: Annotated[AsyncSession, Depends(get_db)],
    ui: Annotated[UIRenderer, Depends(get_ui_renderer)],
):
    user = _require_user(request)
    if user is None:
        return RedirectResponse(url="/login", status_code=303)

    repo = FeedbackRepository(session=db)
    service = FeedbackService(repo=repo)
    feedback = await service.get_feedback(feedback_id)

    if feedback is None or feedback.user_id != user.id:
        return RedirectResponse(url="/account/feedback", status_code=303)

    return await ui.render("account/feedback/detail.html", context={"feedback": feedback})
