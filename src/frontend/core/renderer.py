from typing import Any

from fastapi import Request
from fastapi.templating import Jinja2Templates


class UIRenderer:
    """
    Advanced UI Renderer for the Gateway.
    Handles global context injection and HTMX-specific logic.
    """

    def __init__(self, request: Request, templates: Jinja2Templates):
        self.request = request
        self.templates = templates

    async def render(self, template_name: str, context: dict[str, Any] | None = None, status_code: int = 200):
        """
        Render template with automatic global context.
        """
        context = context or {}

        # 1. Automatic Global Context
        # We pull data from request.state where middleware/dependencies put it
        global_context = {
            "request": self.request,
            "user": getattr(self.request.state, "user", None),
            "is_htmx": "HX-Request" in self.request.headers,
            # We can add more common things here (e.g. app settings, flash messages)
        }

        # 2. Merge contexts
        final_context = {**global_context, **context}

        # 3. Handle HTMX Fragments (optional logic)
        # If we want to automatically switch base templates based on HX-Request,
        # we can pass 'base_template' to the context.
        # If we want to automatically switch base templates based on HX-Request,
        # we can pass 'base_template' to the context.
        if global_context["is_htmx"] and "base_template" not in final_context:
            final_context["base_template"] = "includes/minimal.html"
        elif "base_template" not in final_context:
            final_context["base_template"] = "site/base_site.html"

        return self.templates.TemplateResponse(
            request=self.request,
            name=template_name,
            context=final_context,
            status_code=status_code,
        )


def get_ui_renderer(request: Request) -> UIRenderer:
    """
    Dependency to get an initialized UIRenderer.
    Requires 'templates' to be attached to app.state.
    """
    return UIRenderer(request, request.app.state.templates)
