"""Flask surface: routes ``GET /`` and ``POST /submit``, delegates to
IntakeService.  Kept deliberately thin -- Flask knowledge stops here."""

from __future__ import annotations

from flask import Flask, Response, request

from .evagene_client import EvageneApiError
from .intake_service import IntakeService
from .intake_submission import IntakeValidationError, parse_intake_submission
from .views import error_page, form_page, success_page


def build_flask_app(*, service: IntakeService, evagene_base_url: str) -> Flask:
    app = Flask(__name__)

    @app.get("/")
    def _index() -> Response:
        return Response(form_page(), mimetype="text/html")

    @app.post("/submit")
    def _submit() -> Response:
        return _handle_submit(service, evagene_base_url)

    return app


def _handle_submit(service: IntakeService, evagene_base_url: str) -> Response:
    try:
        submission = parse_intake_submission(request.form)
    except IntakeValidationError as error:
        return Response(error_page(message=str(error)), status=400, mimetype="text/html")

    try:
        result = service.create(submission)
    except EvageneApiError as error:
        return Response(error_page(message=str(error)), status=502, mimetype="text/html")

    pedigree_url = f"{evagene_base_url.rstrip('/')}/pedigrees/{result.pedigree_id}"
    return Response(
        success_page(
            pedigree_id=result.pedigree_id,
            pedigree_url=pedigree_url,
            relatives_added=result.relatives_added,
        ),
        mimetype="text/html",
    )
