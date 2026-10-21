# Parte 2 — Auditoría

## Sección 1: los tests de la IA


### 1. Clasificación de los ocho tests

| # | Test | Clasificación | Por qué | Qué error deja pasar (ejemplo) |
|---|------|---------------|---------|--------------------------------|
| 1 | `test_subtotal` | **Tautológico** | El esperado es `CATALOGO["buzo"] * 2`: la misma constante y la misma cuenta que usa el código, en lugar del 49.999,80 de la especificación. | Un precio mal cargado en el catálogo: con el buzo en 2.499,90 el test sigue en verde (lo probé). |
| 2 | `test_total_funciona` | **Débil** | `is not None` no puede fallar con un `dict`; el test solo se pone en rojo si `calcular_total` lanza una excepción. | Cualquier importe incorrecto: subtotal, descuento, envío o total. |
| 3 | `test_total_positivo` | **Débil** | `total > 0` lo cumplen infinitos valores incorrectos. | El envío a GBA mal cargado (2.500 en vez de 4.000): el test sigue en verde (lo probé). |
| 4 | `test_cupon_egresados` | **Tautológico** | El esperado `100000 * 0.15` repite la fórmula del código, en `float`, con un caso sin redondeo ni fecha límite. | El redondeo incorrecto del medio centavo (1.799,925 → 1.799,92) y el uso de `float` en lugar de `Decimal`. |
| 5 | `test_envio_caba` | **Útil** | Compara contra un valor concreto de la especificación (CABA = 2.500), aunque cubre una sola zona lejos del borde. | El borde de 60.000, las otras zonas y la zona inválida (que en el código lanza `AttributeError`). |
| 6 | `test_descuento_por_cantidad` | **Útil** | Verifica un valor concreto (10% de 100.000 = 10.000), pero con 6 prendas, un paso afuera del borde de 5. | Que con exactamente 5 prendas no se aplique el descuento (`> 5` en lugar de `>= 5`). |
| 7 | `test_talle_valido` | **Débil** | No tiene `assert`: solo falla si `validar_item` lanza una excepción con un ítem perfecto. | Que `validar_item` modifique el ítem recibido, o que no valide nada: con la validación del talle desactivada sigue en verde (lo probé). |
| 8 | `test_no_explota_con_varios_productos` | **Inútil** | El `try/except Exception: pass` se traga cualquier error, así que no puede fallar nunca. | Todo, incluso un `calcular_total` que siempre lanza una excepción: con ese cambio el test **pasa** (lo probé). |

Resumen: 2 útiles · 3 débiles · 2 tautológicos · 1 inútil.

**Débil frente a inútil.** Los tests 2 y 7 se parecen al 8, pero no son iguales.
Cuando hice que `calcular_total` lanzara siempre una excepción, el test 2
falló y el 8 pasó. El 2 y el 7 detectan al menos que el código "explote"; el
8 no detecta absolutamente nada.

### 2. Puntaje de mutación de la suite de la IA

```
$ python mutar.py --tests test_checkout_ia.py
Mutando checkout.py contra test_checkout_ia.py  (motor: pytest)

Mutantes generados : 29
Muertos            : 17
Sobrevivientes     : 12
Puntaje de mutación: 58.6%
```

Los 12 sobrevivientes (líneas del `checkout.py` original) se agrupan así:

| Grupo | Sobrevivientes | Qué test los habría detectado |
|-------|----------------|-------------------------------|
| Bordes sin probar | línea 40 `<` → `<=` y `10` → `11` (cantidad); línea 60 `>` → `>=` (prendas); línea 72 `<` → `<=` (vencimiento); línea 96 `>=` → `>` y `60000` → `60001` (envío gratis) | Tests **en el borde**: cantidad 10, exactamente 5 prendas, fecha 30/11/2026, base de exactamente 60.000 |
| `BIENVENIDA` nunca probado | línea 76 `==` → `!=`; línea 77 `<` → `<=`; línea 82 `+` → `-` | `calcular_descuento(20000, 1, "BIENVENIDA", fecha)` debe dar 3.000 (y 19.999,99 debe dar error) |
| Total y prendas sin valor exacto | línea 107 `+` → `-` (suma de prendas); línea 111 `+`/`-` invertidos (total) | Un `calcular_total` comparado contra el total exacto de la especificación, con descuento y envío distintos de cero |

En tres de esos bordes (líneas 40, 60 y 72) el mutante es justamente lo que
pide la especificación ("1 y 10, ambos inclusive", "5 o más", "hasta el
30/11/2026 inclusive"). Un test escrito desde la especificación habría matado
al mutante **y además** habría encontrado la falla en el código original.

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

### Cómo se trabajó

1. Corrí `ruff check checkout.py` con el `ruff.toml` entregado (resultado al final de esta sección).
2. Leí `checkout.py`, `pedidos.py` y `api.py` línea por línea, comparando cada una con la especificación.
3. Ejecuté el **código original** en una copia temporal con las entradas de `CASOS.md`, para anotar el resultado
   **real** de cada falla en lugar de suponerlo. Esa ejecución también levanta la API y le manda requests HTTP.

**Los números de línea son los de los archivos originales** (commit `Estado inicial`). Después de las correcciones
de la Parte 3 cambian, así que no hay que buscarlos en el `checkout.py` corregido.

En cada hallazgo:
- **Tipo**: *demostrada* (la ejecuté y falla), *consecuencia* (efecto visible de otra falla, sin causa propia) o *code smell*.
- **Test**: el test que la va a demostrar. Los de `checkout.py` son los RED de la Parte 3; los de `pedidos.py` y `api.py` van en las suites de la Parte 4.
- `V` = `date(2026, 10, 1)`.

---

### checkout.py

#### H-01 · El precio lo puede fijar el cliente
- **Archivo y línea:** checkout.py, 49 (`item.get("precio", CATALOGO[...])`)
- **Categoría:** seguridad
- **Regla:** R1 — "El precio sale siempre del catálogo. Si el ítem trae un precio propio, se ignora."
- **Entrada → actual → esperado:** `calcular_subtotal([{"producto":"buzo","talle":"M","cantidad":1,"precio":1}])` → `1` → `D("24999.90")`
- **Cómo la encontré:** caso 1.2 de CASOS.md y lectura de la línea 49.
- **Tipo / nivel / severidad:** demostrada · unitario · **alta** (cualquiera compra a $ 1 editando el request)
- **Test:** `test_el_precio_sale_del_catalogo_aunque_el_item_traiga_otro`

#### H-02 · Cupón oculto `DEBUG100` con 100% de descuento
- **Archivo y línea:** checkout.py, 23
- **Categoría:** seguridad
- **Regla:** R6 — "Estos son los únicos dos cupones que existen." y "El descuento nunca puede superar el subtotal."
- **Entrada → actual → esperado:** `calcular_total([it("campera","M",6)], "CABA", "DEBUG100", V)` → descuento `316799.93` sobre subtotal `287999.94`, **total `-28799.99`** → `ERROR(CUPON_INVALIDO)`
- **Cómo la encontré:** lectura del diccionario `CUPONES` contra la frase "únicos dos cupones". El total negativo aparece al combinarlo con H-14.
- **Tipo / nivel / severidad:** demostrada · unitario · **alta**
- **Test:** `test_solo_existen_dos_cupones`

#### H-03 · Los importes son `float`
- **Archivo y línea:** checkout.py, 13–15, 21–22, 27–30, 45, 58 y 61
- **Categoría:** numéricos
- **Regla:** R7 — "Todos los importes se manejan como `Decimal`. Nunca `float`."
- **Entrada → actual → esperado:** `calcular_total([it("remera","M",1)], "CABA", "EGRESADOS2026", V)` → `{'subtotal': 11999.5, 'descuento': 1799.92, 'envio': 2500, 'total': 12699.58}` (tipos `float` e `int`) → `D("11999.50")`, `D("1799.93")`, `D("2500.00")`, `D("12699.57")`
- **Cómo la encontré:** caso 9.2 de CASOS.md (ejemplo de las secciones 6 y 7) y lectura del catálogo.
- **Tipo / nivel / severidad:** demostrada · unitario · **alta** (cobros con centavos incorrectos)
- **Test:** `test_calcular_total_del_ejemplo_devuelve_decimal`

#### H-04 · El redondeo no es comercial
- **Archivo y línea:** checkout.py, 84 (`round(descuento, 2)`); también 54 y 117
- **Categoría:** numéricos
- **Regla:** R7 — "el medio centavo redondea hacia arriba. Ejemplo: 15% de $ 11.999,50 = $ 1.799,925 → $ 1.799,93"
- **Entrada → actual → esperado:** `calcular_descuento(11999.50, 1, "EGRESADOS2026", V)` → `1799.92` → `D("1799.93")`
- **Cómo la encontré:** caso 7.2 de CASOS.md, que es el ejemplo literal de la especificación.
- **Tipo / nivel / severidad:** demostrada · unitario · **alta**. Es una causa distinta de H-03: aunque se use `Decimal`, `round()` redondea hacia el par (1.799,92).
- **Test:** `test_el_medio_centavo_redondea_hacia_arriba`

#### H-05 · Un producto inexistente se saltea en silencio
- **Archivo y línea:** checkout.py, 48–51 (`try` / `except: continue`)
- **Categoría:** manejo de errores
- **Regla:** R1 — "Un producto que no está en el catálogo → `PRODUCTO_INEXISTENTE`."
- **Entrada → actual → esperado:** `calcular_total([it("gorra","M",1)], "CABA")` → `{'subtotal': 0, 'descuento': 0, 'envio': 2500, 'total': 2500}` → `ERROR(PRODUCTO_INEXISTENTE)`
- **Cómo la encontré:** Ruff (E722 en la línea 50) y caso 1.4 de CASOS.md.
- **Tipo / nivel / severidad:** demostrada · unitario · **alta** (pedido con un ítem fantasma que solo cobra el envío)
- **Test:** `test_un_producto_inexistente_no_se_saltea`

#### H-06 · El producto se valida después del talle y la cantidad
- **Archivo y línea:** checkout.py, 34–41 (`validar_item` no mira el producto)
- **Categoría:** lógica y límites
- **Regla:** sección 3 — "Cada ítem […]: producto, talle, cantidad." y R1
- **Entrada → actual → esperado:** `calcular_total([it("gorra","XXXL",1)], "CABA")` → `TALLE_INVALIDO` → `PRODUCTO_INEXISTENTE`. Además `validar_item(it("gorra","M",1))` no lanza nada.
- **Cómo la encontré:** tabla "Orden de validación" de CASOS.md.
- **Tipo / nivel / severidad:** demostrada · unitario · **baja**. Comparte causa con H-05 (el producto no se valida en `validar_item`) y probablemente se corrijan juntas.
- **Test:** `test_el_producto_se_valida_antes_que_el_talle`

#### H-07 · `validar_item` modifica el ítem que recibe
- **Archivo y línea:** checkout.py, 35 (`item["talle"] = item["talle"].upper()`)
- **Categoría:** efectos laterales
- **Regla:** R4 — "Ninguna función modifica el carrito que recibe."
- **Entrada → actual → esperado:** ítem con `"talle": "m"` → después de `validar_item` queda `"M"` → el ítem queda igual
- **Cómo la encontré:** caso 4.4 de CASOS.md (copiar con `deepcopy` y comparar) y lectura.
- **Tipo / nivel / severidad:** demostrada · unitario · **media**. Como consecuencia, `guardar_pedido` también modifica el carrito que le pasa la API.
- **Test:** `test_validar_item_no_modifica_el_item`

#### H-08 · Un talle con espacios alrededor se rechaza
- **Archivo y línea:** checkout.py, 35 (falta `.strip()`)
- **Categoría:** strings
- **Regla:** R2 — "Se ignoran los espacios al principio y al final (`"  M "` es válido)."
- **Entrada → actual → esperado:** `validar_item(it("buzo","  M ",1))` → `TALLE_INVALIDO` → válido
- **Cómo la encontré:** caso 2.3 de CASOS.md.
- **Tipo / nivel / severidad:** demostrada · unitario · **media**
- **Test:** `test_talle_con_espacios_alrededor_es_valido`

#### H-09 · La cantidad 10 se rechaza
- **Archivo y línea:** checkout.py, 40 (`1 <= cantidad < 10`)
- **Categoría:** lógica y límites
- **Regla:** R3 — "entre 1 y 10, ambos inclusive"
- **Entrada → actual → esperado:** `validar_item(it("buzo","M",10))` → `CANTIDAD_INVALIDA` → válido
- **Cómo la encontré:** valor límite de R3 en CASOS.md. Coincide con el mutante sobreviviente de la línea 40 (sección 1).
- **Tipo / nivel / severidad:** demostrada · unitario · **media**
- **Test:** `test_cantidad_diez_es_valida`

#### H-10 · Se aceptan cantidades que no son enteras
- **Archivo y línea:** checkout.py, 40
- **Categoría:** tipos
- **Regla:** R3 — "Cualquier otro valor, incluidos los no enteros → `CANTIDAD_INVALIDA`."
- **Entrada → actual → esperado:** `calcular_subtotal([it("remera","M",2.5)])` → `29998.75` (cobra dos remeras y media) → `ERROR(CANTIDAD_INVALIDA)`
- **Cómo la encontré:** caso 3.4 de CASOS.md.
- **Tipo / nivel / severidad:** demostrada · unitario · **media**
- **Test:** `test_cantidad_que_no_es_entera_es_invalida`

#### H-11 · Ítems incompletos lanzan `KeyError` o `TypeError` en vez de `CheckoutError`
- **Archivo y línea:** checkout.py, 35, 40 y 49
- **Categoría:** manejo de errores
- **Regla:** sección 1 — "Ante cualquier dato inválido, las funciones lanzan `CheckoutError` […] Nunca otro tipo de excepción."
- **Entrada → actual → esperado:** ítem sin `"talle"` → `KeyError: 'talle'`; cantidad `"2"` → `TypeError` → `ERROR(TALLE_INVALIDO)` / `ERROR(CANTIDAD_INVALIDA)`
- **Cómo la encontré:** casos 2.6 y 3.5 de CASOS.md.
- **Tipo / nivel / severidad:** demostrada · unitario · **media** (por la API terminan en 500, ver H-33)
- **Test:** `test_item_incompleto_lanza_checkout_error`

#### H-12 · Se acepta un carrito vacío
- **Archivo y línea:** checkout.py, 44–54 y 102–119 (no hay ningún control)
- **Categoría:** lógica y límites
- **Regla:** R4 — "Debe tener al menos un ítem → si no, `CARRITO_VACIO`."
- **Entrada → actual → esperado:** `calcular_total([], "CABA")` → `{'subtotal': 0, …, 'total': 2500}` → `ERROR(CARRITO_VACIO)`
- **Cómo la encontré:** valor límite de R4 (0 ítems).
- **Tipo / nivel / severidad:** demostrada · unitario · **media**
- **Test:** `test_carrito_vacio_es_un_error`

#### H-13 · Con 5 prendas no se aplica el descuento
- **Archivo y línea:** checkout.py, 60 (`cantidad_prendas > 5`)
- **Categoría:** lógica y límites
- **Regla:** R5 — "5 o más"
- **Entrada → actual → esperado:** `calcular_descuento(100000, 5, None, V)` → `0` → `D("10000.00")`
- **Cómo la encontré:** valor límite de R5. Coincide con el mutante sobreviviente de la línea 60.
- **Tipo / nivel / severidad:** demostrada · unitario · **media**
- **Test:** `test_cinco_prendas_tienen_descuento`

#### H-14 · El cupón se suma al descuento por cantidad
- **Archivo y línea:** checkout.py, 61, 74 y 82 (`descuento +=`)
- **Categoría:** lógica y límites
- **Regla:** R6 — "El cupón no se acumula con el descuento por cantidad (R5). Se calculan los dos y se aplica el mayor."
- **Entrada → actual → esperado:** `calcular_descuento(100000, 6, "EGRESADOS2026", V)` → `25000.0` → `D("15000.00")`
- **Cómo la encontré:** caso 6.9 de CASOS.md y lectura de los `+=`.
- **Tipo / nivel / severidad:** demostrada · unitario · **alta** (la tienda pierde plata en cada compra grande con cupón)
- **Test:** `test_cupon_y_cantidad_no_se_acumulan`

#### H-15 · El cupón distingue mayúsculas
- **Archivo y línea:** checkout.py, 64 (falta `.upper()`)
- **Categoría:** strings
- **Regla:** R6 — "No se distingue mayúscula de minúscula"
- **Entrada → actual → esperado:** `"egresados2026"` → `CUPON_INVALIDO` → `D("15000.00")`
- **Cómo la encontré:** caso 6.6 de CASOS.md.
- **Tipo / nivel / severidad:** demostrada · unitario · **media**
- **Test:** `test_cupon_sin_importar_mayusculas`

#### H-16 · El cupón vacío se trata como inválido
- **Archivo y línea:** checkout.py, 63 (`if cupon != None`)
- **Categoría:** strings
- **Regla:** R6 — "`None`, `""` o un texto de solo espacios equivalen a no usar cupón. No es un error."
- **Entrada → actual → esperado:** `calcular_descuento(100000, 1, "", V)` → `CUPON_INVALIDO` → `D("0.00")`
- **Cómo la encontré:** caso 6.1 de CASOS.md.
- **Tipo / nivel / severidad:** demostrada · unitario · **alta** (si el frontend manda el campo vacío, no se puede comprar sin cupón)
- **Test:** `test_cupon_vacio_equivale_a_no_usar_cupon`

#### H-17 · Un cupón que no es texto lanza `AttributeError`
- **Archivo y línea:** checkout.py, 64
- **Categoría:** tipos
- **Regla:** sección 1 ("Nunca otro tipo de excepción") y R6
- **Entrada → actual → esperado:** `calcular_descuento(100000, 1, 123, V)` → `AttributeError` → `ERROR(CUPON_INVALIDO)` (interpretación de CASOS.md)
- **Cómo la encontré:** caso 6.8 de CASOS.md.
- **Tipo / nivel / severidad:** demostrada · unitario · **baja**
- **Test:** `test_cupon_que_no_es_texto_es_invalido`

#### H-18 · `EGRESADOS2026` se rechaza el último día válido
- **Archivo y línea:** checkout.py, 72 (`if not fecha < vence`)
- **Categoría:** lógica y límites
- **Regla:** R6 — "Válido hasta el 30/11/2026 inclusive"
- **Entrada → actual → esperado:** `calcular_descuento(100000, 1, "EGRESADOS2026", date(2026,11,30))` → `CUPON_VENCIDO` → `D("15000.00")`
- **Cómo la encontré:** valor límite de R6. Coincide con el mutante sobreviviente de la línea 72.
- **Tipo / nivel / severidad:** demostrada · unitario · **media**
- **Test:** `test_egresados_es_valido_el_30_de_noviembre`

#### H-19 · La fecha por defecto se fija al importar el módulo
- **Archivo y línea:** checkout.py, 57 y 102 (`fecha=date.today()` como valor por defecto)
- **Categoría:** fechas
- **Regla:** R6 — "Si no se recibe `fecha`, se usa la fecha del día en que se hace la llamada."
- **Entrada → actual → esperado:** `calcular_descuento.__defaults__` → `(None, date(2026, 10, 21))`, el día en que se importó el módulo y no el de cada llamada. Un servidor que arranca el 29/11 acepta el cupón vencido indefinidamente → debe usarse la fecha de cada llamada.
- **Cómo la encontré:** Ruff (B008, líneas 57 y 102) y caso 6.10 de CASOS.md.
- **Tipo / nivel / severidad:** demostrada · unitario (simulando "hoy") · **alta**
- **Test:** `test_sin_fecha_se_usa_el_dia_de_la_llamada`

#### H-20 · `fecha=None` explícita lanza `TypeError`
- **Archivo y línea:** checkout.py, 72 (compara `None < date`). La llamada viene de pedidos.py, 50, y de api.py, 41.
- **Categoría:** fechas
- **Regla:** contrato de la sección 1 (`fecha: date | None = None`) y R6
- **Entrada → actual → esperado:** `calcular_descuento(100000, 1, "EGRESADOS2026", None)` → `TypeError` → usar la fecha del día. Por la API, `POST` con `EGRESADOS2026` sin `fecha` → **500**.
- **Cómo la encontré:** caso 6.10 de CASOS.md y lectura de cómo `pedidos.py` llama a `calcular_total`.
- **Tipo / nivel / severidad:** demostrada · unitario, integración y E2E · **alta**. Es una falla entre capas: `pedidos.py` siempre pasa `fecha` (aunque sea `None`) y `checkout.py` no lo acepta. Ninguna capa falla sola.
- **Test:** `test_fecha_none_equivale_al_dia_de_la_llamada`

#### H-21 · Alucinación: `dict_keys.join`
- **Archivo y línea:** checkout.py, 93 (`ENVIOS.keys().join(', ')`)
- **Categoría:** alucinación
- **Regla:** R8 — "Zona que no existe → `ZONA_INVALIDA`."
- **Entrada → actual → esperado:** `calcular_envio(1000, "MARTE")` → `AttributeError: 'dict_keys' object has no attribute 'join'` → `ERROR(ZONA_INVALIDA)`
- **Cómo la encontré:** caso 8.4 de CASOS.md y la documentación de Python: `join` es un método de `str`, no de `dict_keys`. Ruff no lo detecta porque el atributo se resuelve al ejecutar.
- **Tipo / nivel / severidad:** demostrada · unitario · **media**
- **Test:** `test_zona_inexistente_lanza_zona_invalida`

#### H-22 · Una zona que no es texto lanza `AttributeError`
- **Archivo y línea:** checkout.py, 88
- **Categoría:** tipos
- **Regla:** sección 1 y R8
- **Entrada → actual → esperado:** `calcular_envio(1000, None)` → `AttributeError` → `ERROR(ZONA_INVALIDA)` (interpretación de CASOS.md)
- **Cómo la encontré:** caso 8.5 de CASOS.md.
- **Tipo / nivel / severidad:** demostrada · unitario · **baja**
- **Test:** `test_zona_que_no_es_texto_es_invalida`

#### H-23 · El envío gratis se calcula sobre el subtotal sin descontar
- **Archivo y línea:** checkout.py, 110 (`calcular_envio(subtotal, zona)`)
- **Categoría:** lógica y límites
- **Regla:** R8 — "El envío es gratis si el subtotal ya con el descuento aplicado es de $ 60.000 o más."
- **Entrada → actual → esperado:** `calcular_total([it("buzo","M",2), it("remera","M",1)], "CABA", "EGRESADOS2026", V)` → envío `0` (base real 52.699,40) → envío `D("2500.00")`, total `D("55199.40")`
- **Cómo la encontré:** caso 8.6 de CASOS.md, armado para separar "subtotal" de "subtotal con descuento".
- **Tipo / nivel / severidad:** demostrada · unitario · **alta** (la tienda paga envíos que no corresponden)
- **Test:** `test_envio_gratis_se_evalua_con_el_descuento_aplicado`

#### H-24 · El parámetro de `calcular_envio` no se llama como en el contrato
- **Archivo y línea:** checkout.py, 87 (`def calcular_envio(subtotal, zona)`)
- **Categoría:** code smell (ver "Decisiones" al final: no hay categoría para contratos)
- **Regla:** sección 1 — la firma es `calcular_envio(subtotal_con_descuento: Decimal, zona: str)` y "No se pueden cambiar nombres, parámetros ni tipos de retorno."
- **Entrada → actual → esperado:** `calcular_envio(subtotal_con_descuento=1000, zona="GBA")` → `TypeError: unexpected keyword argument` → `D("4000.00")`
- **Cómo la encontré:** comparando las firmas del código con las de la especificación.
- **Tipo / nivel / severidad:** demostrada · unitario · **baja**. El nombre `subtotal` además favorece el error de H-23.
- **Test:** pendiente de decidir (ver "Decisiones").

#### H-25 · Code smells de checkout.py
- **Archivo y línea:** checkout.py, 1 (`import json` sin uso), 63 (`!= None`), 50 (`except:` vacío), 40, 60 y 96 (números mágicos 10, 5 y 60000), 20–24 (`CUPONES` con un campo `"tipo"` que se resuelve con `if/elif`), 105–107 (acumulador manual de prendas)
- **Categoría:** code smell
- **Regla:** —
- **Qué pasa:** nada visible hoy, pero dificulta leer y cambiar las reglas.
- **Cómo la encontré:** Ruff (F401, E711, E722) y lectura.
- **Tipo / nivel / severidad:** code smell · ninguno (análisis estático) · **baja**
- **Test:** — (se corrigen en un `refactor:` con la suite en verde)

---

### pedidos.py

> El enunciado indica que `pedidos.py` y `api.py` **no se corrigen**. Estas fallas se documentan acá
> y se demuestran con los tests de integración y E2E de la Parte 4.

#### H-26 · El pedido nunca queda confirmado (falta el `commit` final)
- **Archivo y línea:** pedidos.py, 52–71 (el `UPDATE` de montos y los `INSERT` de ítems quedan sin `commit`)
- **Categoría:** efectos laterales (ver "Decisiones")
- **Regla:** R10 — "Cuando `guardar_pedido` termina, el pedido es definitivo: cualquier otra conexión a la misma base lo ve completo, con todos sus ítems."
- **Entrada → actual → esperado:** guardar un pedido y leerlo desde **otra** conexión → `total=0`, `items=0` → montos e ítems completos. Por la API: `POST` responde `201` con los montos, pero el `GET` siguiente muestra `subtotal 0.0` e `items []`. En la base quedaron 6 pedidos, todos con montos en 0.
- **Cómo la encontré:** lectura (hay un solo `commit`, a la mitad) y sonda con dos conexiones.
- **Tipo / nivel / severidad:** demostrada · integración y E2E · **alta**: por la API **se pierden todos los pedidos**.
- **Test:** `test_otra_conexion_ve_el_pedido_completo` (integración); `test_crear_y_leer_un_pedido` (E2E)

#### H-27 · Se guarda el pedido antes de calcularlo: quedan pedidos huérfanos
- **Archivo y línea:** pedidos.py, 39–50 (`INSERT` + `commit` en la 48, y recién en la 50 `calcular_total`)
- **Categoría:** efectos laterales (ver "Decisiones")
- **Regla:** R10 — "Si eso lanza `CheckoutError`, el error se propaga y no queda nada guardado: ni el pedido ni sus ítems."
- **Entrada → actual → esperado:** `guardar_pedido(con, "a@a.com", [it("buzo","XXXL",1)], "CABA")` → se propaga el error, pero queda **1 fila** en `pedidos` → 0 filas
- **Cómo la encontré:** lectura del orden de las operaciones y conteo de filas desde otra conexión.
- **Tipo / nivel / severidad:** demostrada · integración · **alta**. El diseño en tres pasos con un `commit` intermedio también impide que pedido e ítems se guarden juntos o no se guarden.
- **Test:** `test_un_error_de_checkout_no_deja_nada_guardado`

#### H-28 · Los montos se guardan como `REAL` y vuelven con error de `float`
- **Archivo y línea:** pedidos.py, 12–15 y 23 (columnas `REAL`), 55–58 y 68 (`float(...)`), 88–91 y 97 (`Decimal(float)`)
- **Categoría:** numéricos
- **Regla:** R10 — "Los montos que devuelve `obtener_pedido` son idénticos a los que calculó `checkout`: `Decimal`, mismo valor, sin ninguna pérdida."
- **Entrada → actual → esperado:** descuento guardado → `Decimal('1799.920000000000072759576141834259033203125')` → `Decimal("1799.93")`. Aunque checkout se corrija y calcule bien, `Decimal(1799.93)` vale `1799.930000000000063664…`.
- **Cómo la encontré:** lectura del esquema y sonda.
- **Tipo / nivel / severidad:** demostrada · integración · **alta**
- **Test:** `test_los_montos_guardados_son_identicos_a_los_calculados`

#### H-29 · `precio_unitario` guarda el precio que manda el cliente
- **Archivo y línea:** pedidos.py, 64 (`item.get("precio", CATALOGO[...])`)
- **Categoría:** seguridad
- **Regla:** R10 — "`precio_unitario` es el precio del catálogo, nunca uno enviado por el cliente."
- **Entrada → actual → esperado:** ítem con `"precio": 1` → `precio_unitario == Decimal('1')` → `D("24999.90")`
- **Cómo la encontré:** lectura (la misma línea que H-01, repetida en otra capa) y sonda.
- **Tipo / nivel / severidad:** demostrada · integración · **alta**. Aun con checkout corregido, la base guardaría un precio falso.
- **Test:** `test_precio_unitario_es_el_del_catalogo`

#### H-30 · Inyección SQL en `pedidos_de`
- **Archivo y línea:** pedidos.py, 107 (consulta armada con f-string y `'{email}'`)
- **Categoría:** seguridad
- **Regla:** R10 — "El email es un dato que escribe el usuario: ningún valor puede alterar la consulta a la base."
- **Entrada → actual → esperado:** `pedidos_de(con, "x' OR '1'='1")` → devuelve **todos** los pedidos de la base (4 de 4, de distintos emails) → `[]`. Un email legítimo como `"o'brien@mail.com"` → `OperationalError` → sus pedidos.
- **Cómo la encontré:** lectura (es la única consulta que no usa `?`) y sonda.
- **Tipo / nivel / severidad:** demostrada · integración · **alta**: expone emails y compras de todos los usuarios.
- **Test:** `test_un_email_malicioso_no_altera_la_consulta`

#### H-31 · Un id fuera de rango lanza `OverflowError`
- **Archivo y línea:** pedidos.py, 75
- **Categoría:** manejo de errores
- **Regla:** R10 — "`obtener_pedido` de un id que no existe devuelve `None`." (y R11: "Un error nunca puede devolver 500")
- **Entrada → actual → esperado:** `obtener_pedido(con, 2**63)` → `OverflowError` → `None`. Por la API, `GET /api/v1/pedidos/99999999999999999999` → **500**.
- **Cómo la encontré:** valor límite de R10 (id fuera del rango de enteros de SQLite).
- **Tipo / nivel / severidad:** demostrada · integración y E2E · **media**
- **Test:** `test_un_id_fuera_de_rango_devuelve_none`

---

### api.py

#### H-32 · Los montos viajan como número JSON
- **Archivo y línea:** api.py, 18 (`json.dumps(cuerpo, default=float)`)
- **Categoría:** numéricos
- **Regla:** R11 — "Los montos viajan siempre como texto (`"1799.93"`), nunca como número JSON."
- **Entrada → actual → esperado:** `POST` válido → `{"subtotal": 11999.5, "descuento": 0.0, …}` → `{"subtotal": "11999.50", "descuento": "0.00", …}`
- **Cómo la encontré:** sonda HTTP y lectura de la línea 18.
- **Tipo / nivel / severidad:** demostrada · E2E · **alta**
- **Test:** `test_crear_y_leer_un_pedido`

#### H-33 · Todo error se responde con 500
- **Archivo y línea:** api.py, 53–54 y 67–68 (`except Exception` → 500)
- **Categoría:** manejo de errores
- **Regla:** R11 — "Cualquier `CheckoutError` → 422" con formato `{"error": {"code", "message"}}`; "Un error nunca puede devolver 500."
- **Entrada → actual → esperado:** `POST` con talle `"XXXL"` → `500 {"error": "Talle inválido: XXXL"}` (sin `code`) → `422 {"error": {"code": "TALLE_INVALIDO", …}}`
- **Cómo la encontré:** sonda HTTP.
- **Tipo / nivel / severidad:** demostrada · E2E · **alta**
- **Test:** `test_un_error_de_negocio_responde_422`

#### H-34 · El cliente recibe mensajes internos del servidor
- **Archivo y línea:** api.py, 54 y 68 (`{"error": str(e)}`)
- **Categoría:** seguridad
- **Regla:** R11 (formato de error y "nunca 500"). La especificación no lo dice con estas palabras, pero un servidor no debe exponer detalles internos.
- **Entrada → actual → esperado:** `GET` de un id enorme → `{"error": "Python int too large to convert to SQLite INTEGER"}`; zona inválida → `{"error": "'dict_keys' object has no attribute 'join'"}` → mensaje controlado, sin detalles de Python ni de la base
- **Cómo la encontré:** sonda HTTP.
- **Tipo / nivel / severidad:** demostrada · E2E · **media**
- **Test:** cubierto por los tests de error de E2E, que comparan el formato `{"error": {"code", "message"}}`

#### H-35 · La fecha llega como texto hasta checkout
- **Archivo y línea:** api.py, 41 (`datos.get("fecha")` sin convertir)
- **Categoría:** tipos
- **Regla:** R11 — "La fecha viaja como texto en formato AAAA-MM-DD", y el contrato de `guardar_pedido` espera `date | None`.
- **Entrada → actual → esperado:** `POST` con `"cupon": "EGRESADOS2026", "fecha": "2026-11-30"` (el ejemplo de la especificación) → **500** (`'<' not supported between instances of 'str' and 'datetime.date'`) → `201` con descuento `"1799.93"`
- **Cómo la encontré:** sonda HTTP con el ejemplo de la sección 7.
- **Tipo / nivel / severidad:** demostrada · E2E · **alta**: ningún pedido con cupón y fecha se puede crear. Falla entre capas: la API pasa texto y checkout espera una fecha.
- **Test:** `test_crear_un_pedido_con_cupon_y_fecha`

#### H-36 · El formato de la fecha nunca se valida
- **Archivo y línea:** api.py, 41
- **Categoría:** tipos
- **Regla:** R11 — "La fecha no tiene formato `AAAA-MM-DD` → 400 `FECHA_INVALIDA`"
- **Entrada → actual → esperado:** `POST` sin cupón con `"fecha": "30/11/2026"` → **201** (la fecha mal escrita se acepta sin mirarla) → `400 FECHA_INVALIDA`
- **Cómo la encontré:** caso 11.7 de CASOS.md.
- **Tipo / nivel / severidad:** demostrada · E2E · **media**
- **Test:** `test_una_fecha_con_otro_formato_responde_400`

#### H-37 · Un cuerpo que no es JSON responde 500
- **Archivo y línea:** api.py, 31–32
- **Categoría:** manejo de errores
- **Regla:** R11 — "El cuerpo no es JSON válido → 400 `JSON_INVALIDO`"
- **Entrada → actual → esperado:** cuerpo `{nojson` → `500` con el mensaje del parser → `400 JSON_INVALIDO`
- **Cómo la encontré:** sonda HTTP.
- **Tipo / nivel / severidad:** demostrada · E2E · **media**
- **Test:** `test_un_cuerpo_que_no_es_json_responde_400`

#### H-38 · Si faltan datos o tienen otro tipo, responde 500
- **Archivo y línea:** api.py, 37–39 (`datos["email"]`, `datos["carrito"]`, `datos["zona"]` sin validar)
- **Categoría:** tipos
- **Regla:** R11 — "Falta email, zona o carrito, o tienen otro tipo → 400 `DATOS_INCOMPLETOS`"
- **Entrada → actual → esperado:** `POST` sin `email` → `500 {"error": "'email'"}` → `400 DATOS_INCOMPLETOS`
- **Cómo la encontré:** sonda HTTP.
- **Tipo / nivel / severidad:** demostrada · E2E · **media**
- **Test:** `test_datos_incompletos_responden_400`

#### H-39 · Un pedido inexistente responde 200 con `null`
- **Archivo y línea:** api.py, 64–66
- **Categoría:** manejo de errores
- **Regla:** R11 — "El pedido no existe → 404 `PEDIDO_INEXISTENTE`"
- **Entrada → actual → esperado:** `GET /api/v1/pedidos/999` → `200 null` → `404 PEDIDO_INEXISTENTE`
- **Cómo la encontré:** sonda HTTP.
- **Tipo / nivel / severidad:** demostrada · E2E · **media**
- **Test:** `test_un_pedido_inexistente_responde_404`

#### H-40 · La conexión a la base queda abierta si hay un error
- **Archivo y línea:** api.py, 34–44 y 63–65 (`con.close()` solo en el camino feliz)
- **Categoría:** code smell
- **Regla:** —
- **Qué pasa:** cada request con error deja una conexión sin cerrar; con muchos errores se acumulan.
- **Cómo la encontré:** lectura.
- **Tipo / nivel / severidad:** code smell · ninguno · **baja**
- **Test:** —

---

### Consecuencias (sin causa propia, no se cuentan aparte)

| Efecto observado | Viene de |
|------------------|----------|
| Total negativo (`-28799.99`) | H-02 + H-14 |
| `guardar_pedido` modifica el carrito que recibe | H-07 |
| Por la API, cada `POST` fallido deja un pedido en 0 en la base (quedaron 6 filas, todas en 0) | H-27 + H-26 |
| `GET` de un id enorme responde 500 | H-31 + H-33 |
| `POST` con zona inválida o talle inválido responde 500 | H-21 / H-11 + H-33 |
| `POST` con `EGRESADOS2026` y sin fecha responde 500 | H-20 + H-33 |

### Decisiones e interpretaciones

- **Categorías.** El enunciado da diez categorías y no tiene "persistencia" ni "contrato entre capas":
  - H-26 y H-27 (transacciones) las puse en **efectos laterales**: una operación deja la base en un estado que no corresponde (guardado a medias o sin confirmar).
  - H-24 (nombre de parámetro) la puse en **code smell**, aunque es una violación del contrato.
  - Conviene preguntarle al profesor si prefiere otra categoría.
- **H-24 y la regla 1 del enunciado.** La regla dice "no cambies los nombres ni los parámetros de las funciones", pero el parámetro del código no es el de la especificación. Decidir si se corrige queda para la Parte 3.
- **Severidad.** Usé solo alta, media y baja, como pide el enunciado. *Alta*: pierde dinero o datos, expone información, o impide un flujo normal de compra. *Media*: rechaza o acepta mal un caso válido, o responde con un error incorrecto. *Baja*: casos raros o sin efecto visible hoy.

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

**Lo que detectó el linter por sí solo:**
- **H-19** (B008, dos veces).
- Parte de **H-25** (F401 y E711).
- El `except:` vacío de **H-05** (E722). Ruff marca el síntoma, pero no dice que se esté salteando un producto: eso salió del caso de prueba.

Los otros 37 hallazgos necesitaron casos de prueba o lectura. Como referencia, corrí también `ruff check pedidos.py api.py`: no encuentra nada, aunque ahí están la inyección SQL, el `commit` faltante y todos los 500.

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

**Resumen:** 40 hallazgos en tres archivos (25 en checkout.py, 6 en pedidos.py y 9 en api.py) · 18 de severidad alta, 16 media y 6 baja · 38 fallas demostradas ejecutando el código y 2 code smells sin efecto visible (H-25 y H-40).
