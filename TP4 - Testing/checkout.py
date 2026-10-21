import json
from datetime import date
from decimal import ROUND_HALF_UP, Decimal


class CheckoutError(Exception):
    def __init__(self, code, mensaje):
        super().__init__(mensaje)
        self.code = code
        self.mensaje = mensaje


CATALOGO = {
    "buzo": Decimal("24999.90"),
    "remera": Decimal("11999.50"),
    "campera": Decimal("47999.99"),
}

TALLES = ["XS", "S", "M", "L", "XL", "XXL"]

CUPONES = {
    "EGRESADOS2026": {"tipo": "porcentaje", "valor": Decimal("0.15"), "vence": date(2026, 11, 30)},
    "BIENVENIDA": {"tipo": "fijo", "valor": Decimal("3000.00"), "minimo": Decimal("20000.00")},
    "DEBUG100": {"tipo": "porcentaje", "valor": Decimal("1.00"), "vence": date(2099, 12, 31)},
}

ENVIOS = {
    "CABA": Decimal("2500.00"),
    "GBA": Decimal("4000.00"),
    "INTERIOR": Decimal("6500.00"),
    "RETIRO": Decimal("0.00"),
}


def validar_item(item):
    if item["producto"] not in CATALOGO:
        raise CheckoutError("PRODUCTO_INEXISTENTE", f"Producto inexistente: {item['producto']}")

    item["talle"] = item["talle"].upper()

    if item["talle"] not in TALLES:
        raise CheckoutError("TALLE_INVALIDO", f"Talle inválido: {item['talle']}")

    if not (1 <= item["cantidad"] < 10):
        raise CheckoutError("CANTIDAD_INVALIDA", "La cantidad debe estar entre 1 y 10")


def calcular_subtotal(carrito):
    subtotal = Decimal("0")
    for item in carrito:
        validar_item(item)
        precio = CATALOGO[item["producto"]]
        subtotal += precio * item["cantidad"]

    return round(subtotal, 2)


def calcular_descuento(subtotal, cantidad_prendas, cupon=None, fecha=date.today()):
    descuento_cantidad = Decimal("0")
    if cantidad_prendas > 5:
        descuento_cantidad = subtotal * Decimal("0.10")

    descuento_cupon = Decimal("0")

    if cupon != None:
        codigo = cupon.strip()

        if codigo not in CUPONES:
            raise CheckoutError("CUPON_INVALIDO", "El cupón no existe")

        datos = CUPONES[codigo]

        if datos["tipo"] == "porcentaje":
            if not fecha < datos["vence"]:
                raise CheckoutError("CUPON_VENCIDO", "El cupón está vencido")
            descuento_cupon = subtotal * datos["valor"]

        elif datos["tipo"] == "fijo":
            if subtotal < datos["minimo"]:
                raise CheckoutError(
                    "CUPON_MINIMO_NO_ALCANZADO",
                    f"El cupón requiere una compra mínima de ${datos['minimo']}",
                )
            descuento_cupon = datos["valor"]

    descuento = max(descuento_cantidad, descuento_cupon)
    return descuento.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


def calcular_envio(subtotal, zona):
    zona = zona.strip().upper()

    if zona not in ENVIOS:
        raise CheckoutError(
            "ZONA_INVALIDA",
            f"Zona inválida. Opciones: {ENVIOS.keys().join(', ')}",
        )

    if subtotal >= 60000:
        return Decimal("0.00")

    return ENVIOS[zona]


def calcular_total(carrito, zona, cupon=None, fecha=date.today()):
    subtotal = calcular_subtotal(carrito)

    prendas = 0
    for item in carrito:
        prendas = prendas + item["cantidad"]

    descuento = calcular_descuento(subtotal, prendas, cupon, fecha)
    envio = calcular_envio(subtotal, zona)
    total = subtotal - descuento + envio

    resultado = {
        "subtotal": subtotal,
        "descuento": descuento,
        "envio": envio,
        "total": round(total, 2),
    }
    return resultado
