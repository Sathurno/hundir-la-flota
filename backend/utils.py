import random
import re

import numpy as np

from . import colores

AGUA_VACIA = "_"
BARCO = "O"
TOCADO = "X"
AGUA = "A"
HUNDIDO = "H"

FLOTA = [2, 2, 2, 3, 3, 4]

SIMBOLOS = {
    AGUA_VACIA: ("·", (colores.AZUL,)),
    AGUA: ("o", (colores.CIAN,)),
    BARCO: ("■", (colores.VERDE_CLARO,)),
    TOCADO: ("X", (colores.ROJO, colores.NEGRITA)),
    HUNDIDO: ("▓", (colores.ROJO_CLARO, colores.NEGRITA)),
}

BANNER = r"""
   ____             _     _     _         __ _       _
  | __ )  __ _  ___| |_  | |   | |___    / _| | ___ | |_ __ _
  |  _ \ / _` |/ __| __| | |___| / __|  | |_| |/ _ \| __/ _` |
  | |_) | (_| |\__ \ |_  | |___| \__ \  |  _| | (_) | || (_| |
  |____/ \__,_||___/\__| |_|   |_|___/  |_| |_|\___/ \__\__,_|
"""


def crear_tablero(tamano=10):
    return np.full((tamano, tamano), AGUA_VACIA)


def _candidatas(eslora, tamano):
    casillas = []
    for fila in range(tamano):
        for col in range(tamano - eslora + 1):
            casillas.append([(fila, col + i) for i in range(eslora)])
    for col in range(tamano):
        for fila in range(tamano - eslora + 1):
            casillas.append([(fila + i, col) for i in range(eslora)])
    return casillas


def crear_barco(eslora, tamano):
    if random.choice(["H", "V"]) == "H":
        fila = random.randint(0, tamano - 1)
        col = random.randint(0, tamano - eslora)
        return [(fila, col + i) for i in range(eslora)]
    fila = random.randint(0, tamano - eslora)
    col = random.randint(0, tamano - 1)
    return [(fila + i, col) for i in range(eslora)]


def colocar_barco(barco, tablero):
    for casilla in barco:
        tablero[casilla] = BARCO
    return tablero


def _cabe(barco, tablero):
    return all(tablero[casilla] == AGUA_VACIA for casilla in barco)


def colocar_barcos(tablero, esloras=FLOTA):
    tamano = tablero.shape[0]
    flota = []
    for eslora in esloras:
        candidatas = _candidatas(eslora, tamano)
        random.shuffle(candidatas)
        for barco in candidatas:
            if _cabe(barco, tablero):
                colocar_barco(barco, tablero)
                casillas = set(barco)
                flota.append({"vivas": set(casillas), "todas": casillas})
                break
    return flota


def construir_indice(flota):
    indice = {}
    for barco in flota:
        for casilla in barco["todas"]:
            indice[casilla] = barco
    return indice


def preparar_bando(tamano, esloras=FLOTA):
    while True:
        tablero = crear_tablero(tamano)
        flota = colocar_barcos(tablero, esloras)
        if len(flota) == len(esloras):
            return tablero, flota, construir_indice(flota)


def disparar(casilla, tablero, indice):
    estado = tablero[casilla]
    if estado in (TOCADO, AGUA, HUNDIDO):
        return "repetido"
    if estado == AGUA_VACIA:
        tablero[casilla] = AGUA
        return "agua"
    barco = indice[casilla]
    barco["vivas"].discard(casilla)
    if barco["vivas"]:
        tablero[casilla] = TOCADO
        return "tocado"
    for celda in barco["todas"]:
        tablero[celda] = HUNDIDO
    return "hundido"


def quedan_barcos(flota):
    return any(barco["vivas"] for barco in flota)


def barcos_vivos(flota):
    return [len(barco["todas"]) for barco in flota if barco["vivas"]]


def ocultar_barcos(tablero):
    visible = tablero.copy()
    visible[visible == BARCO] = AGUA_VACIA
    return visible


ANSI = re.compile(r"\x1b\[[0-9;]*m")


def _ancho(texto):
    return len(ANSI.sub("", texto))


def _simbolo(estado, activo):
    glifo, codigos = SIMBOLOS[estado]
    return colores.pintar(glifo, *codigos, activo=activo)


def _lineas(tablero, activo):
    tamano = tablero.shape[0]
    cabecera = "   " + "".join(f"{i:>2}" for i in range(tamano))
    filas = [colores.pintar(cabecera, colores.GRIS, activo=activo)]
    for i, fila in enumerate(tablero):
        etiqueta = colores.pintar(f"{i:>2} ", colores.GRIS, activo=activo)
        celdas = "".join(f" {_simbolo(estado, activo)}" for estado in fila)
        filas.append(etiqueta + celdas)
    return filas


def render(propio, enemigo, activo):
    izquierda = _lineas(propio, activo)
    derecha = _lineas(enemigo, activo)
    ancho = _ancho(izquierda[0])
    titulo_propio = colores.pintar("TU TABLERO", colores.VERDE_CLARO,
                                   colores.NEGRITA, activo=activo)
    titulo_enemigo = colores.pintar("TABLERO ENEMIGO", colores.ROJO_CLARO,
                                    colores.NEGRITA, activo=activo)
    hueco = " " * max(4, ancho - len("TU TABLERO") + 4)
    lineas = [f"{titulo_propio}{hueco}{titulo_enemigo}"]
    for a, b in zip(izquierda, derecha):
        relleno = " " * (ancho - _ancho(a) + 4)
        lineas.append(a + relleno + b)
    return "\n".join(lineas)


def leyenda(activo):
    partes = []
    for estado, texto in ((AGUA_VACIA, "agua"), (AGUA, "fallo"),
                          (BARCO, "barco"), (TOCADO, "tocado"),
                          (HUNDIDO, "hundido")):
        glifo = _simbolo(estado, activo)
        partes.append(f"{glifo} {colores.pintar(texto, colores.GRIS, activo=activo)}")
    return "  ".join(partes)


def pedir_disparo(tamano):
    while True:
        entrada = input("Disparo (fila,columna) o 'salir': ").strip().lower()
        if entrada in ("salir", "s"):
            return None
        partes = entrada.replace(",", " ").split()
        if len(partes) == 2 and all(p.isdigit() for p in partes):
            fila, col = int(partes[0]), int(partes[1])
            if 0 <= fila < tamano and 0 <= col < tamano:
                return (fila, col)
        print(colores.pintar(
            f"Entrada no válida. Dos números entre 0 y {tamano - 1}, ej: 3,4",
            colores.AMARILLO, activo=True))
