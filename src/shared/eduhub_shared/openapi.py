"""
Generate src/shared/contracts/openapi.json from the route table and models.

Usage: python -m eduhub_shared.openapi            (write the file)
       python -m eduhub_shared.openapi --check    (exit 1 if the committed file is outdated)
"""
import json
import sys
from pathlib import Path
from typing import Any, Literal
from pydantic import BaseModel
from pydantic.json_schema import models_json_schema
from eduhub_shared.models import ErrorResponse
from eduhub_shared.routes import ROUTES, Route
from eduhub_shared.version import CONTRACT_VERSION

OPENAPI_PATH = Path(__file__).resolve().parents[1] / "contracts" / "openapi.json"
REF_TEMPLATE = "#/components/schemas/{model}"
STATUS_DESCRIPTIONS = {
    404: "Not found",
    422: "Invalid request",
    429: "Rate limited",
    500: "Internal error",
    501: "Feature disabled",
    503: "Data source unavailable",
}

Mode = Literal["validation", "serialization"]

def _model_modes() -> list[tuple[type[BaseModel], Mode]]:
    """
    List every model used by the API with its JSON-schema mode (requests: validation, responses: serialization).
    """
    pairs: list[tuple[type[BaseModel], Mode]] = [(ErrorResponse, "serialization")]
    for route in ROUTES:
        if route.request_model is not None and (route.request_model, "validation") not in pairs:
            pairs.append((route.request_model, "validation"))
        if (route.response_model, "serialization") not in pairs:
            pairs.append((route.response_model, "serialization"))
    return pairs

def _json_response(description: str, ref: dict[str, Any]) -> dict[str, Any]:
    """
    Build an OpenAPI response object with a JSON body.
    """
    return {"description": description, "content": {"application/json": {"schema": ref}}}

def _operation(route: Route, refs: dict[tuple[type[BaseModel], Mode], dict[str, Any]]) -> dict[str, Any]:
    """
    Build the OpenAPI operation object of one route.
    """
    operation: dict[str, Any] = {
        "operationId": route.operation_id,
        "summary": route.summary,
        "tags": [route.priority.value],
        "x-priority": route.priority.value,
    }
    if route.path_params:
        operation["parameters"] = [
            {"name": name, "in": "path", "required": True, "schema": {"type": "string"}} for name in route.path_params
        ]
    if route.request_model is not None:
        operation["requestBody"] = {
            "required": True,
            "content": {"application/json": {"schema": refs[(route.request_model, "validation")]}},
        }
    responses = {str(route.status_code): _json_response("Success", refs[(route.response_model, "serialization")])}
    error_ref = refs[(ErrorResponse, "serialization")]
    for status in route.error_statuses:
        responses[str(status)] = _json_response(STATUS_DESCRIPTIONS[status], error_ref)
    operation["responses"] = responses
    return operation

def build_openapi() -> dict[str, Any]:
    """
    Build the full OpenAPI 3.1 document of the contract.
    """
    refs, schema = models_json_schema(_model_modes(), ref_template=REF_TEMPLATE)
    paths: dict[str, dict[str, Any]] = {}
    for route in ROUTES:
        paths.setdefault(route.path, {})[route.method.lower()] = _operation(route, refs)
    return {
        "openapi": "3.1.0",
        "info": {
            "title": "EduHub Creator Analytics API",
            "version": CONTRACT_VERSION,
            "description": "Contract C4. Generated from eduhub_shared; do not edit by hand.",
        },
        "paths": paths,
        "components": {"schemas": schema.get("$defs", {})},
    }

def render_openapi() -> str:
    """
    Serialize the OpenAPI document deterministically.
    """
    return json.dumps(build_openapi(), indent=2, ensure_ascii=False) + "\n"

def main() -> None:
    """
    Write openapi.json, or verify it is up to date with --check.
    """
    rendered = render_openapi()
    if "--check" in sys.argv:
        current = OPENAPI_PATH.read_text(encoding="utf-8") if OPENAPI_PATH.exists() else ""
        if current != rendered:
            print("openapi.json is outdated: run `python -m eduhub_shared.openapi`", file=sys.stderr)
            sys.exit(1)
        print("openapi.json is up to date")
        return
    OPENAPI_PATH.parent.mkdir(parents=True, exist_ok=True)
    OPENAPI_PATH.write_text(rendered, encoding="utf-8")
    print(f"wrote {OPENAPI_PATH}")

if __name__ == "__main__":
    main()
