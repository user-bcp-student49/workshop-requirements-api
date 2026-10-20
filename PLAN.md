# Plan de correccion

## Seleccion

Se selecciona **H-02**, que existe en `HALLAZGOS.md`, sigue `Pendiente` y tiene severidad alta. La concatenacion SQL puede afectar tanto lecturas como inserciones, y es corregible sin cambiar rutas, formatos de respuesta ni la semantica documentada de los endpoints.

**H-04 no se incluye en esta propuesta.** `GOOD_PRACTICES.md` exige que las consultas se limiten a `identity["username"]`, mientras que `docs/ENDPOINTS.md` especifica que el query opcional `owner` determina el propietario consultado. Hacer que prevalezca siempre la identidad cambiaria el contrato descrito. H-04 queda pendiente de una decision explicita sobre ese contrato; este plan no propone modificarlo.

## H-02 — SQL concatenado en filtros e insercion

**Hallazgo de `HALLAZGOS.md`:** valores de `owner` y campos de tarea se concatenan en consultas SQL (`app/main.py`, listado, creacion y resumen).

**Problema:** una comilla en datos validos puede romper la consulta; valores manipulados pueden alterar su significado. El SQL tambien esta dentro de las rutas, mezclando transporte, reglas y persistencia.

**Cambio propuesto:**

1. Antes de modificar codigo de produccion, ampliar `tests/test_api.py` con pruebas de caracterizacion de los contratos actuales: codigos HTTP, campos y nombres de respuesta, orden de listado, valores predeterminados, seleccion de `owner` por query y agregaciones del resumen.
2. Anadir pruebas de regresion observables que creen y consulten tareas con texto que incluya apostrofes en `title`, `description` y `owner`. Deben comprobar que los valores se guardan como datos literales, que las respuestas conservan su forma y que listado/resumen solo devuelven el propietario literal solicitado. Las pruebas deben ejecutarse antes del cambio de implementacion para registrar el comportamiento inicial.
3. Mantener las rutas FastAPI como adaptadores, trasladar las reglas de seleccion de propietario y construccion del resumen a un servicio, y concentrar las operaciones SQLite en un repositorio. En el repositorio, usar placeholders y parametros de `sqlite3` para filtros e inserciones; tambien enlazar como parametro el identificador de la fila creada al leerla de vuelta. No interpolar valores de entrada en SQL.
4. Conservar literalmente los endpoints, codigos y esquemas de respuesta de `docs/ENDPOINTS.md`, incluidos `createdAt`, los valores predeterminados y el significado actual del query `owner`. No agregar dependencias: `sqlite3` es suficiente.

**Archivos a tocar:**

- `tests/test_api.py`: agregar primero caracterizacion del contrato y regresiones de datos con apostrofes.
- `app/main.py`: delegar las rutas de tareas al servicio, preservando sus parametros y respuestas.
- `app/services/__init__.py` y `app/services/tasks.py`: nuevo servicio para reglas de tareas y resumen.
- `app/repositories/__init__.py` y `app/repositories/tasks.py`: nuevo repositorio con consultas SQLite parametrizadas.

**Prueba de caracterizacion previa:** ampliar las pruebas existentes `test_lists_seeded_tasks` y `test_creates_task_and_summary` para afirmar el contrato documentado, y agregar cobertura para `GET /api/tasks?owner=...` y `GET /api/summary?owner=...`. Luego agregar pruebas de regresion con apostrofes en campos de creacion y en el filtro `owner`. Ejecutar `pytest` antes de cambiar `app/main.py`; mantener las pruebas de contrato verdes y confirmar que las nuevas regresiones detectan el fallo inicial. Tras la implementacion, volver a ejecutar la suite completa y comprobar que el contrato sigue intacto.

**Clean Code:** funciones pequenas con responsabilidad diferenciada entre ruta, servicio y repositorio; consultas repetidas centralizadas en el repositorio; sin anidamiento innecesario en la ruta; evitar constantes magicas nuevas y conservar los valores existentes del contrato. No se agregan modelos Pydantic en este cambio porque H-02 no los requiere para parametrizar SQL y ampliar el modelado queda fuera del hallazgo seleccionado.
