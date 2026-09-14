#!/usr/bin/env python3
"""
Generate an OpenAPI 3.0 document for Canvas LMS from Instructure's live,
machine-readable Canvas API documentation.

Source of truth:
  https://canvas.instructure.com/doc/api/api-docs.json
and each resource declaration referenced by that index.

The published Canvas docs are generated from Canvas LMS source/YARD docs.
No credentials are read or written by this script.
"""

from __future__ import annotations

import concurrent.futures
import datetime as dt
import hashlib
import json
import os
import re
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from collections import defaultdict
from pathlib import Path
from typing import Any

INDEX_URL = "https://canvas.instructure.com/doc/api/api-docs.json"
DOC_ROOT = "https://canvas.instructure.com/doc/api"
TARGET_SERVER = os.getenv("CANVAS_OPENAPI_SERVER", "https://canvas.northeastern.edu/api")
OUTPUT = Path(os.getenv("CANVAS_OPENAPI_OUTPUT", "canvas.openapi.json"))
META_OUTPUT = Path(os.getenv("CANVAS_OPENAPI_META_OUTPUT", "canvas.openapi.meta.json"))
USER_AGENT = "Canvas-OpenAPI-Retool-Generator/1.0 (+https://github.com/instructure/canvas-lms)"

HTTP_METHODS = {"get", "post", "put", "patch", "delete", "options", "head"}
component_names: dict[str, str] = {}
used_component_names: set[str] = set()


def fetch_json(url: str, attempts: int = 4) -> dict[str, Any]:
    last: Exception | None = None
    for attempt in range(1, attempts + 1):
        try:
            req = urllib.request.Request(
                url,
                headers={
                    "User-Agent": USER_AGENT,
                    "Accept": "application/json",
                },
            )
            with urllib.request.urlopen(req, timeout=45) as resp:
                return json.load(resp)
        except (urllib.error.URLError, TimeoutError, json.JSONDecodeError) as exc:
            last = exc
            if attempt < attempts:
                time.sleep(min(2 ** attempt, 8))
    raise RuntimeError(f"Failed to fetch {url} after {attempts} attempts: {last}")


def safe_component_name(name: str) -> str:
    if name in component_names:
        return component_names[name]
    base = re.sub(r"[^A-Za-z0-9._-]", "_", str(name)).strip("._-") or "AnonymousModel"
    candidate = base
    if candidate in used_component_names:
        suffix = hashlib.sha1(str(name).encode("utf-8")).hexdigest()[:8]
        candidate = f"{base}_{suffix}"
    component_names[name] = candidate
    used_component_names.add(candidate)
    return candidate


def clean_text(value: Any) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    return text or None


def normalize_type(value: Any) -> tuple[str | None, str | None]:
    if value is None:
        return None, None
    raw = str(value)
    low = raw.lower()
    if low in {"datetime", "date-time", "timestamp"}:
        return "string", "date-time"
    if low == "date":
        return "string", "date"
    if low in {"integer", "int", "int32", "int64", "long"}:
        return "integer", None
    if low in {"number", "float", "double", "decimal"}:
        return "number", None
    if low in {"boolean", "bool"}:
        return "boolean", None
    if low in {"array"}:
        return "array", None
    if low in {"object", "hash"}:
        return "object", None
    if low in {"file"}:
        return "string", "binary"
    if low in {"void", "null"}:
        return None, None
    return "string", None


def legacy_schema(obj: Any) -> dict[str, Any]:
    if obj is None:
        return {}
    if isinstance(obj, str):
        return {"type": "string"}
    if not isinstance(obj, dict):
        return {}

    if "$ref" in obj:
        ref_name = str(obj["$ref"])
        out: dict[str, Any] = {
            "$ref": f"#/components/schemas/{safe_component_name(ref_name)}"
        }
        description = clean_text(obj.get("description"))
        if description:
            # OAS 3.0 siblings of $ref are ignored by many parsers, so preserve as extension.
            out["x-canvas-description"] = description
        return out

    typ, inferred_format = normalize_type(obj.get("type"))
    out: dict[str, Any] = {}
    if typ:
        out["type"] = typ

    fmt = obj.get("format") or inferred_format
    if fmt and fmt not in {"null", "None"}:
        out["format"] = str(fmt)

    if typ == "array":
        out["items"] = legacy_schema(obj.get("items") or {"type": "string"})

    if "properties" in obj and isinstance(obj["properties"], dict):
        out["type"] = "object"
        out["properties"] = {
            str(k): legacy_schema(v) for k, v in obj["properties"].items()
        }

    additional = obj.get("additionalProperties")
    if additional is not None:
        out["additionalProperties"] = (
            legacy_schema(additional) if isinstance(additional, dict) else bool(additional)
        )

    description = clean_text(obj.get("description"))
    if description:
        out["description"] = description

    if "example" in obj and obj["example"] is not None:
        out["example"] = obj["example"]
    if "defaultValue" in obj and obj["defaultValue"] is not None:
        out["default"] = obj["defaultValue"]
    elif "default" in obj and obj["default"] is not None:
        out["default"] = obj["default"]

    enum = obj.get("enum")
    if not enum and isinstance(obj.get("allowableValues"), dict):
        enum = obj["allowableValues"].get("values")
    if isinstance(enum, list) and enum:
        # Some legacy Canvas docs mark an array parameter while enum values describe
        # the allowed values for each item.
        if out.get("type") == "array":
            out.setdefault("items", {"type": "string"})
            if isinstance(out["items"], dict):
                out["items"]["enum"] = enum
        else:
            out["enum"] = enum

    for old_key, new_key in (
        ("minimum", "minimum"),
        ("maximum", "maximum"),
        ("minLength", "minLength"),
        ("maxLength", "maxLength"),
        ("pattern", "pattern"),
    ):
        if old_key in obj and obj[old_key] is not None:
            out[new_key] = obj[old_key]

    return out


def model_schema(model: dict[str, Any]) -> dict[str, Any]:
    schema: dict[str, Any] = {"type": "object"}
    description = clean_text(model.get("description"))
    if description:
        schema["description"] = description

    props = model.get("properties")
    if isinstance(props, dict):
        schema["properties"] = {
            str(name): legacy_schema(prop) for name, prop in props.items()
        }

    required = model.get("required")
    if isinstance(required, list) and required:
        schema["required"] = [str(x) for x in required]

    if model.get("deprecated"):
        schema["deprecated"] = True
    return schema


def parameter_schema(param: dict[str, Any]) -> dict[str, Any]:
    return legacy_schema(param)


def make_parameter(param: dict[str, Any]) -> dict[str, Any]:
    location = str(param.get("paramType") or "query").lower()
    if location == "formdata":
        location = "query"
    result: dict[str, Any] = {
        "name": str(param.get("name") or "parameter"),
        "in": location,
        "required": bool(param.get("required")) if location != "path" else True,
        "schema": parameter_schema(param),
    }
    description = clean_text(param.get("description"))
    if description:
        result["description"] = description
    if param.get("deprecated"):
        result["deprecated"] = True

    if result["schema"].get("type") == "array":
        result["style"] = "form"
        result["explode"] = True

    return result


def response_schema(op: dict[str, Any]) -> dict[str, Any]:
    if op.get("type") == "array":
        return {
            "type": "array",
            "items": legacy_schema(op.get("items") or {"type": "object"}),
        }
    if op.get("type"):
        return legacy_schema(
            {
                "type": op.get("type"),
                "format": op.get("format"),
                "items": op.get("items"),
                "$ref": op.get("$ref"),
            }
        )
    if op.get("$ref"):
        return legacy_schema({"$ref": op["$ref"]})
    return {}


def form_request_body(form_params: list[dict[str, Any]]) -> dict[str, Any]:
    properties: dict[str, Any] = {}
    required: list[str] = []
    has_file = False
    for p in form_params:
        name = str(p.get("name") or "field")
        schema = parameter_schema(p)
        if schema.get("format") == "binary":
            has_file = True
        properties[name] = schema
        if p.get("required"):
            required.append(name)

    obj_schema: dict[str, Any] = {"type": "object", "properties": properties}
    if required:
        obj_schema["required"] = required

    media_type = "multipart/form-data" if has_file else "application/x-www-form-urlencoded"
    return {
        "required": bool(required),
        "content": {
            media_type: {
                "schema": obj_schema
            }
        },
    }


def body_request_body(body_params: list[dict[str, Any]]) -> dict[str, Any]:
    if len(body_params) == 1:
        p = body_params[0]
        schema = parameter_schema(p)
        return {
            "required": bool(p.get("required")),
            "description": clean_text(p.get("description")) or "",
            "content": {"application/json": {"schema": schema}},
        }

    props: dict[str, Any] = {}
    required: list[str] = []
    for p in body_params:
        name = str(p.get("name") or "body")
        props[name] = parameter_schema(p)
        if p.get("required"):
            required.append(name)
    schema: dict[str, Any] = {"type": "object", "properties": props}
    if required:
        schema["required"] = required
    return {
        "required": bool(required),
        "content": {"application/json": {"schema": schema}},
    }


def unique_operation_id(raw: str | None, resource_slug: str, used: set[str]) -> str:
    base = re.sub(r"[^A-Za-z0-9._-]", "_", raw or "operation").strip("._-") or "operation"
    candidate = base
    if candidate in used:
        suffix = re.sub(r"[^A-Za-z0-9]", "_", resource_slug).strip("_")
        candidate = f"{base}_{suffix}" if suffix else f"{base}_duplicate"
    count = 2
    original = candidate
    while candidate in used:
        candidate = f"{original}_{count}"
        count += 1
    used.add(candidate)
    return candidate


def build_operation(
    op: dict[str, Any],
    api_entry: dict[str, Any],
    tag: str,
    resource_slug: str,
    used_operation_ids: set[str],
) -> dict[str, Any]:
    result: dict[str, Any] = {
        "tags": [tag],
        "operationId": unique_operation_id(
            clean_text(op.get("nickname")), resource_slug, used_operation_ids
        ),
        "responses": {},
    }

    summary = clean_text(op.get("summary"))
    if summary:
        result["summary"] = summary

    notes = clean_text(op.get("notes"))
    api_desc = clean_text(api_entry.get("description"))
    description_parts = []
    if notes:
        description_parts.append(notes)
    elif api_desc:
        description_parts.append(api_desc)

    if "paginated" in (notes or api_desc or "").lower():
        description_parts.append(
            "Canvas pagination: follow the HTTP Link response header until no rel=\"next\" link remains."
        )
        result["x-canvas-paginated"] = True

    if description_parts:
        result["description"] = "\n\n".join(description_parts)

    if op.get("deprecated"):
        result["deprecated"] = True
        dep = clean_text(op.get("deprecation_description"))
        if dep:
            result["description"] = (
                (result.get("description", "") + "\n\nDeprecated: " + dep).strip()
            )

    ordinary_params: list[dict[str, Any]] = []
    form_params: list[dict[str, Any]] = []
    body_params: list[dict[str, Any]] = []

    for p in op.get("parameters") or []:
        if not isinstance(p, dict):
            continue
        kind = str(p.get("paramType") or "query").lower()
        if kind in {"form", "formdata"}:
            form_params.append(p)
        elif kind == "body":
            body_params.append(p)
        elif kind in {"path", "query", "header"}:
            ordinary_params.append(make_parameter(p))
        else:
            # Preserve unknown legacy parameter locations as query params rather than dropping them.
            q = dict(p)
            q["paramType"] = "query"
            ordinary_params.append(make_parameter(q))

    if ordinary_params:
        result["parameters"] = ordinary_params
    if body_params:
        result["requestBody"] = body_request_body(body_params)
    elif form_params:
        result["requestBody"] = form_request_body(form_params)

    schema = response_schema(op)
    response_obj: dict[str, Any] = {
        "description": "Successful Canvas API response",
        "headers": {
            "Link": {
                "description": "RFC 5988 pagination links when the response is paginated.",
                "schema": {"type": "string"},
            },
            "X-Request-Cost": {
                "description": "Canvas request cost used for throttling.",
                "schema": {"type": "number"},
            },
            "X-Rate-Limit-Remaining": {
                "description": "Approximate remaining Canvas API capacity.",
                "schema": {"type": "number"},
            },
        },
    }
    if schema:
        response_obj["content"] = {
            "application/json": {
                "schema": schema
            }
        }
    result["responses"]["200"] = response_obj
    result["responses"]["401"] = {"description": "Unauthorized or invalid Canvas access token"}
    result["responses"]["403"] = {"description": "Authenticated, but not permitted to access this Canvas resource"}
    result["responses"]["404"] = {"description": "Canvas resource not found"}

    return result


def fetch_resource(entry: dict[str, Any]) -> tuple[dict[str, Any], str]:
    path = str(entry["path"])
    url = urllib.parse.urljoin(DOC_ROOT + "/", path.lstrip("/"))
    return fetch_json(url), url


def main() -> int:
    generated_at = dt.datetime.now(dt.timezone.utc).replace(microsecond=0).isoformat()

    index = fetch_json(INDEX_URL)
    entries = index.get("apis") or []
    if not entries:
        raise RuntimeError("Canvas API resource listing contained no APIs")

    docs: list[tuple[dict[str, Any], dict[str, Any], str]] = []
    failures: list[dict[str, str]] = []

    with concurrent.futures.ThreadPoolExecutor(max_workers=12) as pool:
        future_map = {pool.submit(fetch_resource, e): e for e in entries}
        for future in concurrent.futures.as_completed(future_map):
            entry = future_map[future]
            try:
                doc, url = future.result()
                docs.append((entry, doc, url))
                print(f"Fetched {entry.get('path')}", file=sys.stderr)
            except Exception as exc:
                failures.append({"path": str(entry.get("path")), "error": str(exc)})
                print(f"WARNING: {entry.get('path')}: {exc}", file=sys.stderr)

    if failures:
        # A supposedly complete spec must not silently omit a Canvas resource group.
        raise RuntimeError(
            "Could not fetch every Canvas resource declaration. "
            + json.dumps(failures, indent=2)
        )

    docs.sort(key=lambda item: str(item[0].get("path")))

    # Pre-register model names so references are deterministic.
    for _, doc, _ in docs:
        for model_name in (doc.get("models") or {}).keys():
            safe_component_name(str(model_name))

    components: dict[str, Any] = {}
    model_sources: dict[str, list[str]] = defaultdict(list)

    for _, doc, url in docs:
        for model_name, model in (doc.get("models") or {}).items():
            if not isinstance(model, dict):
                continue
            safe = safe_component_name(str(model_name))
            converted = model_schema(model)
            model_sources[safe].append(url)
            if safe not in components:
                components[safe] = converted
            else:
                # Prefer whichever declaration provides more documented properties.
                old_props = len((components[safe].get("properties") or {}))
                new_props = len((converted.get("properties") or {}))
                if new_props > old_props:
                    components[safe] = converted

    paths: dict[str, Any] = {}
    tags: dict[str, str] = {}
    used_operation_ids: set[str] = set()
    duplicate_operations: list[dict[str, str]] = []

    for entry, doc, url in docs:
        tag = clean_text(entry.get("description")) or clean_text(doc.get("resourcePath")) or "Canvas"
        tag = str(tag)
        tags[tag] = url
        resource_slug = str(entry.get("path") or "resource").strip("/").replace(".json", "")

        for api in doc.get("apis") or []:
            if not isinstance(api, dict):
                continue
            path = str(api.get("path") or "")
            if not path.startswith("/"):
                path = "/" + path
            if not path or path == "/":
                continue
            path_item = paths.setdefault(path, {})

            for op in api.get("operations") or []:
                if not isinstance(op, dict):
                    continue
                method = str(op.get("method") or "GET").lower()
                if method not in HTTP_METHODS:
                    continue
                converted = build_operation(
                    op, api, tag, resource_slug, used_operation_ids
                )
                converted["x-canvas-source"] = url

                if method in path_item:
                    # Duplicate route declarations exist in the legacy docs. Keep the richer
                    # operation while preserving all tags and record the collision.
                    duplicate_operations.append(
                        {"path": path, "method": method, "source": url}
                    )
                    existing = path_item[method]
                    merged_tags = sorted(
                        set(existing.get("tags") or []) | set(converted.get("tags") or [])
                    )
                    existing["tags"] = merged_tags
                    old_score = len(existing.get("parameters") or []) + len(existing.get("description") or "")
                    new_score = len(converted.get("parameters") or []) + len(converted.get("description") or "")
                    if new_score > old_score:
                        converted["tags"] = merged_tags
                        path_item[method] = converted
                else:
                    path_item[method] = converted

    # Ensure every referenced legacy model has a component, even if Canvas referenced
    # a model that is documented in a different or unpublished resource declaration.
    for original, safe in component_names.items():
        components.setdefault(
            safe,
            {
                "type": "object",
                "description": f"Canvas model reference: {original}. The published legacy declaration did not provide a full schema.",
            },
        )

    spec: dict[str, Any] = {
        "openapi": "3.0.3",
        "info": {
            "title": "Canvas LMS API — Northeastern Retool",
            "version": f"live-{generated_at[:10]}",
            "description": (
                "OpenAPI 3.0 conversion of Instructure's live machine-readable Canvas LMS API "
                "documentation, generated for Retool. The endpoint and model source is "
                "https://canvas.instructure.com/doc/api/api-docs.json and its referenced "
                "resource declarations. Requests are targeted at Northeastern's Canvas tenant. "
                "This specification contains no access token or other secret."
            ),
        },
        "servers": [
            {
                "url": TARGET_SERVER.rstrip("/"),
                "description": "Northeastern University Canvas API",
            }
        ],
        "security": [{"bearerAuth": []}],
        "tags": [
            {
                "name": name,
                "description": f"Canvas resource group. Source: {source}",
            }
            for name, source in sorted(tags.items())
        ],
        "paths": dict(sorted(paths.items())),
        "components": {
            "securitySchemes": {
                "bearerAuth": {
                    "type": "http",
                    "scheme": "bearer",
                    "bearerFormat": "Canvas access token",
                    "description": "Canvas API access token. Store the actual token only in Retool's sanitized Authorization header.",
                }
            },
            "schemas": dict(sorted(components.items())),
        },
        "x-canvas-generation": {
            "generatedAt": generated_at,
            "sourceIndex": INDEX_URL,
            "sourceSwaggerVersion": index.get("swaggerVersion"),
            "sourceApiVersion": index.get("apiVersion"),
            "resourceDeclarationsFetched": len(docs),
            "targetServer": TARGET_SERVER.rstrip("/"),
            "duplicateRouteDeclarationsResolved": len(duplicate_operations),
            "generator": "tools/generate_canvas_openapi.py",
        },
    }

    OUTPUT.write_text(
        json.dumps(spec, ensure_ascii=False, indent=2, sort_keys=False) + "\n",
        encoding="utf-8",
    )

    meta = {
        "generated_at": generated_at,
        "source_index": INDEX_URL,
        "source_swagger_version": index.get("swaggerVersion"),
        "resource_count": len(docs),
        "path_count": len(paths),
        "operation_count": sum(
            1
            for item in paths.values()
            for method in item.keys()
            if method in HTTP_METHODS
        ),
        "schema_count": len(components),
        "target_server": TARGET_SERVER.rstrip("/"),
        "output_bytes": OUTPUT.stat().st_size,
        "sha256": hashlib.sha256(OUTPUT.read_bytes()).hexdigest(),
        "duplicate_route_declarations": duplicate_operations,
        "resource_sources": [url for _, _, url in docs],
        "model_sources": dict(sorted(model_sources.items())),
    }
    META_OUTPUT.write_text(
        json.dumps(meta, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )

    print(json.dumps({
        "paths": meta["path_count"],
        "operations": meta["operation_count"],
        "schemas": meta["schema_count"],
        "bytes": meta["output_bytes"],
        "sha256": meta["sha256"],
    }, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
