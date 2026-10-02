# Serverless Architecture Copilot · AWS Cloud Day (UCATEC Edition)

Proyecto desarrollado para el **AWS Cloud Day UCATEC 2026**, organizado por el **AWS User Group Cochabamba**.

El reto inicial consistía en desarrollar una arquitectura serverless básica que incorporara inferencia de inteligencia artificial. Sin embargo, quise ir un paso más allá de un simple generador de saludos y aprovechar la oportunidad para crear algo más cercano a las necesidades reales de la ingeniería de software.

Así nació el **Copiloto de Arquitectura Serverless**, una herramienta que permite analizar requerimientos técnicos y obtener recomendaciones de arquitectura basadas en el *AWS Well-Architected Framework*. Además, el proyecto incorpora una arquitectura orientada a eventos (*Event-Driven Architecture*), que permite gestionar la persistencia de datos y las notificaciones de forma independiente, sin afectar directamente la respuesta que recibe el usuario.

---

## Diagrama del Flujo de Datos

```text
 [ Cliente Web / SPA ]
          │
          │ 1. Carga inicial (HTML5 / Vanilla JS)
          ▼
   ┌──────────────┐
   │  Amazon S3   │  Hosting Estático (reto-aws-ucatec-jherson)
   └──────────────┘
          │
          │ 2. Request HTTP GET con query parameters (CORS habilitado)
          ▼
   ┌──────────────┐
   │  AWS Lambda  │  Backend API (Python 3.13 / Function URL)
   └──────┬───────┘
          │
          ├──────────────────────────────────────────┐
          │ 3. Converse API (Inferencia LLM)         │ 4. PutItem (Escritura NoSQL)
          ▼                                          ▼
   ┌──────────────┐                          ┌──────────────┐
   │Amazon Bedrock│                          │Amazon DynamoDB│
   │ (Nova Micro) │                          │(Historial)   │
   └──────────────┘                          └──────┬───────┘
                                                    │
                                                    │ 5. Change Data Capture (CDC)
                                                    ▼
                                             ┌──────────────┐
                                             │ DynamoDB     │
                                             │ Streams      │
                                             └──────┬───────┘
                                                    │
                                                    │ 6. Disparo asíncrono
                                                    ▼
                                             ┌──────────────┐
                                             │  AWS Lambda  │
                                             │(Worker Async)│
                                             └──────┬───────┘
                                                    │
                                                    │ 7. Notificación Push
                                                    ▼
                                             ┌──────────────┐
                                             │  Amazon SNS  │  Alerta por correo
                                             └──────────────┘
```

## Implementación por Niveles

### 1. Seguridad Operativa y Gestión de Costos (Nivel 0)

Desde el inicio, tuve en cuenta la seguridad y el control de gastos, ya que trabajar con servicios en la nube requiere prestar atención tanto a los permisos como al consumo de recursos.

* Protección de la cuenta root mediante la autenticación multifactor (MFA).
* Creación de un usuario IAM para las tareas diarias, aplicando el principio de menor privilegio necesario para limitar los permisos de acceso.
* Configuración de un presupuesto de contingencia mediante **AWS Budgets**, con un límite de **$1.00 USD** y alertas por correo electrónico en la región `us-east-1`, para llevar un control del gasto durante el desarrollo.

### 2. Frontend Desacoplado en S3 (Nivel 1)

Para la interfaz decidí utilizar **Amazon S3**, aprovechando su capacidad para alojar sitios web estáticos y mantener el frontend independiente del backend.

* Configuración de un bucket S3 destinado exclusivamente a *Static Website Hosting*.
* Desarrollo de una interfaz enfocada en facilitar la interacción con el usuario, incorporando selectores con casos de uso reales, como APIs transaccionales, picos de tráfico en e-commerce y migraciones a bases de datos NoSQL.
* Implementación del cálculo de latencia de red desde el cliente, junto con la visualización del ID de auditoría generado por la base de datos, para que el usuario pueda identificar y consultar cada solicitud realizada.

### 3. Backend Serverless y Spec-Driven Development con Kiro (Niveles 2 y 3)

El backend se desarrolló utilizando **AWS Lambda** con Python 3.13, buscando mantener una arquitectura sencilla, escalable y sin necesidad de administrar servidores.

* Implementación de la API principal mediante **AWS Lambda**, expuesta directamente a través de **Lambda Function URL**, con soporte nativo para CORS, evitando problemas relacionados con las solicitudes *preflight* del navegador.
* Uso de la metodología **Spec-Driven Development** con **Kiro IDE**, organizando el desarrollo en tres etapas: definición de requisitos (`requirements.md`), diseño de la solución (`design.md`) y planificación de tareas (`tasks.md`). Esto permitió establecer una guía clara antes de comenzar con la implementación.
* Desarrollo de una suite de **65 pruebas unitarias**, todas superadas, con una cobertura de código del **93%**. Estas pruebas permiten verificar la correcta sanitización de cadenas de texto y el comportamiento del sistema ante excepciones no controladas.

### 4. Inferencia con Modelos Fundacionales en Amazon Bedrock (Niveles 4 y 5)

Para incorporar inteligencia artificial al proyecto, utilicé **Amazon Bedrock**, que permite integrar modelos fundacionales sin tener que gestionar directamente su infraestructura.

* Integración de **Amazon Nova Micro** mediante la Converse API de Amazon Bedrock, encargada de procesar los requerimientos técnicos enviados por el usuario.
* Configuración de *system prompts* orientados a que el modelo actúe como un arquitecto de soluciones de AWS, proporcionando respuestas estructuradas y centradas en tres aspectos principales:

  * Los servicios serverless más adecuados para el caso planteado.
  * El pilar correspondiente del *AWS Well-Architected Framework*.
  * Las ventajas de utilizar el patrón de arquitectura recomendado.

De esta manera, el modelo no se limita a generar respuestas generales, sino que ofrece recomendaciones técnicas relacionadas con el escenario que se le presenta.

### 5. Persistencia NoSQL y Arquitectura Orientada a Eventos (Nivel "La Yapa")

Como parte adicional del proyecto, incorporé un sistema de persistencia y notificaciones asíncronas. El objetivo es registrar las consultas y gestionar las alertas sin añadir trabajo innecesario al proceso principal de respuesta.

* **Amazon DynamoDB:** Cada consulta realizada se almacena en la tabla `HistorialConsultas`, utilizando una clave primaria UUIDv4. También se registra la fecha y hora en UTC, los datos de entrada (*payload*) y el diagnóstico generado por el modelo.
* **DynamoDB Streams + Lambda Worker:** Para mantener desacopladas las tareas secundarias, habilité DynamoDB Streams en la tabla, utilizando la captura de eventos `NewImage`. De esta manera, los cambios registrados en la base de datos pueden activar procesos adicionales sin interferir directamente con la respuesta de la API.
* **Amazon SNS:** Desarrollé un worker asíncrono en AWS Lambda, denominado `notificador-worker`, que consume los eventos del stream y publica una notificación de auditoría mediante Amazon SNS. Esta alerta llega a mi correo personal en cuestión de milisegundos, permitiendo recibir información sobre las consultas procesadas.

Esta implementación permite separar el procesamiento principal de las tareas de auditoría y notificación, aprovechando las ventajas de una arquitectura orientada a eventos.

## Stack Tecnológico

Las tecnologías y herramientas utilizadas para desarrollar el proyecto fueron las siguientes:

* **Cloud Provider:** Amazon Web Services (AWS) — Región `us-east-1` (N. Virginia).
* **Compute:** AWS Lambda (Python 3.13).
* **Storage & NoSQL:** Amazon S3, Amazon DynamoDB.
* **IA Generativa:** Amazon Bedrock (Amazon Nova Micro).
* **Integración Asíncrona:** DynamoDB Streams, Amazon SNS.
* **Herramientas de Desarrollo:** Kiro IDE, Boto3 SDK, Git.

## Repositorio y Demo

* **Frontend desplegado:** [Enlace a mi sitio desarrollado en S3](http://reto-aws-ucatec-jherson.s3-website-us-east-1.amazonaws.com)
* **Desarrollador:** Jherson Rivera Rojas (Estudiante de Ingeniería de Sistemas).
* **Comunidad:** AWS User Group Cochabamba / Universidad Privada UCATEC.
