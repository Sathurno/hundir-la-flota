import random

from hundir_la_flota import ia, ia_aprendizaje, utils

random.seed(7)


def crear(nivel, tamano):
    if nivel == "aleatoria":
        return ia.EstrategiaAleatoria(tamano)
    if nivel == "caza":
        return ia.EstrategiaCaza(tamano)
    return ia_aprendizaje.EstrategiaAprendizaje(tamano, utils.FLOTA)


def comprobar_colocacion(flota, tablero):
    casillas = [c for barco in flota for c in barco["todas"]]
    assert len(flota) == len(utils.FLOTA), f"flota incompleta: {len(flota)}"
    assert len(casillas) == len(set(casillas)), "barcos superpuestos"
    assert sum(utils.FLOTA) == len(casillas), "numero de casillas incorrecto"
    for fila, col in casillas:
        assert 0 <= fila < tablero.shape[0] and 0 <= col < tablero.shape[1], "barco fuera"


def partida(nivel_a, nivel_b, tamano=10):
    t1, f1, i1 = utils.preparar_bando(tamano)
    t2, f2, i2 = utils.preparar_bando(tamano)
    comprobar_colocacion(f1, t1)
    comprobar_colocacion(f2, t2)
    e1, e2 = crear(nivel_a, tamano), crear(nivel_b, tamano)
    turnos = 0
    while True:
        turnos += 1
        c = e1.elegir_disparo()
        r = utils.disparar(c, t2, i2)
        assert r != "repetido", f"{nivel_a} repite {c}"
        e1.registrar(c, r, i2[c]["todas"] if r == "hundido" else None)
        if not utils.quedan_barcos(f2):
            return nivel_a, turnos
        c = e2.elegir_disparo()
        r = utils.disparar(c, t1, i1)
        assert r != "repetido", f"{nivel_b} repite {c}"
        e2.registrar(c, r, i1[c]["todas"] if r == "hundido" else None)
        if not utils.quedan_barcos(f1):
            return nivel_b, turnos


def media_turnos(nivel_a, nivel_b, repeticiones=200):
    total = 0
    for _ in range(repeticiones):
        _, turnos = partida(nivel_a, nivel_b)
        total += turnos
    return total / repeticiones


if __name__ == "__main__":
    print("tablero:", utils.crear_tablero().shape)
    for a, b in (("aleatoria", "aleatoria"), ("caza", "aleatoria"),
                 ("aprendizaje", "aleatoria"), ("aprendizaje", "caza")):
        ganador, turnos = partida(a, b)
        print(f"{a:>12} vs {b:<12} -> gana {ganador:<12} en {turnos} turnos")
    for nivel in ("aleatoria", "caza", "aprendizaje"):
        print(f"media turnos {nivel:>12}: {media_turnos(nivel, 'aleatoria'):.1f}")
        print(f"media turnos {nivel:>12}: {media_turnos(nivel, 'caza'):.1f}")
    print("OK")
