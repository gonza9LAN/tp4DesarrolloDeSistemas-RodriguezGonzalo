# Parte 2 — Auditoría

## Sección 1: los tests de la IA

Medido sobre el **código original** que entregó la IA (commit `Estado inicial`),
sin modificar `checkout.py` ni `test_checkout_ia.py`.
Entorno: Python 3.13, pytest 9.1.1, pytest-cov 7.1.0.

### 1. Clasificación de los ocho tests

| # | Test | Clasificación | Por qué |
|---|------|---------------|---------|
| 1 | `test_subtotal` | **Tautológico** | El esperado es `CATALOGO["buzo"] * 2`: la misma constante y la misma cuenta que usa el código, en lugar del 49.999,80 de la especificación. |
| 2 | `test_total_funciona` | **Débil** | `is not None` no puede fallar con un `dict`; el test solo se pone en rojo si `calcular_total` lanza una excepción. |
| 3 | `test_total_positivo` | **Débil** | `total > 0` lo cumplen infinitos valores incorrectos. |
| 4 | `test_cupon_egresados` | **Tautológico** | El esperado `100000 * 0.15` repite la fórmula del código, en `float`, con un caso sin redondeo ni fecha límite. |
| 5 | `test_envio_caba` | **Útil** | Compara contra un valor concreto de la especificación (CABA = 2.500), aunque cubre una sola zona lejos del borde. |
| 6 | `test_descuento_por_cantidad` | **Útil** | Verifica un valor concreto (10% de 100.000 = 10.000), pero con 6 prendas, un paso afuera del borde de 5. |
| 7 | `test_talle_valido` | **Débil** | No tiene `assert`: solo falla si `validar_item` lanza una excepción con un ítem perfecto. |
| 8 | `test_no_explota_con_varios_productos` | **Inútil** | El `try/except Exception: pass` se traga cualquier error, así que no puede fallar nunca. |

Resumen: 2 útiles · 3 débiles · 2 tautológicos · 1 inútil.

### 2. Puntaje de mutación de la suite de la IA

```
$ python mutar.py --tests test_checkout_ia.py
Mutando checkout.py contra test_checkout_ia.py  (motor: pytest)

Mutantes generados : 29
Muertos            : 17
Sobrevivientes     : 12
Puntaje de mutación: 58.6%
```

### 3. ¿Por qué casi 80% de cobertura no detecta ninguna falla?

```
$ pytest test_checkout_ia.py --cov=checkout --cov-report=term          → 77% de líneas
$ pytest test_checkout_ia.py --cov=checkout --cov-branch --cov-report=term-missing
checkout.py   62 stmts  14 miss  26 branch  6 partial  73%   Missing: 7-9, 38, 41, 50-51, 67, 73, 76-82, 91
```

Porque la cobertura mide qué líneas **se ejecutaron**, no qué resultados se
**verificaron**. Hay cuatro razones concretas.

- **Asserts que no comparan contra la especificación.** Dos tests repiten la cuenta del código (1 y 4), tres solo exigen que no haya excepción o que el total sea positivo (2, 3 y 7) y uno no puede fallar (8). Las líneas de `calcular_total` cuentan como cubiertas aunque nadie haya mirado si el total es correcto.
- **Casos lejos de los bordes.** La línea 40 está cubierta con cantidad 1 y el bug está en 10; la 60 con 6 prendas y el bug está en 5. Ejecutar una comparación no prueba que su borde sea el correcto.
- **El 23% sin ejecutar es justo lo más riesgoso.** Las líneas 7 a 9 son el constructor de `CheckoutError`: **ningún test provoca nunca un error de negocio**. Tampoco se ejecutan el `except` que saltea productos inexistentes (50–51), el cupón inválido (67), el cupón vencido (73), todo `BIENVENIDA` (76–82) ni la zona inválida (91).
- **Código y tests salieron del mismo malentendido.** La IA escribió los tests mirando su propio código, con `float` y con las mismas fórmulas. Por eso los tests describen lo que el código **hace**, no lo que la especificación **pide**, y dan verde aunque el código esté mal.

---

## Sección 2: hallazgos

Corrí `ruff check checkout.py` y leí los tres módulos línea por línea, comparándolos con la especificación.
Cada falla la confirmé ejecutando el código original con los casos de `CASOS.md`.
**Los números de línea son los de los archivos originales** (commit inicial).

### checkout.py

#### H-01 · El precio lo puede fijar el cliente
- **Archivo y línea:** checkout.py, 49 (`item.get("precio", CATALOGO[...])`)
- **Categoría:** seguridad
- **Regla:** R1 — "El precio sale siempre del catálogo. Si el ítem trae un precio propio, se ignora."
- **Cómo la encontré:** caso 1.2 de CASOS.md y lectura de la línea 49.
- **Severidad:** alta (cualquiera compra a $ 1 editando el request)

#### H-02 · Cupón oculto `DEBUG100` con 100% de descuento
- **Archivo y línea:** checkout.py, 23
- **Categoría:** seguridad
- **Regla:** R6 — "Estos son los únicos dos cupones que existen." y "El descuento nunca puede superar el subtotal."
- **Cómo la encontré:** lectura del diccionario `CUPONES` contra la frase "únicos dos cupones". El total negativo aparece al combinarlo con H-14.
- **Severidad:** alta

#### H-03 · Los importes son `float`
- **Archivo y línea:** checkout.py, 13–15, 21–22, 27–30, 45, 58 y 61
- **Categoría:** numéricos
- **Regla:** R7 — "Todos los importes se manejan como `Decimal`. Nunca `float`."
- **Cómo la encontré:** caso 9.2 de CASOS.md (ejemplo de las secciones 6 y 7) y lectura del catálogo.
- **Severidad:** alta (cobros con centavos incorrectos)

#### H-04 · El redondeo no es comercial
- **Archivo y línea:** checkout.py, 84 (`round(descuento, 2)`); también 54 y 117
- **Categoría:** numéricos
- **Regla:** R7 — "el medio centavo redondea hacia arriba. Ejemplo: 15% de $ 11.999,50 = $ 1.799,925 → $ 1.799,93"
- **Cómo la encontré:** caso 7.2 de CASOS.md, que es el ejemplo literal de la especificación.
- **Severidad:** alta

#### H-05 · Un producto inexistente se saltea en silencio
- **Archivo y línea:** checkout.py, 48–51 (`try` / `except: continue`)
- **Categoría:** manejo de errores
- **Regla:** R1 — "Un producto que no está en el catálogo → `PRODUCTO_INEXISTENTE`."
- **Cómo la encontré:** Ruff (E722 en la línea 50) y caso 1.4 de CASOS.md.
- **Severidad:** alta (pedido con un ítem fantasma que solo cobra el envío)

#### H-06 · El producto se valida después del talle y la cantidad
- **Archivo y línea:** checkout.py, 34–41 (`validar_item` no mira el producto)
- **Categoría:** lógica y límites
- **Regla:** sección 3 — "Cada ítem […]: producto, talle, cantidad." y R1
- **Cómo la encontré:** lectura de `validar_item` comparada con la sección 3 de la especificación.
- **Severidad:** baja

#### H-07 · `validar_item` modifica el ítem que recibe
- **Archivo y línea:** checkout.py, 35 (`item["talle"] = item["talle"].upper()`)
- **Categoría:** efectos laterales
- **Regla:** R4 — "Ninguna función modifica el carrito que recibe."
- **Cómo la encontré:** caso 4.4 de CASOS.md (copiar con `deepcopy` y comparar) y lectura.
- **Severidad:** media

#### H-08 · Un talle con espacios alrededor se rechaza
- **Archivo y línea:** checkout.py, 35 (falta `.strip()`)
- **Categoría:** strings
- **Regla:** R2 — "Se ignoran los espacios al principio y al final (`"  M "` es válido)."
- **Cómo la encontré:** caso 2.3 de CASOS.md.
- **Severidad:** media

#### H-09 · La cantidad 10 se rechaza
- **Archivo y línea:** checkout.py, 40 (`1 <= cantidad < 10`)
- **Categoría:** lógica y límites
- **Regla:** R3 — "entre 1 y 10, ambos inclusive"
- **Cómo la encontré:** valor límite de R3 en CASOS.md. Coincide con el mutante sobreviviente de la línea 40 (sección 1).
- **Severidad:** media

#### H-10 · Se aceptan cantidades que no son enteras
- **Archivo y línea:** checkout.py, 40
- **Categoría:** tipos
- **Regla:** R3 — "Cualquier otro valor, incluidos los no enteros → `CANTIDAD_INVALIDA`."
- **Cómo la encontré:** caso 3.4 de CASOS.md.
- **Severidad:** media

#### H-11 · Ítems incompletos lanzan `KeyError` o `TypeError` en vez de `CheckoutError`
- **Archivo y línea:** checkout.py, 35, 40 y 49
- **Categoría:** manejo de errores
- **Regla:** sección 1 — "Ante cualquier dato inválido, las funciones lanzan `CheckoutError` […] Nunca otro tipo de excepción."
- **Cómo la encontré:** casos 2.6 y 3.5 de CASOS.md.
- **Severidad:** media (por la API terminan en 500, ver H-33)

#### H-12 · Se acepta un carrito vacío
- **Archivo y línea:** checkout.py, 44–54 y 102–119 (no hay ningún control)
- **Categoría:** lógica y límites
- **Regla:** R4 — "Debe tener al menos un ítem → si no, `CARRITO_VACIO`."
- **Cómo la encontré:** valor límite de R4 (0 ítems).
- **Severidad:** media

#### H-13 · Con 5 prendas no se aplica el descuento
- **Archivo y línea:** checkout.py, 60 (`cantidad_prendas > 5`)
- **Categoría:** lógica y límites
- **Regla:** R5 — "5 o más"
- **Cómo la encontré:** valor límite de R5. Coincide con el mutante sobreviviente de la línea 60.
- **Severidad:** media

#### H-14 · El cupón se suma al descuento por cantidad
- **Archivo y línea:** checkout.py, 61, 74 y 82 (`descuento +=`)
- **Categoría:** lógica y límites
- **Regla:** R6 — "El cupón no se acumula con el descuento por cantidad (R5). Se calculan los dos y se aplica el mayor."
- **Cómo la encontré:** caso 6.9 de CASOS.md y lectura de los `+=`.
- **Severidad:** alta (la tienda pierde plata en cada compra grande con cupón)

#### H-15 · El cupón distingue mayúsculas
- **Archivo y línea:** checkout.py, 64 (falta `.upper()`)
- **Categoría:** strings
- **Regla:** R6 — "No se distingue mayúscula de minúscula"
- **Cómo la encontré:** caso 6.6 de CASOS.md.
- **Severidad:** media

#### H-16 · El cupón vacío se trata como inválido
- **Archivo y línea:** checkout.py, 63 (`if cupon != None`)
- **Categoría:** strings
- **Regla:** R6 — "`None`, `""` o un texto de solo espacios equivalen a no usar cupón. No es un error."
- **Cómo la encontré:** caso 6.1 de CASOS.md.
- **Severidad:** alta (si el frontend manda el campo vacío, no se puede comprar sin cupón)

#### H-17 · Un cupón que no es texto lanza `AttributeError`
- **Archivo y línea:** checkout.py, 64
- **Categoría:** tipos
- **Regla:** sección 1 ("Nunca otro tipo de excepción") y R6
- **Cómo la encontré:** caso 6.8 de CASOS.md.
- **Severidad:** baja

#### H-18 · `EGRESADOS2026` se rechaza el último día válido
- **Archivo y línea:** checkout.py, 72 (`if not fecha < vence`)
- **Categoría:** lógica y límites
- **Regla:** R6 — "Válido hasta el 30/11/2026 inclusive"
- **Cómo la encontré:** valor límite de R6. Coincide con el mutante sobreviviente de la línea 72.
- **Severidad:** media

#### H-19 · La fecha por defecto se fija al importar el módulo
- **Archivo y línea:** checkout.py, 57 y 102 (`fecha=date.today()` como valor por defecto)
- **Categoría:** fechas
- **Regla:** R6 — "Si no se recibe `fecha`, se usa la fecha del día en que se hace la llamada."
- **Cómo la encontré:** Ruff (B008, líneas 57 y 102) y caso 6.10 de CASOS.md.
- **Severidad:** alta

#### H-20 · `fecha=None` explícita lanza `TypeError`
- **Archivo y línea:** checkout.py, 72 (compara `None < date`). La llamada viene de pedidos.py, 50, y de api.py, 41.
- **Categoría:** fechas
- **Regla:** contrato de la sección 1 (`fecha: date | None = None`) y R6
- **Cómo la encontré:** caso 6.10 de CASOS.md y lectura de cómo `pedidos.py` llama a `calcular_total`.
- **Severidad:** alta

#### H-21 · Alucinación: `dict_keys.join`
- **Archivo y línea:** checkout.py, 93 (`ENVIOS.keys().join(', ')`)
- **Categoría:** alucinación
- **Regla:** R8 — "Zona que no existe → `ZONA_INVALIDA`."
- **Cómo la encontré:** caso 8.4 de CASOS.md y la documentación de Python: `join` es un método de `str`, no de `dict_keys`. Ruff no lo detecta porque el atributo se resuelve al ejecutar.
- **Severidad:** media

#### H-22 · Una zona que no es texto lanza `AttributeError`
- **Archivo y línea:** checkout.py, 88
- **Categoría:** tipos
- **Regla:** sección 1 y R8
- **Cómo la encontré:** caso 8.5 de CASOS.md.
- **Severidad:** baja

#### H-23 · El envío gratis se calcula sobre el subtotal sin descontar
- **Archivo y línea:** checkout.py, 110 (`calcular_envio(subtotal, zona)`)
- **Categoría:** lógica y límites
- **Regla:** R8 — "El envío es gratis si el subtotal ya con el descuento aplicado es de $ 60.000 o más."
- **Cómo la encontré:** caso 8.6 de CASOS.md, armado para separar "subtotal" de "subtotal con descuento".
- **Severidad:** alta (la tienda paga envíos que no corresponden)

#### H-24 · El parámetro de `calcular_envio` no se llama como en el contrato
- **Archivo y línea:** checkout.py, 87 (`def calcular_envio(subtotal, zona)`)
- **Categoría:** code smell
- **Regla:** sección 1 — la firma es `calcular_envio(subtotal_con_descuento: Decimal, zona: str)` y "No se pueden cambiar nombres, parámetros ni tipos de retorno."
- **Cómo la encontré:** comparando las firmas del código con las de la especificación.
- **Severidad:** baja

#### H-25 · Code smells de checkout.py
- **Archivo y línea:** checkout.py, 1 (`import json` sin uso), 63 (`!= None`), 50 (`except:` vacío), 40, 60 y 96 (números mágicos 10, 5 y 60000), 20–24 (`CUPONES` con un campo `"tipo"` que se resuelve con `if/elif`), 105–107 (acumulador manual de prendas)
- **Categoría:** code smell
- **Regla:** —
- **Cómo la encontré:** Ruff (F401, E711, E722) y lectura.
- **Severidad:** baja

---

### pedidos.py

#### H-26 · El pedido nunca queda confirmado (falta el `commit` final)
- **Archivo y línea:** pedidos.py, 52–71 (el `UPDATE` de montos y los `INSERT` de ítems quedan sin `commit`)
- **Categoría:** efectos laterales
- **Regla:** R10 — "Cuando `guardar_pedido` termina, el pedido es definitivo: cualquier otra conexión a la misma base lo ve completo, con todos sus ítems."
- **Cómo la encontré:** lectura (hay un solo `commit`, a la mitad) y sonda con dos conexiones.
- **Severidad:** alta — por la API **se pierden todos los pedidos**.

#### H-27 · Se guarda el pedido antes de calcularlo: quedan pedidos huérfanos
- **Archivo y línea:** pedidos.py, 39–50 (`INSERT` + `commit` en la 48, y recién en la 50 `calcular_total`)
- **Categoría:** efectos laterales
- **Regla:** R10 — "Si eso lanza `CheckoutError`, el error se propaga y no queda nada guardado: ni el pedido ni sus ítems."
- **Cómo la encontré:** lectura del orden de las operaciones y conteo de filas desde otra conexión.
- **Severidad:** alta

#### H-28 · Los montos se guardan como `REAL` y vuelven con error de `float`
- **Archivo y línea:** pedidos.py, 12–15 y 23 (columnas `REAL`), 55–58 y 68 (`float(...)`), 88–91 y 97 (`Decimal(float)`)
- **Categoría:** numéricos
- **Regla:** R10 — "Los montos que devuelve `obtener_pedido` son idénticos a los que calculó `checkout`: `Decimal`, mismo valor, sin ninguna pérdida."
- **Cómo la encontré:** lectura del esquema y sonda.
- **Severidad:** alta

#### H-29 · `precio_unitario` guarda el precio que manda el cliente
- **Archivo y línea:** pedidos.py, 64 (`item.get("precio", CATALOGO[...])`)
- **Categoría:** seguridad
- **Regla:** R10 — "`precio_unitario` es el precio del catálogo, nunca uno enviado por el cliente."
- **Cómo la encontré:** lectura (la misma línea que H-01, repetida en otra capa) y sonda.
- **Severidad:** alta

#### H-30 · Inyección SQL en `pedidos_de`
- **Archivo y línea:** pedidos.py, 107 (consulta armada con f-string y `'{email}'`)
- **Categoría:** seguridad
- **Regla:** R10 — "El email es un dato que escribe el usuario: ningún valor puede alterar la consulta a la base."
- **Cómo la encontré:** lectura (es la única consulta que no usa `?`) y sonda.
- **Severidad:** alta — expone emails y compras de todos los usuarios.

#### H-31 · Un id fuera de rango lanza `OverflowError`
- **Archivo y línea:** pedidos.py, 75
- **Categoría:** manejo de errores
- **Regla:** R10 — "`obtener_pedido` de un id que no existe devuelve `None`." (y R11: "Un error nunca puede devolver 500")
- **Cómo la encontré:** valor límite de R10 (id fuera del rango de enteros de SQLite).
- **Severidad:** media

---

### api.py

#### H-32 · Los montos viajan como número JSON
- **Archivo y línea:** api.py, 18 (`json.dumps(cuerpo, default=float)`)
- **Categoría:** numéricos
- **Regla:** R11 — "Los montos viajan siempre como texto (`"1799.93"`), nunca como número JSON."
- **Cómo la encontré:** sonda HTTP y lectura de la línea 18.
- **Severidad:** alta

#### H-33 · Todo error se responde con 500
- **Archivo y línea:** api.py, 53–54 y 67–68 (`except Exception` → 500)
- **Categoría:** manejo de errores
- **Regla:** R11 — "Cualquier `CheckoutError` → 422" con formato `{"error": {"code", "message"}}`; "Un error nunca puede devolver 500."
- **Cómo la encontré:** sonda HTTP.
- **Severidad:** alta

#### H-34 · El cliente recibe mensajes internos del servidor
- **Archivo y línea:** api.py, 54 y 68 (`{"error": str(e)}`)
- **Categoría:** seguridad
- **Regla:** R11 (formato de error y "nunca 500"). La especificación no lo dice con estas palabras, pero un servidor no debe exponer detalles internos.
- **Cómo la encontré:** sonda HTTP.
- **Severidad:** media

#### H-35 · La fecha llega como texto hasta checkout
- **Archivo y línea:** api.py, 41 (`datos.get("fecha")` sin convertir)
- **Categoría:** tipos
- **Regla:** R11 — "La fecha viaja como texto en formato AAAA-MM-DD", y el contrato de `guardar_pedido` espera `date | None`.
- **Cómo la encontré:** sonda HTTP con el ejemplo de la sección 7.
- **Severidad:** alta — ningún pedido con cupón y fecha se puede crear.

#### H-36 · El formato de la fecha nunca se valida
- **Archivo y línea:** api.py, 41
- **Categoría:** tipos
- **Regla:** R11 — "La fecha no tiene formato `AAAA-MM-DD` → 400 `FECHA_INVALIDA`"
- **Cómo la encontré:** caso 11.7 de CASOS.md.
- **Severidad:** media

#### H-37 · Un cuerpo que no es JSON responde 500
- **Archivo y línea:** api.py, 31–32
- **Categoría:** manejo de errores
- **Regla:** R11 — "El cuerpo no es JSON válido → 400 `JSON_INVALIDO`"
- **Cómo la encontré:** sonda HTTP.
- **Severidad:** media

#### H-38 · Si faltan datos o tienen otro tipo, responde 500
- **Archivo y línea:** api.py, 37–39 (`datos["email"]`, `datos["carrito"]`, `datos["zona"]` sin validar)
- **Categoría:** tipos
- **Regla:** R11 — "Falta email, zona o carrito, o tienen otro tipo → 400 `DATOS_INCOMPLETOS`"
- **Cómo la encontré:** sonda HTTP.
- **Severidad:** media

#### H-39 · Un pedido inexistente responde 200 con `null`
- **Archivo y línea:** api.py, 64–66
- **Categoría:** manejo de errores
- **Regla:** R11 — "El pedido no existe → 404 `PEDIDO_INEXISTENTE`"
- **Cómo la encontré:** sonda HTTP.
- **Severidad:** media

#### H-40 · La conexión a la base queda abierta si hay un error
- **Archivo y línea:** api.py, 34–44 y 63–65 (`con.close()` solo en el camino feliz)
- **Categoría:** code smell
- **Regla:** —
- **Cómo la encontré:** lectura.
- **Severidad:** baja

---

---

### Ruff

```
$ ruff check checkout.py
checkout.py:1:8:   F401 `json` imported but unused
checkout.py:50:9:  E722 Do not use bare `except`
checkout.py:57:70: B008 Do not perform function call `date.today` in argument defaults
checkout.py:63:17: E711 Comparison to `None` should be `cond is not None`
checkout.py:102:53: B008 Do not perform function call `date.today` in argument defaults
Found 5 errors.
```

El linter por sí solo marcó H-19 (B008) y parte de H-25 (F401, E711), y el `except:` vacío de H-05 (E722). El resto salió de los casos de prueba y de la lectura.

### Tabla de todas las fallas, de la más grave a la menos grave

| Severidad | Hallazgo | Archivo y línea | Categoría | Regla |
|-----------|----------|-----------------|-----------|-------|
| Alta | H-26 Falta el `commit` final: se pierden los pedidos | pedidos.py 52–71 | efectos laterales | R10 |
| Alta | H-30 Inyección SQL en `pedidos_de` | pedidos.py 107 | seguridad | R10 |
| Alta | H-01 El precio lo fija el cliente | checkout.py 49 | seguridad | R1 |
| Alta | H-29 `precio_unitario` del cliente | pedidos.py 64 | seguridad | R10 |
| Alta | H-02 Cupón oculto `DEBUG100` | checkout.py 23 | seguridad | R6 |
| Alta | H-27 Pedidos huérfanos | pedidos.py 39–50 | efectos laterales | R10 |
| Alta | H-14 Cupón y cantidad se acumulan | checkout.py 61, 74, 82 | lógica y límites | R6 |
| Alta | H-23 Envío gratis sin descontar | checkout.py 110 | lógica y límites | R8 |
| Alta | H-03 Importes en `float` | checkout.py 13–30, 45, 58, 61 | numéricos | R7 |
| Alta | H-04 Redondeo no comercial | checkout.py 84 | numéricos | R7 |
| Alta | H-28 Montos guardados como `REAL` | pedidos.py 12–15, 55–58, 88–91 | numéricos | R10 |
| Alta | H-32 Montos como número JSON | api.py 18 | numéricos | R11 |
| Alta | H-35 Fecha en texto hasta checkout | api.py 41 | tipos | R11 |
| Alta | H-20 `fecha=None` → `TypeError` | checkout.py 72 | fechas | R6 |
| Alta | H-19 Fecha fijada al importar | checkout.py 57, 102 | fechas | R6 |
| Alta | H-16 Cupón vacío inválido | checkout.py 63 | strings | R6 |
| Alta | H-05 Producto inexistente salteado | checkout.py 48–51 | manejo de errores | R1 |
| Alta | H-33 Todo error → 500 | api.py 53–54, 67–68 | manejo de errores | R11 |
| Media | H-34 Mensajes internos expuestos | api.py 54, 68 | seguridad | R11 |
| Media | H-07 Modifica el ítem recibido | checkout.py 35 | efectos laterales | R4 |
| Media | H-09 Cantidad 10 rechazada | checkout.py 40 | lógica y límites | R3 |
| Media | H-13 5 prendas sin descuento | checkout.py 60 | lógica y límites | R5 |
| Media | H-18 Cupón rechazado el 30/11 | checkout.py 72 | lógica y límites | R6 |
| Media | H-12 Carrito vacío aceptado | checkout.py 44–54 | lógica y límites | R4 |
| Media | H-10 Cantidades no enteras | checkout.py 40 | tipos | R3 |
| Media | H-36 Fecha sin validar | api.py 41 | tipos | R11 |
| Media | H-38 Datos faltantes → 500 | api.py 37–39 | tipos | R11 |
| Media | H-08 Talle con espacios | checkout.py 35 | strings | R2 |
| Media | H-15 Cupón distingue mayúsculas | checkout.py 64 | strings | R6 |
| Media | H-21 `dict_keys.join` | checkout.py 93 | alucinación | R8 |
| Media | H-11 `KeyError`/`TypeError` en ítems | checkout.py 35, 40, 49 | manejo de errores | sección 1 |
| Media | H-31 Id fuera de rango | pedidos.py 75 | manejo de errores | R10 |
| Media | H-37 JSON inválido → 500 | api.py 31–32 | manejo de errores | R11 |
| Media | H-39 Pedido inexistente → 200 `null` | api.py 64–66 | manejo de errores | R11 |
| Baja | H-06 Orden de validación | checkout.py 34–41 | lógica y límites | sección 3 |
| Baja | H-17 Cupón que no es texto | checkout.py 64 | tipos | R6 |
| Baja | H-22 Zona que no es texto | checkout.py 88 | tipos | R8 |
| Baja | H-24 Nombre de parámetro | checkout.py 87 | code smell | sección 1 |
| Baja | H-25 Code smells de checkout | checkout.py 1, 50, 63, … | code smell | — |
| Baja | H-40 Conexión sin cerrar | api.py 34–44, 63–65 | code smell | — |

