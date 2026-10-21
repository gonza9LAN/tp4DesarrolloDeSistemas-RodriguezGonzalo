from datetime import date
from decimal import Decimal

import pytest

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