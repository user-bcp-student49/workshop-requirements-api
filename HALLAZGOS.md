# Hallazgos

| id | hallazgo | tipo | explicacion | evidencia (archivo:linea) | severidad | estado |
|---|---|---|---|---|---|---|
| H-01 | Token Base64 con secreto embebido y sin firma | Vulnerabilidad | El secreto está en el código y el token solo se decodifica y compara; quien conozca ese valor puede fabricar identidades y no hay verificación criptográfica de firma, emisor o audiencia. | `app/main.py:14`, `app/main.py:17-26` | alta | Pendiente |
| H-02 | SQL concatenado en filtros e inserción | Vulnerabilidad | Los valores de `owner` y los campos de tarea se incorporan directamente al SQL; entradas manipuladas pueden cambiar la consulta o escritura y afectar datos de SQLite. | `app/main.py:67-72`, `app/main.py:77-87`, `app/main.py:90-94` | alta | Pendiente |
| H-03 | Nombre de archivo recibido se usa directamente al guardar | Vulnerabilidad | El nombre del cliente se une al directorio destino sin normalización ni límites de extensión/tamaño; nombres de ruta pueden escapar del directorio previsto y archivos grandes pueden consumir memoria o disco. | `app/main.py:107-112` | alta | Pendiente |
| H-04 | El cliente puede consultar tareas de otro `owner` | Vulnerabilidad | `owner` se acepta desde la query y reemplaza la identidad autenticada en listado y resumen, permitiendo consultar datos de otro propietario. | `app/main.py:68-71`, `app/main.py:91-94` | media | Pendiente |
| H-05 | Dependencias objetivo del análisis SCA fijadas en las versiones señaladas por el reto | Vulnerabilidad | El proyecto fija `urllib3 2.5.0` y `python-multipart 0.0.21`, los objetivos SCA indicados en RETO.md. El pin por sí solo no confirma un CVE concreto; queda pendiente validar advisories y versiones corregidas con el análisis SCA. | `requirements.txt:4-5` | media | Pendiente |
| H-06 | Rutas, persistencia, reglas y serialización concentradas en un módulo | Refactor | `create_app` inicializa SQLite y define serialización, rutas, consultas y escritura de archivos dentro de `app/main.py`; los cambios cruzados elevan el acoplamiento y hacen más difícil probar cada responsabilidad. | `app/main.py:29-127` | media | Pendiente |
| H-07 | Tipado débil, excepciones amplias y condicionales anidados | Refactor | Se usan `dict[str, Any]` en payloads/respuestas, se capturan excepciones genéricas y `summary` anida condiciones; esto reduce la validación estática y puede ocultar errores o dificultar el mantenimiento. No registro duplicación como hallazgo porque no encontré evidencia inequívoca en el código revisado. | `app/main.py:17-26`, `app/main.py:56-65`, `app/main.py:78`, `app/main.py:90-105`, `app/main.py:120-121` | baja | Pendiente |

## Análisis discovery — 2026-10-20

Proyecto: `workshop-requirements-api`. Alcance: autenticación Bearer, tareas, resumen y carga de requerimientos. Los registros anteriores se conservan como historial; los candidatos de esta ejecución son:

### La validación del token no verifica integridad criptográfica de las claims
- Estado: CANDIDATO
- Evidencia: `app/main.py:14,20-24` compara un secreto constante y decodifica el contenido Base64 para usar las claims; no verifica firma, emisor o audiencia. El token emitido por el backend está codificado en Base64 en `../workshop-auth-backend/src/main/java/com/bcp/workshop/auth/LegacyTokenUtil.java:8,14-15`.
- Impacto: los endpoints protegidos pueden aceptar claims de identidad que no tienen una firma verificable; esto debilita el límite de autenticación entre ambos servicios.
- Prioridad propuesta: P1 (alta antes de cualquier uso fuera del entorno local aislado declarado por los proyectos).
- Contrato potencialmente afectado: autenticación Bearer de todos los endpoints `/api/*`.
- Cómo validarlo: añadir pruebas de integración con tokens de prueba modificados y expirados, verificando que se rechazan y que solo se acepta un token emitido y validado mediante un mecanismo de integridad acordado por ambos servicios.

### Falta de vinculación del propietario de tareas con la identidad autenticada
- Estado: CANDIDATO
- Evidencia: `app/main.py:69-71` permite que el parámetro `owner` determine el propietario consultado en el listado; `app/main.py:83-85` permite definir el propietario de una tarea creada; el resumen repite el filtro suministrado en `app/main.py:92-94`. Las pruebas actuales validan operaciones nominales con el usuario predeterminado en `tests/test_api.py:27-38`.
- Impacto: una identidad autenticada podría acceder a datos asociados a otro propietario o crear registros atribuidos a él, rompiendo el aislamiento entre usuarios.
- Prioridad propuesta: P1 (alta si la API procesa más de una identidad).
- Contrato potencialmente afectado: `GET /api/tasks`, `POST /api/tasks` y `GET /api/summary`; definición de propiedad de tareas por identidad.
- Cómo validarlo: con dos identidades sintéticas, verificar que cada una solo obtiene registros propios y que el servidor deriva la propiedad de escritura de la identidad autenticada, salvo autorización explícita.

### Consultas SQL interpolan valores recibidos por la API
- Estado: CANDIDATO
- Evidencia: `app/main.py:70-71` construye el filtro del listado con concatenación; `app/main.py:84-85` concatena campos de la tarea al `INSERT`; `app/main.py:93` concatena el filtro del resumen. `tests/test_api.py:19-58` cubre operaciones nominales y token inválido, no el tratamiento literal de valores especiales.
- Impacto: datos proporcionados por el cliente pueden cambiar la semántica de consultas o escrituras y afectar la confidencialidad o integridad de la base de datos.
- Prioridad propuesta: P1 (alta si se aceptan solicitudes de usuarios no confiables).
- Contrato potencialmente afectado: filtros y escritura de `GET /api/tasks`, `POST /api/tasks` y `GET /api/summary`.
- Cómo validarlo: probar entradas con caracteres especiales y verificar que se almacenan y comparan como valores, sin alterar el conjunto de filas ni la estructura de las consultas; exigir consultas parametrizadas.

### La ruta de carga se forma directamente con el nombre del archivo
- Estado: CANDIDATO
- Evidencia: `app/main.py:109-111` combina el directorio de cargas con `file.filename`, lee el archivo completo y escribe los bytes sin comprobar que la ruta resuelta permanezca dentro del directorio ni establecer un límite de tamaño. `tests/test_api.py:41-51` solo verifica una carga nominal.
- Impacto: según el nombre recibido y el sistema operativo, una ruta puede salir del directorio previsto; una carga grande también puede consumir memoria o disco.
- Prioridad propuesta: P2 (media-alta; depende de permisos del proceso y exposición del servicio).
- Contrato potencialmente afectado: `POST /api/requirements`, ubicación y límites de almacenamiento de archivos.
- Cómo validarlo: con un directorio temporal, probar nombres de archivo no válidos y archivos que excedan el límite definido; confirmar rechazo y que ningún archivo se escribe fuera de la raíz de cargas.