"""Request-model JSON schemas served for generated parameter forms."""

import asyncio
import json
from pathlib import Path

import pytest

from routes.correlation_routes import AutoCorrelationRequest
from routes.schema_routes import FORMS, get_form_schema

RENDERER_FIXTURE = (
    Path(__file__).resolve().parents[2] / "src" / "test" / "fixtures" / "form-schemas.json"
)


def test_served_schemas_match_the_renderer_test_fixture():
    # Regenerate the fixture when a form schema changes, so renderer tests
    # exercise exactly what the backend serves.
    served = {name: asyncio.run(get_form_schema(name))["data"] for name in FORMS}
    assert served == json.loads(RENDERER_FIXTURE.read_text())


def test_unknown_forms_are_not_served():
    assert asyncio.run(get_form_schema("project_routes"))["success"] is False


def test_form_fields_describe_bounds_choices_and_defaults():
    properties = asyncio.run(get_form_schema("auto_correlation"))["data"]["properties"]
    assert properties["dt"]["exclusiveMinimum"] == 0
    assert properties["dt"]["examples"] == [0.1]
    assert properties["mode"]["enum"] == ["same", "full"]
    assert properties["norm"]["default"] == "none"
    assert all(properties[name]["title"] for name in ("dt", "mode", "norm"))


@pytest.mark.parametrize("fields", [{"dt": -1.0}, {"dt": 1.0, "mode": "other"}])
def test_form_metadata_does_not_change_request_validation(fields):
    # The services keep validating these values and reporting their own
    # messages, exactly as before the schema metadata was added.
    AutoCorrelationRequest(event_list_name="ev", **fields)
