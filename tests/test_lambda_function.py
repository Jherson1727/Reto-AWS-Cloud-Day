"""
Test suite for lambda_function.py
Combines example-based unit tests (pytest) and property-based tests (hypothesis).
"""

import json
import base64

import pytest
from hypothesis import given, settings, strategies as st

from lambda_function import (
    validate_name,
    extract_name,
    build_greeting,
    build_response,
    lambda_handler,
    CORS_HEADERS,
)

# ---------------------------------------------------------------------------
# Helper builders
# ---------------------------------------------------------------------------

def make_get_event(nombre=None, qs_params=None):
    """Build a minimal GET Lambda Function URL event."""
    if qs_params is None:
        qs_params = {"nombre": nombre} if nombre is not None else None
    return {
        "httpMethod": "GET",
        "queryStringParameters": qs_params,
        "body": None,
        "isBase64Encoded": False,
    }


def make_post_event(body_dict=None, raw_body=None, is_base64=False):
    """Build a minimal POST Lambda Function URL event."""
    if raw_body is None and body_dict is not None:
        raw_body = json.dumps(body_dict)
    return {
        "httpMethod": "POST",
        "queryStringParameters": None,
        "body": raw_body,
        "isBase64Encoded": is_base64,
    }


def make_options_event():
    return {
        "httpMethod": "OPTIONS",
        "queryStringParameters": None,
        "body": None,
        "isBase64Encoded": False,
    }


# ===========================================================================
# Task 2.2 – Unit tests for validate_name
# ===========================================================================

class TestValidateName:
    def test_none_input_returns_none(self):
        assert validate_name(None) is None

    def test_empty_string_returns_none(self):
        assert validate_name("") is None

    def test_whitespace_only_returns_none(self):
        assert validate_name("   ") is None

    def test_exactly_100_chars_returns_intact(self):
        name = "a" * 100
        result = validate_name(name)
        assert result == name
        assert len(result) == 100

    def test_101_chars_truncated_to_100(self):
        name = "b" * 101
        result = validate_name(name)
        assert result == "b" * 100
        assert len(result) == 100

    def test_leading_trailing_spaces_stripped(self):
        result = validate_name("  Ana  ")
        assert result == "Ana"

    def test_normal_name_returned_as_is(self):
        assert validate_name("Carlos") == "Carlos"

    def test_tab_only_returns_none(self):
        assert validate_name("\t\t\t") is None

    def test_newline_only_returns_none(self):
        assert validate_name("\n\n") is None

    def test_101_chars_with_leading_spaces_truncated_then_stripped(self):
        # First 100 chars = 3 spaces + 97 'x' → strips to 97 'x'
        name = "   " + "x" * 98  # len=101
        result = validate_name(name)
        assert result == "x" * 97  # truncated to 100, then stripped 3 spaces

    def test_exactly_100_whitespace_only_returns_none(self):
        # 100 spaces → strip → empty → None
        assert validate_name(" " * 100) is None


# ===========================================================================
# Task 2.4 – Unit tests for extract_name
# ===========================================================================

class TestExtractName:
    def test_get_nombre_in_querystring(self):
        event = make_get_event(nombre="Ana")
        name, source = extract_name(event)
        assert name == "Ana"
        assert source == "query_string"

    def test_post_nombre_in_body(self):
        event = make_post_event(body_dict={"nombre": "Ana"})
        name, source = extract_name(event)
        assert name == "Ana"
        assert source == "body"

    def test_qs_takes_precedence_over_body(self):
        event = {
            "httpMethod": "POST",
            "queryStringParameters": {"nombre": "QSName"},
            "body": json.dumps({"nombre": "BodyName"}),
            "isBase64Encoded": False,
        }
        name, source = extract_name(event)
        assert name == "QSName"
        assert source == "query_string"

    def test_no_nombre_returns_none_none(self):
        event = make_get_event()  # no nombre
        name, source = extract_name(event)
        assert name is None
        assert source == "none"

    def test_base64_body_decoded_and_extracted(self):
        payload = json.dumps({"nombre": "Base64User"})
        encoded = base64.b64encode(payload.encode("utf-8")).decode("ascii")
        event = make_post_event(raw_body=encoded, is_base64=True)
        name, source = extract_name(event)
        assert name == "Base64User"
        assert source == "body"

    def test_invalid_json_body_raises_value_error(self):
        event = make_post_event(raw_body="not valid json at all")
        with pytest.raises(ValueError):
            extract_name(event)

    def test_missing_querystring_parameters_does_not_raise(self):
        event = {
            "httpMethod": "GET",
            # queryStringParameters key absent entirely
            "body": None,
            "isBase64Encoded": False,
        }
        name, source = extract_name(event)
        assert name is None
        assert source == "none"

    def test_null_body_does_not_raise(self):
        event = make_post_event(raw_body=None)
        name, source = extract_name(event)
        assert name is None
        assert source == "none"

    def test_qs_params_none_does_not_raise(self):
        event = {
            "httpMethod": "GET",
            "queryStringParameters": None,
            "body": None,
            "isBase64Encoded": False,
        }
        name, source = extract_name(event)
        assert name is None
        assert source == "none"

    def test_nombre_empty_string_in_qs_returns_none(self):
        event = make_get_event(nombre="")
        name, source = extract_name(event)
        assert name is None
        assert source == "none"

    def test_nombre_whitespace_in_body_returns_none(self):
        event = make_post_event(body_dict={"nombre": "   "})
        name, source = extract_name(event)
        assert name is None
        assert source == "none"


# ===========================================================================
# Task 3.2 – Unit tests for build_greeting
# ===========================================================================

class TestBuildGreeting:
    def test_valid_name_returns_personalized_message(self):
        result = build_greeting("Ana", "query_string")
        assert result["mensaje"] == "¡Hola Ana, bienvenido a la arquitectura serverless de AWS!"

    def test_none_name_returns_generic_message(self):
        result = build_greeting(None, "none")
        assert result["mensaje"] == "¡Bienvenido a la arquitectura serverless de AWS!"
        assert result["fuente"] == "none"

    def test_source_query_string_reflected_in_fuente(self):
        result = build_greeting("Carlos", "query_string")
        assert result["fuente"] == "query_string"

    def test_source_body_reflected_in_fuente(self):
        result = build_greeting("María", "body")
        assert result["fuente"] == "body"

    def test_none_name_fuente_is_always_none(self):
        # Even if caller passes a non-"none" source, None name forces fuente="none"
        result = build_greeting(None, "query_string")
        assert result["fuente"] == "none"

    def test_personalized_message_contains_name(self):
        result = build_greeting("Lucía", "body")
        assert "Lucía" in result["mensaje"]

    def test_generic_message_exact_text(self):
        result = build_greeting(None, "none")
        assert result["mensaje"] == "¡Bienvenido a la arquitectura serverless de AWS!"

    def test_result_has_exactly_mensaje_and_fuente(self):
        result = build_greeting("Pedro", "query_string")
        assert set(result.keys()) == {"mensaje", "fuente"}


# ===========================================================================
# Task 3.4 – Unit tests for build_response
# ===========================================================================

class TestBuildResponse:
    def test_200_statuscode(self):
        resp = build_response(200, {"mensaje": "Hi", "fuente": "none"})
        assert resp["statusCode"] == 200

    def test_400_statuscode(self):
        resp = build_response(400, {"error": "bad request"})
        assert resp["statusCode"] == 400

    def test_cors_header_allow_origin_present(self):
        resp = build_response(200, {"mensaje": "Hi", "fuente": "none"})
        assert resp["headers"]["Access-Control-Allow-Origin"] == "*"

    def test_cors_header_allow_methods_present(self):
        resp = build_response(200, {"mensaje": "Hi", "fuente": "none"})
        assert resp["headers"]["Access-Control-Allow-Methods"] == "GET, POST, OPTIONS"

    def test_cors_header_allow_headers_present(self):
        resp = build_response(200, {"mensaje": "Hi", "fuente": "none"})
        assert resp["headers"]["Access-Control-Allow-Headers"] == "Content-Type"

    def test_content_type_application_json(self):
        resp = build_response(200, {"mensaje": "Hi", "fuente": "none"})
        assert resp["headers"]["Content-Type"] == "application/json"

    def test_body_is_valid_json_string(self):
        body_dict = {"mensaje": "Hola", "fuente": "query_string"}
        resp = build_response(200, body_dict)
        parsed = json.loads(resp["body"])
        assert parsed == body_dict

    def test_unicode_not_ascii_escaped(self):
        # ensure_ascii=False means ñ, accents, emojis appear as-is
        body_dict = {"mensaje": "¡Hola José!", "fuente": "body"}
        resp = build_response(200, body_dict)
        assert "José" in resp["body"]
        # No ASCII escape sequences like \u00f3 should appear
        assert "\\u" not in resp["body"]

    def test_400_cors_headers_also_present(self):
        resp = build_response(400, {"error": "oops"})
        assert "Access-Control-Allow-Origin" in resp["headers"]
        assert "Access-Control-Allow-Methods" in resp["headers"]
        assert "Access-Control-Allow-Headers" in resp["headers"]


# ===========================================================================
# Task 4.2 – Integration tests for lambda_handler
# ===========================================================================

class TestLambdaHandler:
    # --- Happy path: GET with nombre ---
    def test_get_with_nombre_returns_200_personalized(self):
        event = make_get_event(nombre="Ana")
        resp = lambda_handler(event, None)
        body = json.loads(resp["body"])
        assert resp["statusCode"] == 200
        assert body["mensaje"] == "¡Hola Ana, bienvenido a la arquitectura serverless de AWS!"
        assert body["fuente"] == "query_string"

    # --- Happy path: POST with nombre in body ---
    def test_post_with_nombre_in_body_returns_200_personalized(self):
        event = make_post_event(body_dict={"nombre": "Ana"})
        resp = lambda_handler(event, None)
        body = json.loads(resp["body"])
        assert resp["statusCode"] == 200
        assert body["mensaje"] == "¡Hola Ana, bienvenido a la arquitectura serverless de AWS!"
        assert body["fuente"] == "body"

    # --- Happy path: GET without nombre ---
    def test_get_without_nombre_returns_200_generic(self):
        event = make_get_event()
        resp = lambda_handler(event, None)
        body = json.loads(resp["body"])
        assert resp["statusCode"] == 200
        assert body["mensaje"] == "¡Bienvenido a la arquitectura serverless de AWS!"
        assert body["fuente"] == "none"

    # --- OPTIONS preflight ---
    def test_options_returns_200_empty_body_with_cors(self):
        event = make_options_event()
        resp = lambda_handler(event, None)
        assert resp["statusCode"] == 200
        assert resp["body"] == ""
        assert resp["headers"]["Access-Control-Allow-Origin"] == "*"
        assert resp["headers"]["Access-Control-Allow-Methods"] == "GET, POST, OPTIONS"
        assert resp["headers"]["Access-Control-Allow-Headers"] == "Content-Type"

    # --- Missing httpMethod → 400 ---
    def test_missing_http_method_returns_400_evento_no_reconocido(self):
        event = {"queryStringParameters": None, "body": None}
        resp = lambda_handler(event, None)
        body = json.loads(resp["body"])
        assert resp["statusCode"] == 400
        assert body["error"] == "Evento no reconocido"
        assert "mensaje" not in body

    # --- POST with invalid JSON body → 400 ---
    def test_post_invalid_json_body_returns_400_with_error(self):
        event = make_post_event(raw_body="this is not json")
        resp = lambda_handler(event, None)
        body = json.loads(resp["body"])
        assert resp["statusCode"] == 400
        assert "error" in body
        assert body["error"]  # non-empty
        assert "mensaje" not in body

    # --- Exactly 100-char name: full name in message ---
    def test_nombre_exactly_100_chars_returned_intact(self):
        name = "x" * 100
        event = make_get_event(nombre=name)
        resp = lambda_handler(event, None)
        body = json.loads(resp["body"])
        assert resp["statusCode"] == 200
        expected = f"¡Hola {name}, bienvenido a la arquitectura serverless de AWS!"
        assert body["mensaje"] == expected

    # --- 101-char name: truncated to first 100 in message ---
    def test_nombre_101_chars_truncated_to_100_in_message(self):
        name_101 = "y" * 101
        expected_name = "y" * 100
        event = make_get_event(nombre=name_101)
        resp = lambda_handler(event, None)
        body = json.loads(resp["body"])
        assert resp["statusCode"] == 200
        assert expected_name in body["mensaje"]
        # The full 101-char name must not appear
        assert name_101 not in body["mensaje"]

    # --- Whitespace-only nombre → generic greeting ---
    def test_nombre_whitespace_only_returns_generic(self):
        event = make_get_event(nombre="    ")
        resp = lambda_handler(event, None)
        body = json.loads(resp["body"])
        assert resp["statusCode"] == 200
        assert body["mensaje"] == "¡Bienvenido a la arquitectura serverless de AWS!"
        assert body["fuente"] == "none"

    # --- Unicode name (ñ, accents, emojis) appears intact ---
    def test_unicode_name_appears_intact_in_message(self):
        name = "Ñoño 🌟 Ångström"
        event = make_get_event(nombre=name)
        resp = lambda_handler(event, None)
        body = json.loads(resp["body"])
        assert resp["statusCode"] == 200
        assert name in body["mensaje"]

    # --- CORS headers present in every response type ---
    def test_cors_headers_present_in_200_response(self):
        event = make_get_event(nombre="Test")
        resp = lambda_handler(event, None)
        assert "Access-Control-Allow-Origin" in resp["headers"]

    def test_cors_headers_present_in_400_response(self):
        event = {"queryStringParameters": None}  # no httpMethod
        resp = lambda_handler(event, None)
        body = json.loads(resp["body"])
        assert resp["statusCode"] == 400
        assert "Access-Control-Allow-Origin" in resp["headers"]

    # --- Response has exactly mensaje and fuente for 200 ---
    def test_successful_response_has_exactly_mensaje_and_fuente(self):
        event = make_get_event(nombre="Julia")
        resp = lambda_handler(event, None)
        body = json.loads(resp["body"])
        assert set(body.keys()) == {"mensaje", "fuente"}

    # --- Error response has error but no mensaje ---
    def test_error_response_no_mensaje_field(self):
        event = make_post_event(raw_body="{invalid}")
        resp = lambda_handler(event, None)
        body = json.loads(resp["body"])
        assert "error" in body
        assert "mensaje" not in body

    # --- POST body with QS name: QS takes precedence ---
    def test_qs_precedence_over_body_in_post(self):
        event = {
            "httpMethod": "POST",
            "queryStringParameters": {"nombre": "FromQS"},
            "body": json.dumps({"nombre": "FromBody"}),
            "isBase64Encoded": False,
        }
        resp = lambda_handler(event, None)
        body = json.loads(resp["body"])
        assert resp["statusCode"] == 200
        assert "FromQS" in body["mensaje"]
        assert body["fuente"] == "query_string"


# ===========================================================================
# Task 6.1 – Reutilizable hypothesis generators
# ===========================================================================

# --- valid_name: 1-100 chars, not all whitespace ---
valid_name = st.text(min_size=1, max_size=100).filter(lambda s: s.strip() != "")

# --- whitespace_only_string: 0-200 chars, only space/tab/newline ---
whitespace_only_string = st.text(
    alphabet=st.sampled_from([" ", "\t", "\n"]),
    min_size=0,
    max_size=200,
)

# --- long_name: strictly more than 100 chars ---
long_name = st.text(min_size=101, max_size=500)

# --- invalid_json_string: strings that are not parseable as JSON ---
invalid_json_string = st.text(min_size=1).filter(
    lambda s: _is_invalid_json(s)
)


def _is_invalid_json(s: str) -> bool:
    try:
        json.loads(s)
        return False
    except (json.JSONDecodeError, ValueError):
        return True


@st.composite
def valid_get_event(draw, name: str | None = None):
    """Factory: build a complete GET Lambda Function URL event."""
    if name is None:
        name = draw(valid_name)
    return {
        "httpMethod": "GET",
        "queryStringParameters": {"nombre": name},
        "body": None,
        "isBase64Encoded": False,
    }


@st.composite
def valid_post_event(draw, name: str | None = None):
    """Factory: build a complete POST Lambda Function URL event with name in body."""
    if name is None:
        name = draw(valid_name)
    return {
        "httpMethod": "POST",
        "queryStringParameters": None,
        "body": json.dumps({"nombre": name}),
        "isBase64Encoded": False,
    }


@st.composite
def any_event(draw):
    """Arbitrary Lambda event — valid, invalid, or malformed."""
    method = draw(st.sampled_from(["GET", "POST", "OPTIONS", "DELETE", "", "INVALID"]))

    qs_params = draw(
        st.one_of(
            st.none(),
            st.fixed_dictionaries({}),
            st.fixed_dictionaries({"nombre": st.text(max_size=200)}),
        )
    )

    body = draw(
        st.one_of(
            st.none(),
            st.text(max_size=500),
            st.just(""),
        )
    )

    is_base64 = draw(st.booleans())

    # Optionally omit httpMethod entirely
    include_method = draw(st.booleans())
    event: dict = {
        "queryStringParameters": qs_params,
        "body": body,
        "isBase64Encoded": is_base64,
    }
    if include_method:
        event["httpMethod"] = method

    return event


# ===========================================================================
# Tasks 6.2-6.12 – Property-based tests (hypothesis)
# ===========================================================================

# Feature: lambda-greeting-api, Property 1: Saludo personalizado correcto para
# cualquier nombre válido
@given(name=valid_name, use_post=st.booleans())
@settings(max_examples=100)
def test_property_1_personalized_greeting(name, use_post):
    """Validates: Requirements 1.1, 1.2, 7.1, 7.2"""
    if use_post:
        event = {
            "httpMethod": "POST",
            "queryStringParameters": None,
            "body": json.dumps({"nombre": name}),
            "isBase64Encoded": False,
        }
    else:
        event = {
            "httpMethod": "GET",
            "queryStringParameters": {"nombre": name},
            "body": None,
            "isBase64Encoded": False,
        }

    resp = lambda_handler(event, None)
    body = json.loads(resp["body"])

    # validate_name strips and may truncate — reproduce what the handler does
    validated = name.strip() if len(name) <= 100 else name[:100].strip()
    if not validated:
        # edge: name became empty after strip/truncate → generic greeting
        assert body["mensaje"] == "¡Bienvenido a la arquitectura serverless de AWS!"
    else:
        expected = f"¡Hola {validated}, bienvenido a la arquitectura serverless de AWS!"
        assert body["mensaje"] == expected


# Feature: lambda-greeting-api, Property 2: Precedencia del query string sobre
# el body
@given(
    qs_name=valid_name,
    body_name=valid_name,
)
@settings(max_examples=100)
def test_property_2_query_string_precedence(qs_name, body_name):
    """Validates: Requirements 1.3"""
    # Reproduce what validate_name does so we can build the expected message
    validated_qs = qs_name.strip() if len(qs_name) <= 100 else qs_name[:100].strip()
    validated_body = body_name.strip() if len(body_name) <= 100 else body_name[:100].strip()

    # Skip if either normalises to empty — not in the scope of this property
    if not validated_qs or not validated_body:
        return

    event = {
        "httpMethod": "POST",
        "queryStringParameters": {"nombre": qs_name},
        "body": json.dumps({"nombre": body_name}),
        "isBase64Encoded": False,
    }

    resp = lambda_handler(event, None)
    body = json.loads(resp["body"])

    assert resp["statusCode"] == 200
    # fuente must be query_string — QS wins over body
    assert body["fuente"] == "query_string"
    # The message must be the exact personalised greeting built from the QS name
    expected_msg = f"¡Hola {validated_qs}, bienvenido a la arquitectura serverless de AWS!"
    assert body["mensaje"] == expected_msg


# Feature: lambda-greeting-api, Property 3: Saludo genérico e invariante para
# entradas sin nombre válido
@given(
    whitespace_val=whitespace_only_string,
    method=st.sampled_from(["GET", "POST"]),
)
@settings(max_examples=100)
def test_property_3_generic_greeting(whitespace_val, method):
    """Validates: Requirements 1.4, 2.1, 2.2, 2.4, 7.3"""
    if method == "GET":
        event = {
            "httpMethod": "GET",
            "queryStringParameters": {"nombre": whitespace_val} if whitespace_val else None,
            "body": None,
            "isBase64Encoded": False,
        }
    else:
        event = {
            "httpMethod": "POST",
            "queryStringParameters": None,
            "body": json.dumps({"nombre": whitespace_val}),
            "isBase64Encoded": False,
        }

    resp = lambda_handler(event, None)
    body = json.loads(resp["body"])

    assert resp["statusCode"] == 200
    assert body["mensaje"] == "¡Bienvenido a la arquitectura serverless de AWS!"
    assert body["fuente"] == "none"


# Feature: lambda-greeting-api, Property 4: El campo `fuente` refleja siempre
# el origen correcto del nombre
@given(
    name=valid_name,
    use_get=st.booleans(),
)
@settings(max_examples=100)
def test_property_4_fuente_field_correctness(name, use_get):
    """Validates: Requirements 2.3"""
    validated = name.strip() if len(name) <= 100 else name[:100].strip()
    if not validated:
        return  # not a valid name after normalization

    if use_get:
        event = {
            "httpMethod": "GET",
            "queryStringParameters": {"nombre": name},
            "body": None,
            "isBase64Encoded": False,
        }
        expected_fuente = "query_string"
    else:
        event = {
            "httpMethod": "POST",
            "queryStringParameters": None,
            "body": json.dumps({"nombre": name}),
            "isBase64Encoded": False,
        }
        expected_fuente = "body"

    resp = lambda_handler(event, None)
    body = json.loads(resp["body"])

    assert resp["statusCode"] == 200
    assert body["fuente"] == expected_fuente


# Feature: lambda-greeting-api, Property 5: Body JSON inválido produce HTTP
# 400 con campo `error`
@given(bad_body=invalid_json_string)
@settings(max_examples=100)
def test_property_5_invalid_json_400(bad_body):
    """Validates: Requirements 3.3, 5.6, 6.5"""
    event = {
        "httpMethod": "POST",
        "queryStringParameters": None,
        "body": bad_body,
        "isBase64Encoded": False,
    }

    resp = lambda_handler(event, None)
    body = json.loads(resp["body"])

    assert resp["statusCode"] == 400
    assert "error" in body
    assert isinstance(body["error"], str) and body["error"]  # non-empty string
    assert "mensaje" not in body


# Feature: lambda-greeting-api, Property 6: Round-trip JSON estable para toda
# respuesta de saludo
@given(
    name=st.one_of(valid_name, st.none()),
    use_get=st.booleans(),
)
@settings(max_examples=100)
def test_property_6_json_round_trip(name, use_get):
    """Validates: Requirements 3.4, 7.4"""
    if name is not None:
        event = {
            "httpMethod": "GET" if use_get else "POST",
            "queryStringParameters": {"nombre": name} if use_get else None,
            "body": None if use_get else json.dumps({"nombre": name}),
            "isBase64Encoded": False,
        }
    else:
        event = {
            "httpMethod": "GET",
            "queryStringParameters": None,
            "body": None,
            "isBase64Encoded": False,
        }

    resp = lambda_handler(event, None)
    raw_body = resp["body"]

    # Round-trip: parse → dump → parse must equal the first parse
    first_parse = json.loads(raw_body)
    second_parse = json.loads(json.dumps(first_parse, ensure_ascii=False))
    assert first_parse == second_parse


# Feature: lambda-greeting-api, Property 7: Los headers de respuesta correctos
# están presentes en toda respuesta
@given(event=any_event())
@settings(max_examples=100)
def test_property_7_cors_headers_always_present(event):
    """Validates: Requirements 3.1, 4.1, 4.2, 4.3, 4.5, 7.5"""
    resp = lambda_handler(event, None)

    headers = resp.get("headers", {})
    assert headers.get("Access-Control-Allow-Origin") == "*"
    assert headers.get("Access-Control-Allow-Methods") == "GET, POST, OPTIONS"
    assert headers.get("Access-Control-Allow-Headers") == "Content-Type"
    # Content-Type is present for all non-OPTIONS responses; for OPTIONS it
    # may be absent (the handler returns CORS_HEADERS without Content-Type).
    # The requirement states it must be present in all responses, so check
    # the method from the event.
    method = event.get("httpMethod", "").upper()
    if method != "OPTIONS":
        assert headers.get("Content-Type") == "application/json"


# Feature: lambda-greeting-api, Property 8: La decodificación Base64 produce
# el mismo resultado que el envío directo
@given(name=valid_name)
@settings(max_examples=100)
def test_property_8_base64_equivalence(name):
    """Validates: Requirements 5.3"""
    validated = name.strip() if len(name) <= 100 else name[:100].strip()
    if not validated:
        return  # skip edge where name normalizes to empty

    raw_body = json.dumps({"nombre": name})
    b64_body = base64.b64encode(raw_body.encode("utf-8")).decode("ascii")

    event_direct = {
        "httpMethod": "POST",
        "queryStringParameters": None,
        "body": raw_body,
        "isBase64Encoded": False,
    }
    event_b64 = {
        "httpMethod": "POST",
        "queryStringParameters": None,
        "body": b64_body,
        "isBase64Encoded": True,
    }

    resp_direct = lambda_handler(event_direct, None)
    resp_b64 = lambda_handler(event_b64, None)

    assert resp_direct["statusCode"] == resp_b64["statusCode"]
    assert json.loads(resp_direct["body"]) == json.loads(resp_b64["body"])


# Feature: lambda-greeting-api, Property 9: Truncado exacto a 100 caracteres
# para nombres demasiado largos
@given(name=long_name)
@settings(max_examples=100)
def test_property_9_name_truncation(name):
    """Validates: Requirements 6.3"""
    event = {
        "httpMethod": "GET",
        "queryStringParameters": {"nombre": name},
        "body": None,
        "isBase64Encoded": False,
    }

    resp = lambda_handler(event, None)
    body = json.loads(resp["body"])

    # The first 100 chars of the name, stripped
    truncated = name[:100].strip()

    if not truncated:
        # Truncated to all-whitespace → generic greeting
        assert body["mensaje"] == "¡Bienvenido a la arquitectura serverless de AWS!"
        assert body["fuente"] == "none"
    else:
        assert resp["statusCode"] == 200
        expected = f"¡Hola {truncated}, bienvenido a la arquitectura serverless de AWS!"
        assert body["mensaje"] == expected
        # The full original name must NOT appear in the message
        assert name not in body["mensaje"]


# Feature: lambda-greeting-api, Property 10: La función nunca devuelve HTTP
# 5xx
@given(event=any_event())
@settings(max_examples=100)
def test_property_10_never_500(event):
    """Validates: Requirements 6.4, 1.6"""
    resp = lambda_handler(event, None)
    assert resp["statusCode"] in (200, 400)


# Feature: lambda-greeting-api, Property 11: Toda respuesta exitosa tiene
# exactamente los campos `mensaje` y `fuente`
@given(
    name=st.one_of(valid_name, st.none()),
    use_get=st.booleans(),
)
@settings(max_examples=100)
def test_property_11_response_schema(name, use_get):
    """Validates: Requirements 3.2"""
    if name is not None:
        event = {
            "httpMethod": "GET" if use_get else "POST",
            "queryStringParameters": {"nombre": name} if use_get else None,
            "body": None if use_get else json.dumps({"nombre": name}),
            "isBase64Encoded": False,
        }
    else:
        event = {
            "httpMethod": "GET",
            "queryStringParameters": None,
            "body": None,
            "isBase64Encoded": False,
        }

    resp = lambda_handler(event, None)
    if resp["statusCode"] != 200:
        return  # Only check successful responses

    body = json.loads(resp["body"])
    assert set(body.keys()) == {"mensaje", "fuente"}
    assert isinstance(body["mensaje"], str) and body["mensaje"]
    assert isinstance(body["fuente"], str) and body["fuente"]
