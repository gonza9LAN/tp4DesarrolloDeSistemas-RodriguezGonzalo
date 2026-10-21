from datetime import date
from decimal import Decimal

import pytest

import pedidos
from checkout import CheckoutError

HOY_VIGENTE = date(2026, 10, 1)


@pytest.fixture
def ruta(tmp_path):
    return str(tmp_path / "tienda.db")


@pytest.fixture
def con(ruta):
    conexion = pedidos.conectar(ruta)
    pedidos.crear_esquema(conexion)
    yield conexion
    conexion.close()


def item(producto="buzo", talle="M", cantidad=1, **extra):
    return {"producto": producto, "talle": talle, "cantidad": cantidad, **extra}


def contar(ruta, tabla):
    assert tabla in ("pedidos", "items")
    otra = pedidos.conectar(ruta)
    try:
        return otra.execute(f"SELECT COUNT(*) FROM {tabla}").fetchone()[0]
    finally:
        otra.close()


def test_un_id_inexistente_devuelve_none(con):
    assert pedidos.obtener_pedido(con, 999) is None


# R10 — Si checkout lanza CheckoutError, el error se propaga y no queda nada guardado


def test_un_error_de_checkout_se_propaga_y_no_deja_nada_guardado(con, ruta):
    carrito = [item(talle="XXXL")]

    with pytest.raises(CheckoutError) as error:
        pedidos.guardar_pedido(con, "ana@mail.com", carrito, "CABA")

    assert error.value.code == "TALLE_INVALIDO"
    assert contar(ruta, "pedidos") == 0
    assert contar(ruta, "items") == 0


# R10 — Al terminar guardar_pedido, otra conexión ve el pedido completo


def test_otra_conexion_ve_el_pedido_completo_al_terminar_de_guardar(con, ruta):
    carrito = [item(producto="remera", talle="M"), item(producto="remera", talle="L")]

    pedido_id = pedidos.guardar_pedido(con, "ana@mail.com", carrito, "CABA")

    otra = pedidos.conectar(ruta)
    try:
        pedido = pedidos.obtener_pedido(otra, pedido_id)
    finally:
        otra.close()
    assert pedido["subtotal"] == Decimal("23999.00")
    assert [i["talle"] for i in pedido["items"]] == ["M", "L"]


# R10 — Los montos recuperados son idénticos a los que calculó checkout


def test_los_montos_recuperados_son_identicos_a_los_que_calculo_checkout(con):
    carrito = [item(producto="remera")]

    pedido_id = pedidos.guardar_pedido(con, "ana@mail.com", carrito, "CABA", "EGRESADOS2026", HOY_VIGENTE)
    pedido = pedidos.obtener_pedido(con, pedido_id)

    assert {clave: pedido[clave] for clave in ("subtotal", "descuento", "envio", "total")} == {
        "subtotal": Decimal("11999.50"),
        "descuento": Decimal("1799.93"),
        "envio": Decimal("2500.00"),
        "total": Decimal("12699.57"),
    }


# R10 — Ningún valor de email puede alterar la consulta de pedidos_de


def test_un_email_malicioso_no_altera_la_consulta_de_pedidos_de(con):
    pedidos.guardar_pedido(con, "ana@mail.com", [item()], "CABA")

    resultado = pedidos.pedidos_de(con, "x' OR '1'='1")

    assert resultado == []