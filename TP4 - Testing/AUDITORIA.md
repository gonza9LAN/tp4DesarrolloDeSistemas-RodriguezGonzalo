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
