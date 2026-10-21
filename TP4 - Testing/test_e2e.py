import json
import threading
import urllib.error
import urllib.request

import pytest

import api

RUTA = "/api/v1/pedidos"


@pytest.fixture
def url(tmp_path):
    servidor = api.crear_servidor(str(tmp_path / "tienda.db"), 0)
    threading.Thread(target=servidor.serve_forever, kwargs={"poll_interval": 0.05}, daemon=True).start()
    yield f"http://127.0.0.1:{servidor.server_address[1]}"
    servidor.shutdown()
    servidor.server_close()


def pedir(url, metodo, ruta, cuerpo=None, crudo=None):
    datos = crudo if crudo is not None else (json.dumps(cuerpo).encode() if cuerpo is not None else None)
    req = urllib.request.Request(url + ruta, data=datos, method=metodo,
                                 headers={"Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=5) as r:
            return r.status, json.loads(r.read() or b"null")
    except urllib.error.HTTPError as e:
        return e.code, json.loads(e.read() or b"null")


def compra(**cambios):
    cuerpo = {"email": "ana@mail.com", "zona": "CABA",
              "carrito": [{"producto": "buzo", "talle": "M", "cantidad": 1}]}
    cuerpo.update(cambios)
    return cuerpo


def test_una_ruta_inexistente_devuelve_404(url):
    status, cuerpo = pedir(url, "GET", "/api/v1/otra")
    assert status == 404
    assert cuerpo["error"]["code"] == "RUTA_INEXISTENTE"


# R11 — Endpoints


def test_crear_un_pedido_responde_201_con_los_montos_como_texto(url):
    cuerpo = compra()

    status, respuesta = pedir(url, "POST", RUTA, cuerpo)

    assert status == 201
    assert respuesta == {
        "id": respuesta["id"],
        "subtotal": "24999.90",
        "descuento": "0.00",
        "envio": "2500.00",
        "total": "27499.90",
    }


def test_un_pedido_creado_se_lee_completo_con_get(url):
    _, creado = pedir(url, "POST", RUTA, compra())

    status, pedido = pedir(url, "GET", f"{RUTA}/{creado['id']}")

    assert status == 200
    assert pedido == {
        "id": creado["id"],
        "email": "ana@mail.com",
        "zona": "CABA",
        "cupon": None,
        "subtotal": "24999.90",
        "descuento": "0.00",
        "envio": "2500.00",
        "total": "27499.90",
        "items": [{"producto": "buzo", "talle": "M", "cantidad": 1, "precio_unitario": "24999.90"}],
    }


# R11 — Errores


def test_un_error_de_negocio_responde_422_con_el_codigo_del_error(url):
    cuerpo = compra(carrito=[{"producto": "buzo", "talle": "XXXL", "cantidad": 1}])

    status, respuesta = pedir(url, "POST", RUTA, cuerpo)

    assert status == 422
    assert respuesta["error"]["code"] == "TALLE_INVALIDO"
    assert set(respuesta["error"]) == {"code", "message"}


def test_si_falta_el_email_responde_400_datos_incompletos(url):
    cuerpo = compra()
    del cuerpo["email"]

    status, respuesta = pedir(url, "POST", RUTA, cuerpo)

    assert status == 400
    assert respuesta["error"]["code"] == "DATOS_INCOMPLETOS"


def test_una_fecha_sin_formato_aaaa_mm_dd_responde_400_fecha_invalida(url):
    cuerpo = compra(fecha="30/11/2026")

    status, respuesta = pedir(url, "POST", RUTA, cuerpo)

    assert status == 400
    assert respuesta["error"]["code"] == "FECHA_INVALIDA"


def test_un_pedido_que_no_existe_responde_404_pedido_inexistente(url):
    ruta_inexistente = f"{RUTA}/999"

    status, respuesta = pedir(url, "GET", ruta_inexistente)

    assert status == 404
    assert respuesta["error"]["code"] == "PEDIDO_INEXISTENTE"