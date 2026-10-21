from datetime import date
from decimal import Decimal

import pytest

import checkout
from checkout import (
    CheckoutError,
    calcular_descuento,
    calcular_envio,
    calcular_subtotal,
    calcular_total,
    validar_item,
)

HOY_VIGENTE = date(2026, 10, 1)


def item(producto="buzo", talle="M", cantidad=1, **extra):
    return {"producto": producto, "talle": talle, "cantidad": cantidad, **extra}


def codigo_de_error(funcion, *args):
    with pytest.raises(CheckoutError) as error:
        funcion(*args)
    return error.value.code


def simular_hoy(monkeypatch, dia):
    class FechaSimulada(date):
        @classmethod
        def today(cls):
            return dia

    monkeypatch.setattr(checkout, "date", FechaSimulada)


def test_cantidad_cero_es_invalida():
    assert codigo_de_error(validar_item, item(cantidad=0)) == "CANTIDAD_INVALIDA"


# R1 — Catálogo y precios


def test_validar_item_rechaza_un_producto_que_no_esta_en_el_catalogo():
    gorra = item(producto="gorra")

    codigo = codigo_de_error(validar_item, gorra)

    assert codigo == "PRODUCTO_INEXISTENTE"


def test_un_producto_inexistente_en_el_carrito_no_se_saltea():
    carrito = [item(producto="buzo"), item(producto="gorra")]

    codigo = codigo_de_error(calcular_total, carrito, "CABA")

    assert codigo == "PRODUCTO_INEXISTENTE"


def test_el_producto_se_valida_antes_que_el_talle():
    carrito = [item(producto="gorra", talle="XXXL")]

    codigo = codigo_de_error(calcular_total, carrito, "CABA")

    assert codigo == "PRODUCTO_INEXISTENTE"


def test_el_precio_sale_del_catalogo_aunque_el_item_traiga_otro():
    carrito = [item(producto="buzo", cantidad=2, precio=1)]

    subtotal = calcular_subtotal(carrito)

    assert subtotal == Decimal("49999.80")


# R7 — Dinero y redondeo


def test_el_ejemplo_de_la_especificacion_devuelve_importes_decimal():
    carrito = [item(producto="buzo", talle="M", cantidad=2)]

    resultado = calcular_total(carrito, "CABA")

    assert resultado == {
        "subtotal": Decimal("49999.80"),
        "descuento": Decimal("0.00"),
        "envio": Decimal("2500.00"),
        "total": Decimal("52499.80"),
    }
    assert all(type(importe) is Decimal for importe in resultado.values())


def test_el_medio_centavo_redondea_hacia_arriba():
    subtotal = Decimal("11999.50")

    descuento = calcular_descuento(subtotal, 1, "EGRESADOS2026", HOY_VIGENTE)

    assert descuento == Decimal("1799.93")


# R6 — Cupones


def test_cupon_y_cantidad_no_se_suman_y_gana_el_cupon_si_es_mayor():
    subtotal = Decimal("100000.00")

    descuento = calcular_descuento(subtotal, 6, "EGRESADOS2026", HOY_VIGENTE)

    assert descuento == Decimal("15000.00")


def test_cupon_y_cantidad_no_se_suman_y_gana_la_cantidad_si_es_mayor():
    subtotal = Decimal("100000.00")

    descuento = calcular_descuento(subtotal, 6, "BIENVENIDA", HOY_VIGENTE)

    assert descuento == Decimal("10000.00")


def test_cinco_prendas_ya_tienen_descuento_por_cantidad():
    subtotal = Decimal("100000.00")

    descuento = calcular_descuento(subtotal, 5, None, HOY_VIGENTE)

    assert descuento == Decimal("10000.00")


def test_el_cupon_no_distingue_mayusculas_ni_espacios():
    subtotal = Decimal("100000.00")

    descuento = calcular_descuento(subtotal, 1, " egresados2026 ", HOY_VIGENTE)

    assert descuento == Decimal("15000.00")


@pytest.mark.parametrize("cupon", ["", "   "])
def test_un_cupon_vacio_equivale_a_no_usar_cupon(cupon):
    subtotal = Decimal("100000.00")

    descuento = calcular_descuento(subtotal, 1, cupon, HOY_VIGENTE)

    assert descuento == Decimal("0.00")


def test_un_cupon_que_no_es_texto_es_invalido():
    subtotal = Decimal("100000.00")

    codigo = codigo_de_error(calcular_descuento, subtotal, 1, 123, HOY_VIGENTE)

    assert codigo == "CUPON_INVALIDO"


def test_egresados2026_es_valido_el_30_de_noviembre():
    ultimo_dia = date(2026, 11, 30)

    descuento = calcular_descuento(Decimal("100000.00"), 1, "EGRESADOS2026", ultimo_dia)

    assert descuento == Decimal("15000.00")


def test_bienvenida_descuenta_tres_mil_con_el_minimo_exacto():
    subtotal = Decimal("20000.00")

    descuento = calcular_descuento(subtotal, 1, "BIENVENIDA", HOY_VIGENTE)

    assert descuento == Decimal("3000.00")


def test_bienvenida_con_un_centavo_menos_del_minimo_no_se_aplica():
    subtotal = Decimal("19999.99")

    codigo = codigo_de_error(calcular_descuento, subtotal, 1, "BIENVENIDA", HOY_VIGENTE)

    assert codigo == "CUPON_MINIMO_NO_ALCANZADO"


def test_solo_existen_los_cupones_egresados2026_y_bienvenida():
    subtotal = Decimal("100000.00")

    codigo = codigo_de_error(calcular_descuento, subtotal, 1, "DEBUG100", HOY_VIGENTE)

    assert codigo == "CUPON_INVALIDO"


def test_sin_fecha_se_usa_el_dia_de_la_llamada(monkeypatch):
    simular_hoy(monkeypatch, date(2026, 12, 1))
    carrito = [item(producto="remera")]

    codigo = codigo_de_error(calcular_total, carrito, "CABA", "EGRESADOS2026")

    assert codigo == "CUPON_VENCIDO"


def test_fecha_none_equivale_al_dia_de_la_llamada(monkeypatch):
    simular_hoy(monkeypatch, date(2026, 11, 30))

    descuento = calcular_descuento(Decimal("100000.00"), 1, "EGRESADOS2026", None)

    assert descuento == Decimal("15000.00")


# R2 — Talles


def test_un_talle_con_espacios_y_en_minuscula_es_valido():
    carrito = [item(producto="remera", talle="  m ")]

    subtotal = calcular_subtotal(carrito)

    assert subtotal == Decimal("11999.50")


# R3 — Cantidad


def test_la_cantidad_diez_es_valida():
    carrito = [item(producto="remera", cantidad=10)]

    subtotal = calcular_subtotal(carrito)

    assert subtotal == Decimal("119995.00")


def test_la_cantidad_once_es_invalida():
    carrito_item = item(cantidad=11)

    codigo = codigo_de_error(validar_item, carrito_item)

    assert codigo == "CANTIDAD_INVALIDA"


@pytest.mark.parametrize("cantidad", [2.5, "2", True])
def test_una_cantidad_que_no_es_entera_es_invalida(cantidad):
    carrito_item = item(cantidad=cantidad)

    codigo = codigo_de_error(validar_item, carrito_item)

    assert codigo == "CANTIDAD_INVALIDA"


@pytest.mark.parametrize(
    "item_incompleto, codigo_esperado",
    [
        ({"talle": "M", "cantidad": 1}, "PRODUCTO_INEXISTENTE"),
        ({"producto": "buzo", "cantidad": 1}, "TALLE_INVALIDO"),
        ({"producto": "buzo", "talle": None, "cantidad": 1}, "TALLE_INVALIDO"),
        ({"producto": "buzo", "talle": "M"}, "CANTIDAD_INVALIDA"),
    ],
)
def test_un_item_incompleto_lanza_checkout_error(item_incompleto, codigo_esperado):
    carrito = [item_incompleto]

    codigo = codigo_de_error(calcular_total, carrito, "CABA")

    assert codigo == codigo_esperado


# R4 — Carrito


def test_un_carrito_vacio_es_un_error():
    carrito = []

    codigo = codigo_de_error(calcular_total, carrito, "CABA")

    assert codigo == "CARRITO_VACIO"


def test_validar_item_no_modifica_el_item_que_recibe():
    original = item(talle="m")

    validar_item(original)

    assert original == item(talle="m")


# R8 — Envío


def test_una_zona_inexistente_lanza_zona_invalida():
    subtotal = Decimal("1000.00")

    codigo = codigo_de_error(calcular_envio, subtotal, "MARTE")

    assert codigo == "ZONA_INVALIDA"


def test_una_zona_que_no_es_texto_lanza_zona_invalida():
    subtotal = Decimal("1000.00")

    codigo = codigo_de_error(calcular_envio, subtotal, None)

    assert codigo == "ZONA_INVALIDA"


def test_el_envio_es_gratis_desde_sesenta_mil_inclusive():
    subtotal_con_descuento = Decimal("60000.00")

    envio = calcular_envio(subtotal_con_descuento, "INTERIOR")

    assert envio == Decimal("0.00")


def test_el_envio_gratis_se_evalua_con_el_descuento_aplicado():
    carrito = [item(producto="buzo", cantidad=2), item(producto="remera")]

    resultado = calcular_total(carrito, "CABA", "EGRESADOS2026", HOY_VIGENTE)

    assert resultado == {
        "subtotal": Decimal("61999.30"),
        "descuento": Decimal("9299.90"),
        "envio": Decimal("2500.00"),
        "total": Decimal("55199.40"),
    }


def test_calcular_envio_usa_los_nombres_de_parametro_del_contrato():
    argumentos = {"subtotal_con_descuento": Decimal("1000.00"), "zona": "GBA"}

    envio = calcular_envio(**argumentos)

    assert envio == Decimal("4000.00")