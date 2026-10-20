# Autenticación y límites de tareas — API de requisitos

## Fuente

Hallazgos aprobados por el usuario y documentados en `HALLAZGOS.md`:

- La validación del token no verifica integridad criptográfica de las claims (`app/main.py:14,20-24`).
- Falta de vinculación del propietario de tareas con la identidad autenticada (`app/main.py:69-71,83-85,92-94`).
- Consultas SQL interpolan valores recibidos por la API (`app/main.py:70-71,84-85,93`).
- La ruta de carga se forma directamente con el nombre del archivo (`app/main.py:109-111`).

El emisor del token es `workshop-auth-backend`; su evidencia está referenciada en el hallazgo de token y en `../workshop-auth-backend/src/main/java/com/bcp/workshop/auth/LegacyTokenUtil.java:8,14-15`.

## Contexto actual

La API valida el Bearer decodificando Base64, compara un secreto constante y usa las claims resultantes como identidad. Las operaciones de listado y resumen aceptan `owner` en query; la creación permite `owner` en el body. Los filtros y la inserción de tareas construyen SQL concatenando valores del cliente. La carga une el directorio con `file.filename`, lee el contenido completo y lo escribe. El README restringe el servicio a un entorno local aislado.

## Problema confirmado

El servicio no acredita criptográficamente la identidad presentada, y los límites por propietario se basan en valores controlables por el cliente. Además, valores recibidos pueden alterar las consultas SQL, y la ruta/nombre y tamaño de una carga no quedan sujetos a límites explícitos en el comportamiento revisado.

## Comportamiento a preservar

- Mantener los endpoints existentes y el uso de `Authorization: Bearer <token>` para rutas protegidas.
- Mantener `GET /api/tasks` como una lista JSON de tareas, `POST /api/tasks` como creación de tarea, y `GET /api/summary` con sus campos `owner`, `total`, `byStatus` y `highPriorityOpen`.
- Mantener el contrato del frontend: envía `owner` como query al listar y espera un array JSON de tareas en respuesta.
- Mantener `POST /api/requirements` y su respuesta exitosa actual, con `owner`, `fileName`, `storedAt` y `size`.
- Mantener acceso legítimo a las tareas del propietario autenticado y carga legítima de archivos dentro del almacenamiento autorizado.
- Mantener la ejecución local y aislada declarada en el README.

## Alcance

- Aceptar como identidad únicamente tokens cuya integridad y vigencia puedan validarse de manera acordada con el backend emisor.
- Definir cómo se aplica la identidad autenticada a las lecturas de tareas, resumen y creación, incluyendo la relación con el parámetro/campo `owner`.
- Asegurar que los valores del cliente usados en consultas y escrituras no alteren la semántica SQL.
- Definir límites verificables para nombre/ruta y tamaño de archivos cargados, manteniendo el almacenamiento dentro de la ubicación autorizada.

## Fuera de alcance

- Selección del formato, algoritmo o biblioteca concreta de token.
- Nuevos roles o permisos para acceso delegado entre propietarios, salvo decisión explícita posterior.
- Cambios en la interfaz o en el almacenamiento de sesión del frontend.
- Cambios de esquema de tareas o migración de base de datos no exigidos por los criterios acordados.
- Políticas de análisis antivirus, retención, extensiones permitidas o publicación de archivos que no estén definidas aquí.
- Otros hallazgos que no forman parte de los cuatro aprobados.

## Criterios de aceptación

1. Un token válido y vigente emitido por el backend de autenticación permite solicitudes legítimas a los endpoints protegidos.
2. Tokens alterados o expirados son rechazados por los endpoints protegidos con una respuesta de autenticación no exitosa.
3. Con dos identidades de prueba, listado y resumen no revelan tareas de una identidad a la otra.
4. La creación de una tarea no permite atribuirla a otra identidad, salvo que exista una autorización explícita acordada y cubierta por prueba.
5. Valores de query y body con caracteres especiales se tratan como datos: no cambian el conjunto de filas, la estructura de la consulta ni afectan registros ajenos.
6. Los casos válidos de listado, creación y resumen conservan sus formas de respuesta consumidas por el frontend y los clientes actuales.
7. Un nombre de archivo no puede provocar una escritura fuera del directorio de cargas autorizado.
8. Las cargas que excedan el máximo acordado se rechazan; las cargas rechazadas no se reportan como exitosas ni dejan un archivo parcial.
9. Una carga legítima conserva la respuesta exitosa con `owner`, `fileName`, `storedAt` y `size`.
10. Pruebas de integración verifican conjuntamente token emitido/validado y llamadas de tareas desde el contrato del frontend.

## Contratos afectados/protegidos

- Autenticación Bearer compartida con `workshop-auth-backend` para todos los endpoints protegidos.
- `GET /api/tasks`: query `owner`; respuesta en forma de array de tareas compatible con `TasksService` y `readTasks`.
- `POST /api/tasks`: body de creación y respuesta de tarea creada.
- `GET /api/summary`: nombres y tipos de los campos existentes del resumen.
- `POST /api/requirements`: multipart con archivo y respuesta exitosa con `owner`, `fileName`, `storedAt` y `size`.
- Contrato de cliente documentado en `workshop-login-frontend/docs/ENDPOINTS.md`; la API debe hacer cumplir autorización por propietario independientemente del filtro `owner` enviado por el cliente.
- Los códigos de error deben continuar siendo no exitosos para Axios cuando la autenticación falla; el frontend muestra un mensaje genérico ante respuestas HTTP fuera de 2xx.

## Riesgos, supuestos y preguntas abiertas

- Se asume que la identidad incluida en el token es la fuente de autoridad para la propiedad de tareas.
- Debe decidirse si un intento de solicitar otro `owner` se rechaza explícitamente o se limita a datos propios; no se presume autorización administrativa.
- Debe acordarse el límite máximo de carga y el estado HTTP/error cuando el archivo exceda ese límite.
- La respuesta de carga incluye `storedAt`; debe verificarse que el valor devuelto no exponga una ruta interna que el contrato no requiera.
- Se asume que backend emisor y API pueden coordinar el cambio de token sin romper solicitudes legítimas del frontend.
- El README indica uso local aislado; no se presume que el servicio esté destinado a exposición pública.
