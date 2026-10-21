# Parte 1 — Casos de prueba de caja negra

Casos diseñados **solo con `ESPECIFICACION.md`**, antes de corregir el código.
Para cada regla, de R1 a R11, hay tres cosas:

1. **Particiones**: grupos de entradas que el sistema debería tratar igual (V = válida, I = inválida).
2. **Valores límite**: el borde exacto de la regla y un valor a cada lado.
3. **Casos**: al menos uno por partición, con la entrada concreta y el resultado esperado.

### Notación

- `D("…")` es `Decimal("…")`. Todos los importes esperados son `Decimal` con dos decimales.
- `it(p, t, c)` es el ítem `{"producto": p, "talle": t, "cantidad": c}`.
- `→ ERROR(CODIGO)` significa que se espera `CheckoutError` con ese `code`, y ninguna otra excepción (sección 1: "Nunca otro tipo de excepción").
- `VIGENTE` = `date(2026, 10, 1)`, una fecha en la que `EGRESADOS2026` está vigente.
- **Nivel**: dónde conviene probar el caso. *Unitario* = una función de `checkout.py`. *Integración* = `pedidos.py` + `checkout.py` + SQLite real. *E2E* = servidor HTTP real.
- **(interpretación)** marca un esperado que no sale de una frase explícita de la especificación sino de una lectura razonable de ella. Están juntas al final, en "Ambigüedades".

Precios del catálogo usados en las cuentas: buzo 24.999,90 · remera 11.999,50 · campera 47.999,99.

---

## R1 — Catálogo y precios

**Particiones**

| # | Partición | V/I |
|---|-----------|:---:|
| 1.1 | Producto del catálogo escrito exactamente (`buzo`, `remera`, `campera`) | V |
| 1.2 | Ítem que trae un precio propio | V (el precio se ignora) |
| 1.3 | Ítem con claves extra | V (se ignoran) |
| 1.4 | Producto que no está en el catálogo | I |
| 1.5 | Nombre del catálogo escrito distinto (mayúsculas, espacios) | I |
| 1.6 | Producto ausente, vacío o que no es texto | I |

**Valores límite**: R1 no tiene bordes numéricos. El borde es la escritura exacta: `"buzo"` es válido y `"Buzo"` o `" buzo"`, que difieren en un solo carácter, son inválidos.

**Casos**

| Partición | Entrada | Esperado | Nivel |
|-----------|---------|----------|-------|
| 1.1 | `calcular_subtotal([it("buzo","M",1)])` | `D("24999.90")` | unitario |
| 1.1 | `calcular_subtotal([it("remera","M",1)])` | `D("11999.50")` | unitario |
| 1.1 | `calcular_subtotal([it("campera","M",1)])` | `D("47999.99")` | unitario |
| 1.1 | `calcular_subtotal([it("buzo","M",1), it("remera","S",2), it("campera","XL",1)])` | `D("96998.89")` | unitario |
| 1.2 | `calcular_subtotal([{**it("buzo","M",2), "precio": 1}])` | `D("49999.80")` (no 2) | unitario |
| 1.2 | `calcular_subtotal([{**it("remera","M",1), "precio": 99999}])` | `D("11999.50")` | unitario |
| 1.2 | `guardar_pedido` con `{"precio": 1}` y después `obtener_pedido` | `precio_unitario == D("24999.90")` | integración |
| 1.3 | `calcular_subtotal([{**it("remera","M",1), "color": "rojo"}])` | `D("11999.50")`, sin error | unitario |
| 1.4 | `validar_item(it("gorra","M",1))` | `ERROR(PRODUCTO_INEXISTENTE)` | unitario |
| 1.4 | `calcular_total([it("buzo","M",1), it("gorra","M",1)], "CABA")` (el inexistente no se saltea) | `ERROR(PRODUCTO_INEXISTENTE)` | unitario |
| 1.5 | `validar_item(it("Buzo","M",1))`, `it("REMERA",…)`, `it(" campera",…)` | `ERROR(PRODUCTO_INEXISTENTE)` | unitario |
| 1.6 | `validar_item({"talle":"M","cantidad":1})`, `it("", "M", 1)`, `it(None, "M", 1)` | `ERROR(PRODUCTO_INEXISTENTE)` (interpretación) | unitario |
| 1.4 | `POST /api/v1/pedidos` con `"gorra"` | `422` y `code` `PRODUCTO_INEXISTENTE` | E2E |

---

## R2 — Talles

**Particiones**

| # | Partición | V/I |
|---|-----------|:---:|
| 2.1 | Uno de los seis talles, en mayúscula | V |
| 2.2 | Talle válido en minúscula o mezclado | V |
| 2.3 | Talle válido con espacios al principio o al final | V |
| 2.4 | Texto que no es uno de los seis talles | I |
| 2.5 | Texto vacío o solo espacios | I |
| 2.6 | Talle ausente o que no es texto | I |

**Valores límite**

| Borde | Justo adentro | Justo afuera |
|-------|---------------|--------------|
| Extremo chico de la lista | `XS` → válido | `XXS` → `TALLE_INVALIDO` |
| Extremo grande de la lista | `XXL` → válido | `XXXL` → `TALLE_INVALIDO` |
| Espacios | `" M "` (alrededor) → válido | `"X L"` (en el medio) → `TALLE_INVALIDO` |
| Largo del texto | `"S"` (1 carácter) → válido | `""` (0 caracteres) → `TALLE_INVALIDO` |

**Casos**

| Partición | Entrada | Esperado | Nivel |
|-----------|---------|----------|-------|
| 2.1 | `calcular_subtotal([it("remera", t, 2)])` para `t` en `XS, S, M, L, XL, XXL` | `D("23999.00")` cada uno | unitario |
| 2.2 | `calcular_subtotal([it("remera","m",1)])`, `"xxl"`, `"Xl"` | `D("11999.50")` | unitario |
| 2.3 | `calcular_subtotal([it("remera","  M ",1)])`, `" xl"` | `D("11999.50")` | unitario |
| 2.4 | `validar_item(it("buzo","XXXL",1))`, `"XXS"`, `"MM"`, `"X L"` | `ERROR(TALLE_INVALIDO)` | unitario |
| 2.5 | `validar_item(it("buzo","",1))`, `"   "` | `ERROR(TALLE_INVALIDO)` | unitario |
| 2.6 | `validar_item({"producto":"buzo","cantidad":1})`, `it("buzo", None, 1)`, `it("buzo", 42, 1)` | `ERROR(TALLE_INVALIDO)` (interpretación) | unitario |
| 2.2 | Mensaje del error con `"XXXL"` | `mensaje == "Talle inválido: 'XXXL'"` (ejemplo de la sección 7) | unitario |
| 2.3 | `guardar_pedido` con talle `" m "` y después `obtener_pedido` | `talle == "M"` | integración |

---

## R3 — Cantidad

**Particiones**

| # | Partición | V/I |
|---|-----------|:---:|
| 3.1 | Entero entre 1 y 10 | V |
| 3.2 | Entero menor que 1 | I |
| 3.3 | Entero mayor que 10 | I |
| 3.4 | Número que no es entero (decimal) | I |
| 3.5 | Otro tipo: texto, `None`, booleano, clave ausente | I |

**Valores límite**

| Borde | Afuera | Borde | Adentro |
|-------|--------|-------|---------|
| Mínimo | `0` → `CANTIDAD_INVALIDA` | `1` → válido | `2` → válido |
| Máximo | `11` → `CANTIDAD_INVALIDA` | `10` → válido | `9` → válido |

**Casos**

| Partición | Entrada | Esperado | Nivel |
|-----------|---------|----------|-------|
| 3.1 | `calcular_subtotal([it("remera","M",1)])` | `D("11999.50")` | unitario |
| 3.1 | `calcular_subtotal([it("remera","M",2)])` | `D("23999.00")` | unitario |
| 3.1 | `calcular_subtotal([it("remera","M",9)])` | `D("107995.50")` | unitario |
| 3.1 | `calcular_subtotal([it("remera","M",10)])` | `D("119995.00")` | unitario |
| 3.2 | `validar_item(it("buzo","M",0))`, `-1` | `ERROR(CANTIDAD_INVALIDA)` | unitario |
| 3.3 | `validar_item(it("buzo","M",11))`, `100` | `ERROR(CANTIDAD_INVALIDA)` | unitario |
| 3.4 | `validar_item(it("buzo","M",2.5))` | `ERROR(CANTIDAD_INVALIDA)` | unitario |
| 3.4 | `validar_item(it("buzo","M",1.0))` | `ERROR(CANTIDAD_INVALIDA)` (interpretación: es `float`, no entero) | unitario |
| 3.5 | `validar_item(it("buzo","M","2"))`, `None`, `{"producto":"buzo","talle":"M"}` | `ERROR(CANTIDAD_INVALIDA)` (no `TypeError` ni `KeyError`) | unitario |
| 3.5 | `validar_item(it("buzo","M",True))` | `ERROR(CANTIDAD_INVALIDA)` (interpretación: en Python `True == 1`, pero no es una cantidad) | unitario |

---

## R4 — Carrito

**Particiones**

| # | Partición | V/I |
|---|-----------|:---:|
| 4.1 | Lista con uno o más ítems | V |
| 4.2 | Lista vacía | I |
| 4.3 | Algo que no es una lista (`None`) | I |
| 4.4 | Cualquier llamada válida o inválida: el carrito recibido queda igual | V (efecto lateral prohibido) |

**Valores límite**: `0` ítems → `CARRITO_VACIO`; `1` ítem → válido; `2` ítems → válido.

**Casos**

| Partición | Entrada | Esperado | Nivel |
|-----------|---------|----------|-------|
| 4.1 | `calcular_total([it("remera","M",1)], "CABA")` | `total == D("14499.50")` | unitario |
| 4.2 | `calcular_total([], "CABA")` | `ERROR(CARRITO_VACIO)` | unitario |
| 4.3 | `calcular_total(None, "CABA")` | `ERROR(CARRITO_VACIO)` (interpretación) | unitario |
| 4.4 | Carrito `[it("buzo"," m ",1), {**it("remera","xl",2), "precio": 1, "color": "rojo"}]`, copiado con `deepcopy`; llamar a `calcular_total(carrito, "CABA")` | `carrito == copia` | unitario |
| 4.4 | `validar_item(it("buzo"," s ",1))` | el ítem sigue con `" s "` | unitario |
| 4.4 | Carrito con un ítem inválido, `calcular_total` lanza error | `carrito == copia` aunque falle | unitario |
| 4.2 | `POST` con `"carrito": []` | `422` y `CARRITO_VACIO` (interpretación: es una lista, así que no es "otro tipo") | E2E |

---

## R5 — Descuento por cantidad

**Particiones**

| # | Partición | V/I |
|---|-----------|:---:|
| 5.1 | Menos de 5 prendas en total: sin descuento | V |
| 5.2 | 5 o más prendas: 10% del subtotal | V |
| 5.3 | Las prendas se suman entre todos los ítems | V |

**Valores límite**: `4` prendas → 0; `5` prendas → 10%; `6` prendas → 10%.

**Casos**

| Partición | Entrada | Esperado | Nivel |
|-----------|---------|----------|-------|
| 5.1 | `calcular_descuento(D("100000.00"), 4, None, VIGENTE)` | `D("0.00")` | unitario |
| 5.2 | `calcular_descuento(D("100000.00"), 5, None, VIGENTE)` | `D("10000.00")` | unitario |
| 5.2 | `calcular_descuento(D("100000.00"), 6, None, VIGENTE)` | `D("10000.00")` | unitario |
| 5.3 | `calcular_total([it("buzo","M",2), it("remera","S",3)], "CABA")` (2 + 3 = 5) | subtotal `D("85998.30")`, descuento `D("8599.83")`, envío `D("0.00")`, total `D("77398.47")` | unitario |
| 5.2 | `calcular_total([it("remera","M",5)], "GBA")` | subtotal `D("59997.50")`, descuento `D("5999.75")`, envío `D("4000.00")`, total `D("57997.75")` | unitario |

---

## R6 — Cupones

**Particiones**

| # | Partición | V/I |
|---|-----------|:---:|
| 6.1 | Sin cupón: `None`, `""` o solo espacios | V (descuento 0, no es error) |
| 6.2 | `EGRESADOS2026` hasta el 30/11/2026 inclusive | V (15%) |
| 6.3 | `EGRESADOS2026` después del 30/11/2026 | I → `CUPON_VENCIDO` |
| 6.4 | `BIENVENIDA` con subtotal de 20.000 o más | V ($ 3.000) |
| 6.5 | `BIENVENIDA` con subtotal menor a 20.000 | I → `CUPON_MINIMO_NO_ALCANZADO` |
| 6.6 | Cupón válido en minúscula o con espacios alrededor | V |
| 6.7 | Cualquier otro código | I → `CUPON_INVALIDO` |
| 6.8 | Cupón que no es texto | I → `CUPON_INVALIDO` (interpretación) |
| 6.9 | Cupón y descuento por cantidad: se aplica el mayor, no la suma | V |
| 6.10 | Sin `fecha` (o `fecha=None`): se usa la del día de la llamada | V |

**Valores límite**

| Borde | Afuera | Borde | Adentro |
|-------|--------|-------|---------|
| Vigencia de `EGRESADOS2026` | `2026-12-01` → `CUPON_VENCIDO` | `2026-11-30` → 15% | `2026-11-29` → 15% |
| Mínimo de `BIENVENIDA` | `19999.99` → `CUPON_MINIMO_NO_ALCANZADO` | `20000.00` → 3.000 | `20000.01` → 3.000 |
| Empate entre `BIENVENIDA` y 10% (con 5 prendas) | subtotal `29999.90`: 10% = 2.999,99 → gana `BIENVENIDA` (3.000) | subtotal `30000.00`: los dos dan 3.000 | subtotal `30000.10`: 10% = 3.000,01 → gana el 10% |

**Casos**

| Partición | Entrada | Esperado | Nivel |
|-----------|---------|----------|-------|
| 6.1 | `calcular_descuento(D("30000.00"), 1, c, VIGENTE)` con `c` en `None`, `""`, `"   "` | `D("0.00")`, sin error | unitario |
| 6.2 | `calcular_descuento(D("100000.00"), 1, "EGRESADOS2026", VIGENTE)` | `D("15000.00")` | unitario |
| 6.2 | ídem con `date(2026, 11, 30)` | `D("15000.00")` | unitario |
| 6.3 | ídem con `date(2026, 12, 1)` | `ERROR(CUPON_VENCIDO)` | unitario |
| 6.4 | `calcular_descuento(D("20000.00"), 1, "BIENVENIDA", VIGENTE)` | `D("3000.00")` | unitario |
| 6.5 | `calcular_descuento(D("19999.99"), 1, "BIENVENIDA", VIGENTE)` | `ERROR(CUPON_MINIMO_NO_ALCANZADO)` | unitario |
| 6.5 | `calcular_total([it("remera","M",1)], "CABA", " bienvenida ", VIGENTE)` (subtotal 11.999,50) | `ERROR(CUPON_MINIMO_NO_ALCANZADO)` | unitario |
| 6.6 | `"egresados2026"`, `"  EGRESADOS2026 "`, `"Egresados2026"` con subtotal 100.000 | `D("15000.00")` | unitario |
| 6.7 | `calcular_descuento(D("100000.00"), 1, c, VIGENTE)` con `c` en `"NAVIDAD"`, `"TEST100"`, `"ADMIN"` | `ERROR(CUPON_INVALIDO)` | unitario |
| 6.7 | Código inválido aunque haya descuento por cantidad: `calcular_descuento(D("100000.00"), 6, "NAVIDAD", VIGENTE)` | `ERROR(CUPON_INVALIDO)` | unitario |
| 6.8 | `calcular_descuento(D("100000.00"), 1, 123, VIGENTE)` | `ERROR(CUPON_INVALIDO)` (interpretación) | unitario |
| 6.9 | `calcular_descuento(D("100000.00"), 6, "EGRESADOS2026", VIGENTE)`: 15.000 contra 10.000 | `D("15000.00")` (no 25.000) | unitario |
| 6.9 | `calcular_descuento(D("100000.00"), 6, "BIENVENIDA", VIGENTE)`: 3.000 contra 10.000 | `D("10000.00")` | unitario |
| 6.9 | `calcular_descuento(D("25000.00"), 5, "BIENVENIDA", VIGENTE)`: 3.000 contra 2.500 | `D("3000.00")` | unitario |
| 6.9 | `calcular_descuento(D("29999.90"), 5, "BIENVENIDA", VIGENTE)`: 3.000 contra 2.999,99 | `D("3000.00")` | unitario |
| 6.9 | `calcular_descuento(D("30000.00"), 5, "BIENVENIDA", VIGENTE)`: empate | `D("3000.00")` | unitario |
| 6.9 | `calcular_descuento(D("30000.10"), 5, "BIENVENIDA", VIGENTE)`: 3000.01 contra 3.000 | `D("3000.01")` | unitario |
| 6.10 | Sin `fecha`, con "hoy" simulado en `2026-12-01` y cupón `EGRESADOS2026` | `ERROR(CUPON_VENCIDO)` | unitario |
| 6.10 | `fecha=None` explícito, con "hoy" simulado en `2026-11-30` | `D("15000.00")`, sin `TypeError` | unitario |
| — | El descuento nunca supera el subtotal: `calcular_total([it("buzo","M",1)], "RETIRO", "BIENVENIDA", VIGENTE)` | descuento `D("3000.00")` ≤ subtotal `D("24999.90")`; total `D("21999.90")` | unitario |
| 6.1 | `guardar_pedido` con cupón `""` o `"   "` | `cupon is None` en la base | integración |
| 6.6 | `guardar_pedido` con `" egresados2026 "` | `cupon == "EGRESADOS2026"` en la base | integración |
| 6.2 / 6.3 | `POST` con `"fecha": "2026-11-30"` / `"2026-12-01"` | `201` / `422 CUPON_VENCIDO` | E2E |

---

## R7 — Dinero y redondeo

**Particiones**

| # | Partición | V/I |
|---|-----------|:---:|
| 7.1 | Todos los importes devueltos son `Decimal` (nunca `float`) | V |
| 7.2 | Descuento porcentual con medio centavo exacto: redondea hacia arriba | V |
| 7.3 | Fracción menor a medio centavo: redondea hacia abajo | V |
| 7.4 | Fracción mayor a medio centavo: redondea hacia arriba | V |
| 7.5 | Importe que no necesita redondeo | V |

**Valores límite**: la fracción del tercer decimal alrededor de 5. Con `0,xx4…` baja, con `0,xx5` exacto sube y con `0,xx6…` sube.

**Casos**

| Partición | Entrada | Esperado | Nivel |
|-----------|---------|----------|-------|
| 7.1 | `calcular_total([it("buzo","M",2)], "CABA")` | las 4 claves son de tipo `Decimal` | unitario |
| 7.2 | `calcular_descuento(D("11999.50"), 1, "EGRESADOS2026", VIGENTE)`: 1.799,925 | `D("1799.93")` (ejemplo de la especificación) | unitario |
| 7.2 | `calcular_descuento(D("24999.90"), 1, "EGRESADOS2026", VIGENTE)`: 3.749,985 | `D("3749.99")` | unitario |
| 7.2 | `calcular_descuento(D("99999.95"), 5, None, VIGENTE)`: 10% = 9.999,995 | `D("10000.00")` | unitario |
| 7.3 | `calcular_descuento(D("59999.49"), 1, "EGRESADOS2026", VIGENTE)`: 8.999,9235 | `D("8999.92")` | unitario |
| 7.4 | `calcular_descuento(D("47999.99"), 1, "EGRESADOS2026", VIGENTE)`: 7.199,9985 | `D("7200.00")` | unitario |
| 7.5 | `calcular_subtotal([it("remera","M",3)])` | exactamente `D("35998.50")`, de tipo `Decimal` | unitario |
| 7.1 | Texto de cada importe de `calcular_total([it("remera","M",1)], "RETIRO", "EGRESADOS2026", VIGENTE)` | `"11999.50"`, `"1799.93"`, `"0.00"`, `"10199.57"` (interpretación: dos decimales, como en los ejemplos de la especificación) | unitario |
| 7.1 | Montos de `obtener_pedido` | `Decimal` con el mismo texto que calculó `checkout` (`"1799.93"`, no `"1799.930000…"`) | integración |
| 7.1 | Montos en el JSON de `POST` y `GET` | strings (`"1799.93"`), nunca números JSON | E2E |

---

## R8 — Envío

**Particiones**

| # | Partición | V/I |
|---|-----------|:---:|
| 8.1 | Zona válida y base (subtotal con descuento) menor a 60.000: se cobra la tarifa | V |
| 8.2 | Zona válida y base de 60.000 o más: envío gratis | V |
| 8.3 | Zona válida en minúscula o con espacios | V |
| 8.4 | Zona que no existe | I → `ZONA_INVALIDA` |
| 8.5 | Zona vacía o que no es texto | I → `ZONA_INVALIDA` (interpretación) |
| 8.6 | El envío gratis se decide con el subtotal **ya descontado**, no con el subtotal | V |

**Valores límite**: base `59999.99` → se paga; `60000.00` → gratis; `60000.01` → gratis.

**Casos**

| Partición | Entrada | Esperado | Nivel |
|-----------|---------|----------|-------|
| 8.1 | `calcular_envio(D("59999.99"), "CABA")` | `D("2500.00")` | unitario |
| 8.1 | `calcular_envio(D("59999.99"), "GBA")` | `D("4000.00")` | unitario |
| 8.1 | `calcular_envio(D("59999.99"), "INTERIOR")` | `D("6500.00")` | unitario |
| 8.1 | `calcular_envio(D("59999.99"), "RETIRO")` | `D("0.00")` | unitario |
| 8.2 | `calcular_envio(D("60000.00"), "INTERIOR")` | `D("0.00")` | unitario |
| 8.2 | `calcular_envio(D("60000.01"), "INTERIOR")` | `D("0.00")` | unitario |
| 8.3 | `calcular_envio(D("1000.00"), z)` con `z` en `"gba"`, `" GBA "`, `"Gba"` | `D("4000.00")` | unitario |
| 8.4 | `calcular_envio(D("1000.00"), "MARTE")` | `ERROR(ZONA_INVALIDA)` | unitario |
| 8.4 | `calcular_envio(D("100000.00"), "MARTE")` (sería gratis, pero la zona no existe) | `ERROR(ZONA_INVALIDA)` | unitario |
| 8.5 | `calcular_envio(D("1000.00"), z)` con `z` en `""`, `"   "`, `None`, `5` | `ERROR(ZONA_INVALIDA)` | unitario |
| 8.6 | `calcular_total([it("buzo","M",2), it("remera","M",1)], "CABA", "EGRESADOS2026", VIGENTE)`: subtotal 61.999,30 pero base 52.699,40 | subtotal `D("61999.30")`, descuento `D("9299.90")`, envío `D("2500.00")`, total `D("55199.40")` | unitario |
| 8.6 | `calcular_total([it("remera","M",6)], "INTERIOR")`: base 71.997 − 7.199,70 = 64.797,30 | envío `D("0.00")`, total `D("64797.30")` | unitario |
| 8.6 | `calcular_envio(subtotal_con_descuento=D("1000.00"), zona="GBA")` (nombres de parámetro del contrato) | `D("4000.00")` | unitario |
| 8.3 | `guardar_pedido` con zona `" caba "` | `zona == "CABA"` en la base | integración |
| 8.4 | `POST` con `"zona": "MARTE"` | `422 ZONA_INVALIDA` | E2E |

---

## R9 — Total

**Particiones**

| # | Partición | V/I |
|---|-----------|:---:|
| 9.1 | Sin descuento y con envío pago | V |
| 9.2 | Con descuento porcentual y envío pago | V |
| 9.3 | Con descuento fijo | V |
| 9.4 | Con envío gratis | V |
| 9.5 | Retiro en el colegio (envío 0 por zona) | V |

**Valores límite**: no tiene bordes propios; hereda los de R5, R6 y R8. Para que el test distinga `subtotal − descuento + envío` de otras combinaciones, conviene que descuento y envío sean **los dos distintos de cero**.

**Casos** (formato: subtotal / descuento / envío / **total**)

| Partición | Entrada | Esperado | Nivel |
|-----------|---------|----------|-------|
| 9.1 | `calcular_total([it("buzo","M",2)], "CABA")` (ejemplo de la sección 5) | `D("49999.80")` / `D("0.00")` / `D("2500.00")` / **`D("52499.80")`** | unitario |
| 9.2 | `calcular_total([it("remera","M",1)], "CABA", "EGRESADOS2026", VIGENTE)` | `D("11999.50")` / `D("1799.93")` / `D("2500.00")` / **`D("12699.57")`** | unitario |
| 9.3 | `calcular_total([it("buzo","L",1)], "GBA", "BIENVENIDA", VIGENTE)` | `D("24999.90")` / `D("3000.00")` / `D("4000.00")` / **`D("25999.90")`** | unitario |
| 9.4 | `calcular_total([it("campera","S",2)], "GBA")` | `D("95999.98")` / `D("0.00")` / `D("0.00")` / **`D("95999.98")`** | unitario |
| 9.5 | `calcular_total([it("remera","M",1)], "RETIRO")` | `D("11999.50")` / `D("0.00")` / `D("0.00")` / **`D("11999.50")`** | unitario |
| — | Claves del resultado | exactamente `{"subtotal", "descuento", "envio", "total"}` | unitario |

---

## Orden de validación (sección 3)

Cuando hay más de un problema, se informa el primero en este orden: carrito vacío → cada ítem en orden (producto, talle, cantidad) → cupón → zona.

| Situación | Entrada de `calcular_total` | Esperado | Nivel |
|-----------|-----------------------------|----------|-------|
| Carrito vacío antes que todo | `([], "MARTE", "NAVIDAD")` | `CARRITO_VACIO` | unitario |
| Producto antes que talle y cantidad | `([it("gorra","XXXL",0)], "MARTE", "NAVIDAD")` | `PRODUCTO_INEXISTENTE` | unitario |
| Talle antes que cantidad | `([it("buzo","XXXL",0)], "MARTE", "NAVIDAD")` | `TALLE_INVALIDO` | unitario |
| Cantidad antes que cupón y zona | `([it("buzo","M",0)], "MARTE", "NAVIDAD")` | `CANTIDAD_INVALIDA` | unitario |
| Ítems en el orden en que aparecen | `([it("buzo","M",1), it("buzo","XXXL",1), it("gorra","M",1)], "CABA")` | `TALLE_INVALIDO` (el 2.º ítem, no el 3.º) | unitario |
| Cupón antes que zona | `([it("buzo","M",1)], "MARTE", "NAVIDAD", VIGENTE)` | `CUPON_INVALIDO` | unitario |
| Cupón vencido antes que zona | `([it("buzo","M",1)], "MARTE", "EGRESADOS2026", date(2026,12,1))` | `CUPON_VENCIDO` | unitario |
| Zona al final | `([it("buzo","M",1)], "MARTE")` | `ZONA_INVALIDA` | unitario |

---

## R10 — Persistencia (`pedidos.py`)

Todos los casos usan **un archivo SQLite nuevo por test** (no `:memory:`). Lo guardado se verifica con **otra conexión**, como pide la especificación: "cualquier otra conexión a la misma base".

**Particiones** (una por punto de R10)

| # | Punto de R10 | V/I |
|---|--------------|:---:|
| 10.1 | `calcular_total` lanza `CheckoutError` → se propaga y no queda nada guardado | I |
| 10.2 | Al terminar `guardar_pedido`, otra conexión ve el pedido completo con sus ítems | V |
| 10.3 | Los montos recuperados son idénticos a los calculados (`Decimal`, sin pérdida) | V |
| 10.4 | `precio_unitario` es el del catálogo, nunca el del cliente | V |
| 10.5 | Datos normalizados: email en minúscula sin espacios; zona, talle y cupón en mayúscula sin espacios; cupón vacío → `None` | V |
| 10.6 | `obtener_pedido` de un id que no existe → `None` | I |
| 10.7a | `pedidos_de` no distingue mayúsculas ni espacios en el email | V |
| 10.7b | `pedidos_de` devuelve del más reciente al más antiguo | V |
| 10.7c | Ningún valor de email altera la consulta | I (entrada maliciosa) |

**Valores límite**

| Borde | Casos |
|-------|-------|
| Ids | id del último pedido guardado → lo devuelve; ese id + 1 → `None`; `0` y `-1` → `None`; un id fuera del rango de enteros de SQLite (`2**63`) → `None` (interpretación: "no existe") |
| Cantidad de pedidos de un email | 0 → `[]`; 1 → lista de uno; 3 → los tres, en orden descendente |
| Momento del error | error detectado en un ítem; en el cupón; en la zona (el último paso de la validación) |

**Casos**

| Punto | Entrada | Esperado | Nivel |
|-------|---------|----------|-------|
| 10.1 | `guardar_pedido(con, "ana@mail.com", [it("buzo","XXXL",1)], "CABA")` | se propaga `CheckoutError` con `TALLE_INVALIDO`; 0 filas en `pedidos` y en `items`, vistas desde otra conexión | integración |
| 10.1 | Igual, con cupón `"NAVIDAD"` o zona `"MARTE"` (errores que se detectan después de los ítems) | `CUPON_INVALIDO` / `ZONA_INVALIDA`; 0 filas | integración |
| 10.1 | Un pedido válido guardado y después un intento con error | sigue habiendo exactamente 1 pedido, sin cambios | integración |
| 10.1 | Intento con error y después un pedido válido por la **misma** conexión | queda exactamente 1 pedido (el válido): el intento fallido no se confirma con él | integración |
| 10.2 | `guardar_pedido(...)` y `obtener_pedido` desde **otra** conexión | el pedido con sus montos y todos sus ítems | integración |
| 10.2 | `guardar_pedido(...)`, cerrar la conexión y abrir otra | el pedido sigue completo | integración |
| 10.3 | `guardar_pedido(con, "ana@mail.com", [it("remera","M",1)], "CABA", "EGRESADOS2026", VIGENTE)` | montos `== calcular_total(...)`; `D("11999.50")`, `D("1799.93")`, `D("2500.00")`, `D("12699.57")`; tipo `Decimal`; `str(descuento) == "1799.93"` | integración |
| 10.3 | El mismo pedido, formato completo | igual al ejemplo de la sección 6: `id`, `email`, `zona`, `cupon`, cuatro montos, `items` con `precio_unitario` | integración |
| 10.4 | Carrito `[{**it("buzo","M",1), "precio": 1}]` | `precio_unitario == D("24999.90")` y `subtotal == D("24999.90")` | integración |
| 10.5 | email `"  Ana@Mail.COM "`, zona `" caba "`, talles `" m "` y `"xl"`, cupón `" egresados2026 "` | `"ana@mail.com"`, `"CABA"`, `["M", "XL"]`, `"EGRESADOS2026"` | integración |
| 10.5 | cupón `None`, `""`, `"   "` | `cupon is None` | integración |
| 10.6 | `obtener_pedido(con, 999)` con la base vacía o con un solo pedido | `None` | integración |
| 10.7a | guardar con `"Ana@Mail.com"`, buscar `"  ANA@MAIL.COM "` | la lista con ese pedido | integración |
| 10.7a | pedidos de `ana@…` y de `beto@…` | `pedidos_de(con, "ana@mail.com")` devuelve solo los de Ana | integración |
| 10.7a | email sin pedidos | `[]` | integración |
| 10.7b | tres pedidos de Ana, guardados en orden | ids en orden descendente | integración |
| 10.7c | `pedidos_de(con, "x' OR '1'='1")` habiendo pedidos de otros | `[]` | integración |
| 10.7c | un email legítimo con apóstrofo, `"o'brien@mail.com"` | sus pedidos, sin error | integración |
| — | Sin `fecha`: `guardar_pedido(..., "EGRESADOS2026")` con "hoy" simulado en `2026-11-30` | descuento `D("1799.93")` (aplica R6) | integración |

---

## R11 — API HTTP (`api.py`)

Servidor real (`crear_servidor(archivo_temporal, 0)`), requests HTTP reales y base en un archivo. Todos los errores tienen el formato `{"error": {"code": …, "message": …}}`.

**Particiones**

| # | Partición | V/I |
|---|-----------|:---:|
| 11.1 | `POST /api/v1/pedidos` con datos válidos, sin `cupon` ni `fecha` | V → `201` |
| 11.2 | `POST` con `cupon` y `fecha` válidos (texto `AAAA-MM-DD`) | V → `201` |
| 11.3 | `GET /api/v1/pedidos/{id}` de un pedido que existe | V → `200` |
| 11.4 | Error de negocio (cualquier `CheckoutError`) | I → `422` + `code` del error |
| 11.5 | Cuerpo que no es JSON válido | I → `400 JSON_INVALIDO` |
| 11.6 | Falta `email`, `zona` o `carrito`, o tienen otro tipo | I → `400 DATOS_INCOMPLETOS` |
| 11.7 | `fecha` que no tiene formato `AAAA-MM-DD` | I → `400 FECHA_INVALIDA` |
| 11.8 | `GET` de un pedido que no existe | I → `404 PEDIDO_INEXISTENTE` |
| 11.9 | Ruta que no existe | I → `404 RUTA_INEXISTENTE` |
| 11.10 | Ningún error devuelve `500` | — |

**Valores límite**

| Borde | Casos |
|-------|-------|
| Fecha | `"2026-02-28"` → válida; `"2026-02-29"` → `FECHA_INVALIDA` (2026 no es bisiesto); `"2026-12-31"` válida y `"2026-13-01"` inválida |
| Formato de fecha | `"2026-11-30"` válido; `"20261130"` (sin guiones), `"2026-11-30T10:00"` (con hora) y `"30/11/2026"` → `FECHA_INVALIDA` |
| Id | el id recién creado → `200`; ese id + 1 → `404 PEDIDO_INEXISTENTE` |
| Montos en el JSON | siempre texto con dos decimales: `"0.00"`, no `0` ni `0.0` |

**Casos**

| Partición | Request | Esperado | Nivel |
|-----------|---------|----------|-------|
| 11.1 + 11.3 | `POST` `{"email":"  Ana@Mail.COM ","zona":" caba ","carrito":[{"producto":"remera","talle":" m ","cantidad":1,"precio":1},{"producto":"buzo","talle":"L","cantidad":1}]}` y después `GET` del id | `201` `{"id": <int>, "subtotal":"36999.40","descuento":"0.00","envio":"2500.00","total":"39499.40"}`; `GET` `200` con `email` `"ana@mail.com"`, `zona` `"CABA"`, `cupon` `null`, los mismos montos como texto y dos ítems con `precio_unitario` `"11999.50"` y `"24999.90"` | E2E |
| 11.2 | `POST` con remera, `"cupon":"EGRESADOS2026"`, `"fecha":"2026-11-30"` (ejemplo de la sección 7) | `201` `{"id":…, "subtotal":"11999.50","descuento":"1799.93","envio":"2500.00","total":"12699.57"}` | E2E |
| 11.4 | `POST` con talle `"XXXL"` | `422` `{"error":{"code":"TALLE_INVALIDO","message":…}}` | E2E |
| 11.4 | `POST` con `"fecha":"2026-12-01"` y `EGRESADOS2026` | `422 CUPON_VENCIDO` | E2E |
| 11.4 | `POST` con `"zona":"MARTE"` / `"cupon":"NAVIDAD"` / `"carrito":[]` | `422` con `ZONA_INVALIDA` / `CUPON_INVALIDO` / `CARRITO_VACIO` | E2E |
| 11.5 | `POST` con cuerpo `{nojson`, cuerpo vacío o bytes que no son UTF-8 | `400 JSON_INVALIDO` | E2E |
| 11.6 | `POST` sin `email`; sin `zona`; sin `carrito` | `400 DATOS_INCOMPLETOS` | E2E |
| 11.6 | `POST` con `"email": 5`, `"zona": null`, `"carrito": "remera"` o con el cuerpo `[ … ]` (lista en vez de objeto) | `400 DATOS_INCOMPLETOS` | E2E |
| 11.7 | `POST` con `"fecha"` en `"30/11/2026"`, `"2026-02-29"`, `"2026-13-01"`, `"20261130"`, `"2026-11-30T10:00"` o el número `20261130` | `400 FECHA_INVALIDA` | E2E |
| 11.8 | `GET /api/v1/pedidos/999` | `404 PEDIDO_INEXISTENTE` | E2E |
| 11.9 | `GET /api/v1/otra`, `POST /api/v1/otra`, `GET /api/v1/pedidos/abc` | `404 RUTA_INEXISTENTE` | E2E |
| 11.4–11.7 | Después de cada `POST` con error, `GET /api/v1/pedidos/1` | `404`: el intento fallido no dejó nada guardado | E2E |
| 11.10 | Todos los casos de error anteriores | ninguno responde `500` | E2E |

---

## Ambigüedades (esperados por interpretación)

| Caso | Interpretación elegida | Por qué |
|------|------------------------|---------|
| Producto, talle o cantidad ausentes, `None` o de otro tipo | El `code` de la regla correspondiente (`PRODUCTO_INEXISTENTE`, `TALLE_INVALIDO`, `CANTIDAD_INVALIDA`) | Sección 1: "Ante cualquier dato inválido, las funciones lanzan `CheckoutError` … Nunca otro tipo de excepción" |
| Cantidad `1.0` o `True` | `CANTIDAD_INVALIDA` | R3 pide un "número entero"; `1.0` es `float` y `True` es un booleano |
| Carrito `None` | `CARRITO_VACIO` | Es el único código de la sección 4 que habla del carrito |
| Cupón que no es texto (`123`) | `CUPON_INVALIDO` | No es un código que exista |
| Zona vacía o que no es texto | `ZONA_INVALIDA` | No es una zona que exista |
| Importes con dos decimales (`"0.00"`, `"2500.00"`) | Siempre dos decimales | Los ejemplos de las secciones 5, 6 y 7 los muestran así |
| Id fuera del rango de enteros de SQLite | `obtener_pedido` → `None`; la API → `404` | Ese pedido no existe y "un error nunca puede devolver 500" |
| `POST` con `"carrito": []` | `422 CARRITO_VACIO`, no `400` | El carrito existe y es una lista; el problema es de negocio |
| `"email": ""` o `"   "` en el `POST` | **A consultar** | No está claro si un email vacío es "falta email" (`400`) o un dato que se guarda |
| `"cupon": null` o `"fecha": null` en el JSON | Equivalen a no mandarlos → `201` | Son opcionales y en Python llegan como `None` |
| Varios errores `400` a la vez (por ejemplo, sin email y con fecha inválida) | **A consultar** | La especificación no define el orden entre ellos |
