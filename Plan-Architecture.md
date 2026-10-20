# Plan de arquitectura — autenticación y límites de tareas

## Impacto

El cambio cruza los límites de autenticación, autorización, persistencia de tareas y almacenamiento de archivos. Se concentra en `app/main.py` y las pruebas de `tests/test_api.py`; no requiere por ahora reestructurar el módulo ni migrar el esquema de tareas.

## Componentes afectados

- `legacy_identity`: validación del token compartido con `workshop-auth-backend`.
- Endpoints `list_tasks`, `create_task` y `summary`: identidad autenticada, filtros de propietario y acceso a SQLite.
- `upload_requirement`: nombre, ruta, tamaño de carga y respuesta de almacenamiento.
- `tests/test_api.py`: pruebas de API con base y directorio temporales.

## Contratos protegidos

- Mantener autenticación Bearer para los endpoints protegidos.
- `GET /api/tasks` conserva la respuesta como array de tareas; el frontend continúa enviando `owner`.
- `POST /api/tasks` conserva creación y respuesta de tarea compatible con el cliente actual.
- `GET /api/summary` conserva `owner`, `total`, `byStatus` y `highPriorityOpen`.
- `POST /api/requirements` conserva la carga multipart y la respuesta exitosa con `owner`, `fileName`, `storedAt` y `size`.
- El frontend no es autoridad de autorización: `owner` solo puede servir como filtro conforme a una política aprobada por el servidor.
- Errores de autenticación continúan siendo HTTP no exitosos para que Axios los rechace.

## Estrategia incremental

1. Ampliar pruebas con base temporal para fijar respuestas nominales existentes antes de cambiar validación y acceso.
2. Validar el JWT HS256 emitido por `workshop-auth-backend`, exigiendo `sub`, `client`, `iat` y `exp`, aceptando solo `client=angular-workshop` y rechazando inmediatamente el formato Base64 anterior. `AUTH_TOKEN_SECRET` se requiere en este servicio y en el emisor con el mismo valor y al menos 32 bytes UTF-8.
3. Definir el comportamiento para `owner` distinto del usuario autenticado. Aplicar una única política coherente a listado, resumen y creación; no otorgar acceso delegado implícitamente.
4. Cambiar las consultas dinámicas de tareas para que valores del cliente no alteren la sintaxis o alcance de SQL; preservar campos, filtros y orden actual.
5. Establecer reglas explícitas de nombre y tamaño para carga. Verificar que la ruta final permanezca bajo el directorio autorizado y que una carga rechazada no deje un archivo parcial.
6. Probar los límites por separado y luego ejecutar integración de token válido, login y listado usando el contrato del frontend.

La estrategia JWT, algoritmo, cliente, secreto y transición inmediata del formato anterior están aprobados y deben desplegarse coordinados con el backend emisor. Las decisiones de `owner` y máximo de carga quedan fuera de HU-01 y no bloquean este cambio de token.

## Pruebas necesarias

- Token: válido/vigente aceptado; token alterado, vencido, ausente o malformado rechazado con HTTP no exitoso.
- Propietarios: dos identidades sintéticas; listado y resumen no filtran tareas ajenas y la creación no atribuye tareas a otro usuario sin permiso explícito.
- SQL: valores con caracteres especiales permanecen como datos en listados, creación y resumen, sin afectar otras filas.
- Respuestas: validar forma de la lista, tarea creada y campos del resumen contra los contratos actuales.
- Archivos: carga nominal permitida; nombres que resuelvan fuera de la raíz rechazados; carga mayor al límite acordado rechazada sin archivo parcial; respuesta nominal conserva sus campos.
- Integración: token emitido por el backend permite el flujo legítimo del frontend hacia `GET /api/tasks`.

## Riesgos / trade-offs

- Cambiar simultáneamente formato de token y políticas de autorización puede dificultar aislar regresiones; separar etapas y pruebas reduce ese riesgo.
- Rechazar explícitamente una solicitud para otro `owner` y devolver una lista vacía son comportamientos diferentes; el contrato HTTP debe acordarse.
- El máximo de carga no está fijado; un límite muy bajo puede rechazar documentos válidos y uno alto aumenta consumo de recursos.
- La respuesta incluye `storedAt`; revelar una ruta absoluta puede exponer información del entorno, pero cambiar ese campo puede romper consumidores.
- La API mantiene conexión SQLite global y lógica en un módulo; no se planifica refactor general porque no es necesario para los hallazgos aprobados.
- Los READMEs limitan el uso a local y aislado; no se asume despliegue público.

## Decisiones abiertas

- Respuesta para un `owner` distinto: denegar, limitar a identidad propia o admitir algún permiso delegado explícito.
- Si el campo `owner` del body de creación se ignora, se valida contra la identidad o permite una excepción autorizada.
- Tamaño máximo, nombres/extensiones aceptados y respuesta HTTP al exceder límites de carga.
- Si `storedAt` puede mantenerse como ruta devuelta o debe conservarse semánticamente con una representación no interna.

No se registra ADR en este plan: los contratos de autorización, token y carga requieren decisiones de producto/seguridad aún abiertas.
