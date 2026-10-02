# Requirements Document

## Introduction

Esta feature evoluciona una función AWS Lambda en Python 3.13 con Function URL de devolver un mensaje estático a una API de saludo dinámica. La API extrae un nombre del query string o del cuerpo JSON de la petición, devuelve un saludo personalizado cuando el nombre está presente y un saludo genérico cuando no lo está. Se habilita CORS para permitir la invocación desde una landing page alojada en Amazon S3.

## Glossary

- **Lambda_Function**: La función AWS Lambda en Python 3.13 expuesta mediante una Function URL.
- **Function_URL**: El endpoint HTTPS generado por AWS Lambda que acepta peticiones HTTP directamente sin pasar por API Gateway.
- **Query_String**: Los parámetros que viajan en la URL después del símbolo `?` (p. ej. `?nombre=Ana`).
- **Request_Body**: El cuerpo de la petición HTTP en formato JSON que puede contener el campo `nombre`.
- **Greeting_Response**: El objeto JSON que devuelve la Lambda_Function con el mensaje de saludo.
- **Generic_Greeting**: El mensaje de saludo devuelto cuando no se proporciona ningún nombre: `"¡Bienvenido a la arquitectura serverless de AWS!"`.
- **Personalized_Greeting**: El mensaje de saludo devuelto cuando se proporciona un nombre: `"¡Hola {nombre}, bienvenido a la arquitectura serverless de AWS!"`.
- **CORS_Headers**: Los encabezados HTTP (`Access-Control-Allow-Origin`, `Access-Control-Allow-Methods`, `Access-Control-Allow-Headers`) requeridos para permitir peticiones cross-origin desde una página alojada en S3.
- **Preflight_Request**: Petición HTTP con método `OPTIONS` enviada por el navegador antes de una petición cross-origin para verificar los permisos CORS.
- **S3_Landing_Page**: Una página web estática alojada en un bucket de Amazon S3 que invoca la Function_URL desde el navegador del usuario.
- **nombre_Field**: El campo de texto libre que identifica al usuario; puede llegar via Query_String o Request_Body.

---

## Requirements

### Requirement 1: Saludo personalizado por nombre

**User Story:** Como usuario de la S3_Landing_Page, quiero enviar mi nombre a la API para que me devuelva un saludo personalizado, y así sentir que la experiencia es relevante para mí.

#### Acceptance Criteria

1. WHEN una petición HTTP `GET` llega a la Lambda_Function con el parámetro `nombre` en el Query_String cuya longitud sea de 1 a 100 caracteres no en blanco, THE Lambda_Function SHALL incluir en la Greeting_Response el campo `mensaje` con el valor `"¡Hola {nombre}, bienvenido a la arquitectura serverless de AWS!"` donde `{nombre}` es el valor recibido.
2. WHEN una petición HTTP `POST` llega a la Lambda_Function con un Request_Body JSON que contiene el campo `nombre` cuya longitud sea de 1 a 100 caracteres no en blanco, THE Lambda_Function SHALL incluir en la Greeting_Response el campo `mensaje` con el valor `"¡Hola {nombre}, bienvenido a la arquitectura serverless de AWS!"` donde `{nombre}` es el valor del campo nombre_Field del Request_Body.
3. WHEN el parámetro `nombre` aparece tanto en el Query_String como en el Request_Body, THE Lambda_Function SHALL dar precedencia al valor del Query_String para construir la Greeting_Response.
4. WHEN el nombre_Field está ausente, es una cadena vacía, o contiene únicamente espacios en blanco, THE Lambda_Function SHALL devolver la Generic_Greeting `"¡Bienvenido a la arquitectura serverless de AWS!"` con código de estado HTTP `200`.
5. WHEN el nombre_Field tiene una longitud superior a 100 caracteres, THE Lambda_Function SHALL devolver la Generic_Greeting con código de estado HTTP `200` tratándolo como nombre ausente.
6. THE Lambda_Function SHALL devolver la Greeting_Response con código de estado HTTP `200` en respuestas de saludo personalizadas y genéricas.

---

### Requirement 2: Saludo genérico cuando no se provee nombre

**User Story:** Como usuario de la S3_Landing_Page, quiero que la API me devuelva un saludo de bienvenida aunque no proporcione mi nombre, para que siempre reciba una respuesta útil.

#### Acceptance Criteria

1. WHEN una petición llega a la Lambda_Function sin el parámetro `nombre` en el Query_String ni en el Request_Body, THE Lambda_Function SHALL incluir en la Greeting_Response el campo `mensaje` con el valor `"¡Bienvenido a la arquitectura serverless de AWS!"` y el campo `fuente` con el valor `"none"`.
2. IF una petición llega a la Lambda_Function con el parámetro `nombre` con valor vacío `""`, THEN THE Lambda_Function SHALL devolver la Generic_Greeting `"¡Bienvenido a la arquitectura serverless de AWS!"` con código de estado HTTP `200` y el campo `fuente` con el valor `"none"`.
3. THE Lambda_Function SHALL incluir en toda Greeting_Response el campo `fuente` con el valor `"query_string"` cuando el nombre se extrajo del Query_String, `"body"` cuando se extrajo del Request_Body, o `"none"` cuando no se proporcionó nombre válido (incluyendo cadena vacía y valor solo con espacios en blanco).
4. WHEN el nombre_Field contiene únicamente caracteres de espacio en blanco, THE Lambda_Function SHALL tratar ese valor como nombre ausente, devolviendo la Generic_Greeting `"¡Bienvenido a la arquitectura serverless de AWS!"` con código de estado HTTP `200` y el campo `fuente` con valor `"none"`.

---

### Requirement 3: Formato y estructura de la respuesta

**User Story:** Como desarrollador de la S3_Landing_Page, quiero que la respuesta de la API tenga siempre el mismo esquema JSON, para que mi código de frontend pueda parsearlo de forma predecible.

#### Acceptance Criteria

1. THE Lambda_Function SHALL devolver la Greeting_Response con el encabezado `Content-Type: application/json` sin parámetros adicionales distintos a ese valor.
2. THE Lambda_Function SHALL devolver una Greeting_Response que sea un objeto JSON válido con exactamente los campos `mensaje` (string no vacío, máximo 500 caracteres) y `fuente` (string no vacío, máximo 100 caracteres), sin campos adicionales.
3. IF el Request_Body de una petición `POST` no es JSON válido, THEN THE Lambda_Function SHALL devolver una respuesta con código de estado HTTP `400` que contenga exactamente el campo `error` (string no vacío describiendo el problema) y no contenga el campo `mensaje`.
4. THE Lambda_Function SHALL serializar toda Greeting_Response de forma que `json.loads(json.dumps(response)) == response` para toda respuesta generada (propiedad de round-trip JSON).

---

### Requirement 4: Soporte CORS para S3_Landing_Page

**User Story:** Como desarrollador de la S3_Landing_Page, quiero que la Lambda_Function responda con los CORS_Headers correctos, para que el navegador permita las peticiones cross-origin desde mi dominio S3.

#### Acceptance Criteria

1. THE Lambda_Function SHALL incluir en toda respuesta el CORS_Header `Access-Control-Allow-Origin` con el valor `"*"`.
2. THE Lambda_Function SHALL incluir en toda respuesta el CORS_Header `Access-Control-Allow-Methods` con el valor exacto `"GET, POST, OPTIONS"`.
3. THE Lambda_Function SHALL incluir en toda respuesta el CORS_Header `Access-Control-Allow-Headers` con el valor exacto `"Content-Type"`.
4. WHEN una Preflight_Request con método `OPTIONS` llega a la Lambda_Function, THE Lambda_Function SHALL responder con código de estado HTTP `200`, los CORS_Headers definidos en los criterios 1 al 3, y un cuerpo de respuesta vacío sin ningún campo.
5. THE Lambda_Function SHALL incluir los CORS_Headers definidos en los criterios 1 al 3 en toda respuesta, incluyendo las respuestas con código de estado HTTP 4xx o 5xx.

---

### Requirement 5: Compatibilidad con el evento de AWS Lambda Function URL

**User Story:** Como operador de la infraestructura AWS, quiero que la Lambda_Function interprete correctamente el payload del evento generado por la Function URL, para que funcione sin API Gateway.

#### Acceptance Criteria

1. IF el método HTTP de la petición es `GET`, THEN THE Lambda_Function SHALL leer el nombre_Field del campo `queryStringParameters` del evento Lambda.
2. WHEN el método HTTP es `POST` y el campo `body` del evento Lambda no es nulo, THE Lambda_Function SHALL parsear el campo `body` como JSON para extraer el nombre_Field.
3. WHEN el campo `isBase64Encoded` del evento Lambda es `true`, THE Lambda_Function SHALL decodificar el campo `body` en Base64 antes de parsearlo como JSON.
4. IF el campo `queryStringParameters` del evento Lambda es nulo o ausente, THEN THE Lambda_Function SHALL tratar el Query_String como vacío sin lanzar una excepción.
5. IF el campo `body` del evento Lambda es nulo, THEN THE Lambda_Function SHALL tratar el Request_Body como una cadena vacía sin lanzar una excepción.
6. IF el campo `body` del evento Lambda contiene un valor que no puede ser parseado como JSON válido, THEN THE Lambda_Function SHALL devolver una respuesta con código de estado HTTP `400` con el campo `error` describiendo el problema, sin propagar la excepción.
7. IF el nombre_Field está ausente en el Query_String y en el Request_Body, THEN THE Lambda_Function SHALL devolver la Generic_Greeting con `fuente: "none"`.

---

### Requirement 6: Robustez ante entradas inesperadas

**User Story:** Como operador de la infraestructura AWS, quiero que la Lambda_Function maneje entradas malformadas sin fallar, para evitar errores 5xx que afecten la disponibilidad.

#### Acceptance Criteria

1. IF el evento recibido por la Lambda_Function no contiene el campo `httpMethod`, THEN THE Lambda_Function SHALL devolver una respuesta con código de estado HTTP `400` y el campo `error` con el valor `"Evento no reconocido"`.
2. WHEN el nombre_Field contiene uno o más caracteres especiales (incluyendo comillas simples o dobles, ángulos `<` `>`, ampersands `&`, o puntos de código Unicode fuera del rango U+0020–U+007E), THE Lambda_Function SHALL incluir el nombre_Field en la Greeting_Response sin modificar, omitir ni sustituir ninguno de dichos caracteres.
3. WHEN el nombre_Field tiene una longitud superior a 100 caracteres, THE Lambda_Function SHALL truncar el nombre_Field a exactamente los primeros 100 caracteres antes de construir la Greeting_Response, descartando todos los caracteres desde la posición 101 en adelante.
4. THE Lambda_Function SHALL devolver siempre una respuesta con código de estado HTTP `200` o `400`; nunca SHALL propagar una excepción no controlada que provoque un código de estado `500` devuelto por AWS Lambda.
5. IF el cuerpo del evento no puede ser interpretado como un objeto con el campo `nombre_Field` válido (incluyendo cuerpo ausente, nulo, o con formato inválido), THEN THE Lambda_Function SHALL devolver una respuesta con código de estado HTTP `400` y un campo `error` indicando que el cuerpo de la solicitud es inválido, sin propagar la excepción.

---

### Requirement 7: Propiedades de corrección del saludo

**User Story:** Como ingeniero de calidad, quiero que el comportamiento de la API sea verificable mediante propiedades formales, para detectar regresiones en pruebas automatizadas.

#### Acceptance Criteria

1. THE Lambda_Function SHALL producir una Greeting_Response cuyo campo `mensaje` contiene la subcadena del nombre_Field para todo nombre_Field de longitud 1 a 100 caracteres no en blanco (propiedad de invariante: el nombre enviado siempre aparece en la respuesta).
2. THE Lambda_Function SHALL producir una Greeting_Response cuyo campo `mensaje` comienza exactamente con `"¡Hola "` seguida del nombre_Field para todo nombre_Field de longitud 1 a 100 caracteres no en blanco (propiedad metamórfica: el prefijo del saludo personalizado es constante).
3. IF una petición no incluye nombre_Field o lo incluye como cadena vacía o solo con espacios en blanco, THEN THE Lambda_Function SHALL devolver siempre el campo `mensaje` con el valor exacto `"¡Bienvenido a la arquitectura serverless de AWS!"` (propiedad de idempotencia del saludo genérico).
4. THE Lambda_Function SHALL serializar toda Greeting_Response de forma que el campo `mensaje` sea una cadena UTF-8 válida sin caracteres de control no escapados, y que su serialización y deserialización JSON produzca el mismo valor (round-trip estable).
5. THE Lambda_Function SHALL incluir el CORS_Header `Access-Control-Allow-Origin` en toda respuesta, independientemente del contenido del nombre_Field (propiedad de invariante: CORS siempre presente).
