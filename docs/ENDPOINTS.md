# Contrato de endpoints

Este documento describe el comportamiento implementado actualmente en `app/main.py`; no modifica ni propone cambios al contrato.

## Autenticación

Todos los endpoints requieren `Authorization: Bearer <token>`. El token actual es una cadena Base64 que contiene `username|role|expiry_epoch|secret`. La API comprueba que haya cuatro partes, que el secreto coincida con la constante embebida y que la expiración no haya pasado. No comprueba firma, emisor ni audiencia. Un token rechazado produce HTTP 401 con un objeto `detail`.

## Endpoints

### `GET /api/tasks`

- Query opcional: `owner`. Si se omite o está vacío, se usa el `username` del token.
- Respuesta HTTP 200: lista de tareas ordenada por `id` ascendente.
- Cada tarea tiene `id`, `title`, `description`, `status`, `owner`, `priority` y `createdAt`.

### `POST /api/tasks`

- Body JSON requerido. Campos leídos: `title` (por defecto `""`), `description` (por defecto `""`), `status` (por defecto `"TODO"`), `priority` (por defecto `"MEDIUM"`) y `owner` (por defecto el `username` del token). Los valores se convierten a texto.
- Respuesta HTTP 201: una tarea con los mismos campos de salida que `GET /api/tasks`.

### `GET /api/summary`

- Query opcional: `owner`. Si se omite o está vacío, se usa el `username` del token.
- Respuesta HTTP 200: objeto con `owner`, `total`, `byStatus` (mapa de estado a cantidad) y `highPriorityOpen` (tareas `HIGH` cuyo estado no es `DONE` ni `ARCHIVED`).

### `POST /api/requirements`

- Body `multipart/form-data` con el campo requerido `file`.
- Respuesta HTTP 201: objeto con `owner`, `fileName`, `storedAt` y `size` en bytes.
- Actualmente el archivo se guarda en el directorio configurado usando el nombre recibido, sin validaciones adicionales.

### `GET /api/backend-health`

- Consulta el backend de autenticación usando `AUTH_HEALTH_URL`, cuyo valor predeterminado es `http://localhost:8080/q/health`.
- Respuesta HTTP 200: objeto con `requestedBy`, `status` y `body`. Si ocurre una excepción en la consulta, `status` vale `0` y `body` contiene el texto de la excepción.

## Persistencia y configuración

La ruta SQLite se configura con `WORKSHOP_DB_PATH` (predeterminado `./data/workshop.db`) y el directorio de archivos con `WORKSHOP_UPLOAD_DIR` (predeterminado `./uploads`). `create_app` crea la tabla `tasks` y, si está vacía, inserta tres tareas iniciales. Las rutas consultan y modifican la misma conexión SQLite creada durante la inicialización; se cierra al apagar la aplicación.