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