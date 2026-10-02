# Implementation Plan: lambda-greeting-api

## Overview

Implementar una AWS Lambda Function en Python 3.13 que expone una API de saludo dinámico accesible directamente a través de una Function URL (sin API Gateway). La función acepta peticiones `GET`, `POST` y `OPTIONS`, extrae un campo `nombre` del query string o del cuerpo JSON, y devuelve un JSON con un saludo personalizado o genérico. Incluye soporte completo de CORS y una suite de tests con `pytest` y `hypothesis`.

---

## Tasks

- [x] 1. Crear la estructura del proyecto y los archivos base
  - Crear el archivo `lambda_function.py` en la raíz del proyecto con las constantes de módulo (`CORS_HEADERS`) y los imports necesarios (`json`, `base64`)
  - Crear el archivo `tests/test_lambda_function.py` vacío con los imports iniciales (`pytest`, `hypothesis`)
  - Crear `requirements-dev.txt` con `pytest`, `pytest-cov` y `hypothesis` fijados a versiones exactas
  - _Requirements: 4.1, 4.2, 4.3_

- [x] 2. Implementar las funciones de validación y extracción de nombre
  - [x] 2.1 Implementar `validate_name(raw: str | None) -> str | None`
    - Si `raw` es `None` → devuelve `None`
    - `raw.strip()` → si vacío devuelve `None`
    - Si `len(raw) > 100` → truncar a primeros 100 caracteres, re-aplicar strip; si queda vacío devuelve `None`
    - Retornar el valor truncado y sin espacios extremos
    - _Requirements: 1.4, 1.5, 6.2, 6.3_

  - [ ]* 2.2 Escribir tests de ejemplo para `validate_name`
    - Caso: `None` → `None`
    - Caso: `""` → `None`
    - Caso: `"   "` → `None`
    - Caso: nombre de exactamente 100 caracteres → devuelve íntegro
    - Caso: nombre de 101 caracteres → devuelve primeros 100
    - Caso: nombre con espacios extremos → devuelve sin espacios extremos
    - _Requirements: 1.4, 1.5, 6.3_

  - [x] 2.3 Implementar `extract_name(event: dict) -> tuple[str | None, str]`
    - Precedencia: query string > body JSON
    - Leer `queryStringParameters` del evento (puede ser `None` o ausente)
    - Si método es `POST` y hay `body`, decodificar Base64 si `isBase64Encoded=true`, luego parsear JSON; lanzar `ValueError` si no es JSON válido
    - Devolver `(nombre_validado, fuente)` donde `fuente ∈ {"query_string", "body", "none"}`
    - _Requirements: 1.1, 1.2, 1.3, 5.1, 5.2, 5.3, 5.4, 5.5, 5.7_

  - [ ]* 2.4 Escribir tests de ejemplo para `extract_name`
    - Caso: GET con `nombre` en QS → `("Ana", "query_string")`
    - Caso: POST con `nombre` en body → `("Ana", "body")`
    - Caso: `nombre` en QS y en body → QS tiene precedencia
    - Caso: sin `nombre` → `(None, "none")`
    - Caso: body Base64 válido → decodifica y extrae nombre
    - Caso: body JSON inválido → lanza `ValueError`
    - Caso: `queryStringParameters` ausente → no lanza excepción
    - Caso: `body` nulo → no lanza excepción
    - _Requirements: 1.3, 5.1, 5.2, 5.3, 5.4, 5.5, 5.6_

- [x] 3. Implementar las funciones de construcción de respuesta
  - [x] 3.1 Implementar `build_greeting(name: str | None, source: str) -> dict`
    - Si `name` es no-None y no vacío: `{"mensaje": "¡Hola {name}, bienvenido a la arquitectura serverless de AWS!", "fuente": source}`
    - Si `name` es `None`: `{"mensaje": "¡Bienvenido a la arquitectura serverless de AWS!", "fuente": "none"}`
    - _Requirements: 1.1, 1.2, 1.4, 2.1, 2.3, 3.2_

  - [ ]* 3.2 Escribir tests de ejemplo para `build_greeting`
    - Caso: nombre válido → mensaje personalizado con nombre incluido
    - Caso: `None` → mensaje genérico con `fuente="none"`
    - Caso: `fuente="query_string"` → campo `fuente` refleja la fuente correcta
    - Caso: `fuente="body"` → campo `fuente` refleja la fuente correcta
    - _Requirements: 2.1, 2.3_

  - [x] 3.3 Implementar `build_response(status_code: int, body: dict) -> dict`
    - Serializar `body` a JSON con `json.dumps(body, ensure_ascii=False)`
    - Retornar `{"statusCode": status_code, "headers": {**CORS_HEADERS, "Content-Type": "application/json"}, "body": <json_string>}`
    - _Requirements: 3.1, 3.4, 4.1, 4.2, 4.3_

  - [ ]* 3.4 Escribir tests de ejemplo para `build_response`
    - Caso: respuesta 200 → `statusCode=200`, headers CORS presentes, `Content-Type: application/json`
    - Caso: respuesta 400 → `statusCode=400`, headers CORS presentes
    - Caso: cuerpo con caracteres Unicode → serializado con `ensure_ascii=False`
    - _Requirements: 3.1, 3.4, 4.5_

- [x] 4. Implementar el handler principal `lambda_handler`
  - [x] 4.1 Implementar `lambda_handler(event: dict, context) -> dict`
    - Extraer `httpMethod` del evento; si ausente → devolver `build_response(400, {"error": "Evento no reconocido"})`
    - Si `OPTIONS` → devolver `{"statusCode": 200, "headers": CORS_HEADERS, "body": ""}`
    - Llamar `extract_name(event)` dentro de un `try/except ValueError` → si `ValueError` → `build_response(400, {"error": f"Request body is not valid JSON: {e}"})`
    - Llamar `build_greeting(name, source)` y `build_response(200, greeting)`
    - Envolver todo en un `try/except Exception` catch-all → `build_response(400, {"error": "Error interno inesperado"})`
    - _Requirements: 1.6, 3.1, 4.4, 5.6, 6.1, 6.4_

  - [ ]* 4.2 Escribir tests de ejemplo para `lambda_handler` (integración end-to-end)
    - Caso: GET con `nombre=Ana` → 200, mensaje personalizado, `fuente="query_string"`
    - Caso: POST con body `{"nombre":"Ana"}` → 200, mensaje personalizado, `fuente="body"`
    - Caso: GET sin `nombre` → 200, mensaje genérico, `fuente="none"`
    - Caso: OPTIONS → 200, body vacío, headers CORS
    - Caso: evento sin `httpMethod` → 400, campo `error="Evento no reconocido"`, sin campo `mensaje`
    - Caso: POST con body JSON inválido → 400, campo `error` presente, sin campo `mensaje`
    - Caso: nombre de exactamente 100 caracteres → 200, saludo personalizado completo
    - Caso: nombre de 101 caracteres → 200, nombre truncado a 100 en `mensaje`
    - Caso: nombre solo espacios en blanco → 200, saludo genérico
    - Caso: nombre con caracteres Unicode fuera ASCII básico → aparece íntegro en `mensaje`
    - _Requirements: 1.1, 1.2, 1.4, 1.5, 1.6, 3.3, 4.4, 6.1, 6.2_

- [x] 5. Checkpoint — Verificar tests de ejemplo
  - Asegurarse de que todos los tests de ejemplo pasan con `pytest tests/ -v`. Preguntar al usuario si hay dudas antes de continuar.

- [x] 6. Escribir los tests de propiedades con `hypothesis`
  - [x] 6.1 Escribir los generadores `hypothesis` reutilizables
    - `valid_name()`: `st.text(min_size=1, max_size=100).filter(lambda s: s.strip() != "")`
    - `whitespace_only_string()`: `st.text(alphabet=st.sampled_from([" ", "\t", "\n"]), min_size=0, max_size=200)`
    - `long_name()`: `st.text(min_size=101, max_size=500)`
    - `invalid_json_string()`: strings que no parseables como JSON
    - `valid_post_event(name)` y `valid_get_event(name)`: factories de eventos Lambda completos
    - `any_event()`: eventos Lambda arbitrarios (válidos o malformados)
    - _Requirements: 7.1, 7.2, 7.3, 7.4, 7.5_

  - [ ]* 6.2 Escribir test de Property 1: saludo personalizado correcto para cualquier nombre válido
    - **Property 1: Saludo personalizado correcto para cualquier nombre válido**
    - Usar `valid_name()` con fuente aleatoria (GET/POST)
    - Verificar que `mensaje == f"¡Hola {nombre}, bienvenido a la arquitectura serverless de AWS!"`
    - `@settings(max_examples=100)`
    - **Validates: Requirements 1.1, 1.2, 7.1, 7.2**

  - [ ]* 6.3 Escribir test de Property 2: precedencia del query string sobre el body
    - **Property 2: Precedencia del query string sobre el body**
    - Usar dos `valid_name()` distintos, uno en QS y otro en body
    - Verificar que `mensaje` contiene `qs_name`, `fuente == "query_string"`, y `body_name` no aparece en `mensaje`
    - `@settings(max_examples=100)`
    - **Validates: Requirements 1.3**

  - [ ]* 6.4 Escribir test de Property 3: saludo genérico para entradas sin nombre válido
    - **Property 3: Saludo genérico e invariante para entradas sin nombre válido**
    - Usar `whitespace_only_string()` y ausencia de nombre
    - Verificar `mensaje == "¡Bienvenido a la arquitectura serverless de AWS!"`, `fuente == "none"`, `statusCode == 200`
    - `@settings(max_examples=100)`
    - **Validates: Requirements 1.4, 2.1, 2.2, 2.4, 7.3**

  - [ ]* 6.5 Escribir test de Property 4: campo `fuente` refleja siempre el origen correcto
    - **Property 4: El campo `fuente` refleja siempre el origen correcto del nombre**
    - Usar `valid_name()` con fuente aleatoria
    - Verificar la correspondencia exacta entre origen real y valor de `fuente`
    - `@settings(max_examples=100)`
    - **Validates: Requirements 2.3**

  - [ ]* 6.6 Escribir test de Property 5: body JSON inválido produce HTTP 400
    - **Property 5: Body JSON inválido produce HTTP 400 con campo `error`**
    - Usar `invalid_json_string()`
    - Verificar `statusCode == 400`, campo `error` presente (string no vacío), campo `mensaje` ausente
    - `@settings(max_examples=100)`
    - **Validates: Requirements 3.3, 5.6, 6.5**

  - [ ]* 6.7 Escribir test de Property 6: round-trip JSON estable
    - **Property 6: Round-trip JSON estable para toda respuesta de saludo**
    - Usar `valid_name()` y ausencia de nombre
    - Verificar `json.loads(response["body"]) == json.loads(response["body"])` (idempotencia)
    - `@settings(max_examples=100)`
    - **Validates: Requirements 3.4, 7.4**

  - [ ]* 6.8 Escribir test de Property 7: headers CORS presentes en toda respuesta
    - **Property 7: Los headers de respuesta correctos están presentes en toda respuesta**
    - Usar `any_event()` (eventos válidos, inválidos y OPTIONS)
    - Verificar que `Content-Type`, `Access-Control-Allow-Origin`, `Access-Control-Allow-Methods` y `Access-Control-Allow-Headers` están presentes
    - `@settings(max_examples=100)`
    - **Validates: Requirements 3.1, 4.1, 4.2, 4.3, 4.5, 7.5**

  - [ ]* 6.9 Escribir test de Property 8: decodificación Base64 produce el mismo resultado
    - **Property 8: La decodificación Base64 produce el mismo resultado que el envío directo**
    - Usar `valid_post_event(valid_name())` y comparar respuesta con body directo vs. body Base64+`isBase64Encoded=true`
    - `@settings(max_examples=100)`
    - **Validates: Requirements 5.3**

  - [ ]* 6.10 Escribir test de Property 9: truncado exacto a 100 caracteres
    - **Property 9: Truncado exacto a 100 caracteres para nombres demasiado largos**
    - Usar `long_name()` (longitud > 100)
    - Verificar que el campo `mensaje` contiene exactamente los primeros 100 caracteres del nombre
    - `@settings(max_examples=100)`
    - **Validates: Requirements 6.3**

  - [ ]* 6.11 Escribir test de Property 10: la función nunca devuelve HTTP 5xx
    - **Property 10: La función nunca devuelve HTTP 5xx**
    - Usar `any_event()` (incluyendo eventos completamente malformados)
    - Verificar `statusCode in (200, 400)`
    - `@settings(max_examples=100)`
    - **Validates: Requirements 6.4, 1.6**

  - [ ]* 6.12 Escribir test de Property 11: toda respuesta exitosa tiene exactamente `mensaje` y `fuente`
    - **Property 11: Toda respuesta exitosa tiene exactamente los campos `mensaje` y `fuente`**
    - Usar `valid_name()` y ausencia de nombre
    - Parsear `response["body"]` y verificar que las claves son exactamente `{"mensaje", "fuente"}`, ambos strings no vacíos
    - `@settings(max_examples=100)`
    - **Validates: Requirements 3.2**

- [x] 7. Checkpoint final — Verificar suite completa
  - Ejecutar `pytest tests/ -v --cov=lambda_function --cov-report=term-missing` y confirmar cobertura de línea ≥ 90 % y de rama ≥ 85 %. Preguntar al usuario si hay dudas antes de entregar.

---

## Notes

- Las tareas marcadas con `*` son opcionales y pueden omitirse para un MVP más rápido
- Cada tarea referencia criterios de aceptación específicos para trazabilidad
- Los checkpoints (tareas 5 y 7) son puntos de validación incremental
- Los tests de propiedades validan invariantes universales; los de ejemplo validan casos concretos y edge cases
- La librería `hypothesis` debe fijarse a una versión exacta en `requirements-dev.txt` para reproducibilidad
- El archivo `lambda_function.py` va en la raíz del proyecto (sin subdirectorio); los tests van en `tests/`
- Comandos de referencia:
  - `pytest tests/ -v` → todos los tests en modo single-run
  - `pytest tests/ -v -k "property"` → solo tests de propiedades
  - `pytest tests/ --cov=lambda_function --cov-report=term-missing` → con cobertura

## Task Dependency Graph

```json
{
  "waves": [
    { "id": 0, "tasks": ["1"] },
    { "id": 1, "tasks": ["2.1", "3.1", "3.3"] },
    { "id": 2, "tasks": ["2.2", "2.3", "3.2", "3.4"] },
    { "id": 3, "tasks": ["2.4", "4.1"] },
    { "id": 4, "tasks": ["4.2", "6.1"] },
    { "id": 5, "tasks": ["6.2", "6.3", "6.4", "6.5", "6.6", "6.7", "6.8", "6.9", "6.10", "6.11", "6.12"] }
  ]
}
```
