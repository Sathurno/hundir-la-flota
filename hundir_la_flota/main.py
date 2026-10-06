from . import colores
from . import utils
from .ia import EstrategiaAleatoria, EstrategiaCaza
from .ia_aprendizaje import EstrategiaAprendizaje

NIVELES = {
    1: ("Aleatoria", "dispara sin estrategia"),
    2: ("Aleatoria + caza", "si acierta, remata el barco"),
    3: ("Aprendizaje", "estima probabilidades con lo que sabe"),
}

ETIQUETAS = {
    "agua": ("AGUA", (colores.CIAN,)),
    "tocado": ("TOCADO", (colores.ROJO, colores.NEGRITA)),
    "hundido": ("¡HUNDIDO!", (colores.ROJO_CLARO, colores.NEGRITA)),
    "repetido": ("YA DISPARADO", (colores.AMARILLO,)),
}


def elegir_nivel():
    print(colores.NEGRITA + "Dificultad de la máquina:" + colores.RESET)
    for clave, (nombre, descripcion) in NIVELES.items():
        print(f"  {clave}. {nombre}  ({descripcion})")
    while True:
        entrada = input("Elige 1-3 [2]: ").strip()
        if entrada == "":
            return 2
        if entrada.isdigit() and int(entrada) in NIVELES:
            return int(entrada)
        print("Opción no válida.")


def elegir_tamano():
    entrada = input("Tamaño del tablero [10]: ").strip()
    if entrada.isdigit() and int(entrada) >= 6:
        return int(entrada)
    return 10


def crear_estrategia(nivel, tamano):
    if nivel == 1:
        return EstrategiaAleatoria(tamano)
    if nivel == 3:
        return EstrategiaAprendizaje(tamano, utils.FLOTA)
    return EstrategiaCaza(tamano)


def etiqueta_resultado(resultado, activo):
    texto, codigos = ETIQUETAS[resultado]
    return colores.pintar(texto, *codigos, activo=activo)


def turno_jugador(tablero, indice, activo):
    while True:
        casilla = utils.pedir_disparo(tablero.shape[0])
        if casilla is None:
            return None
        resultado = utils.disparar(casilla, tablero, indice)
        print(f"Tu disparo a {casilla}: {etiqueta_resultado(resultado, activo)}")
        if resultado != "repetido":
            return resultado


def turno_maquina(estrategia, tablero, indice, activo):
    casilla = estrategia.elegir_disparo()
    resultado = utils.disparar(casilla, tablero, indice)
    barco = indice[casilla]["todas"] if resultado == "hundido" else None
    estrategia.registrar(casilla, resultado, barco)
    print(f"La máquina dispara a {casilla}: {etiqueta_resultado(resultado, activo)}")
    return resultado


def mostrar(propio, rival, activo, revelar=False):
    visto = rival if revelar else utils.ocultar_barcos(rival)
    print()
    print(utils.render(propio, visto, activo))


def jugar(activo):
    nivel = elegir_nivel()
    tamano = elegir_tamano()
    tablero_jugador, flota_jugador, indice_jugador = utils.preparar_bando(tamano)
    tablero_maquina, flota_maquina, indice_maquina = utils.preparar_bando(tamano)
    estrategia = crear_estrategia(nivel, tamano)

    while True:
        mostrar(tablero_jugador, tablero_maquina, activo)
        jugada = turno_jugador(tablero_maquina, indice_maquina, activo)
        if jugada is None:
            print(colores.pintar("\nHas abandonado la partida.", colores.AMARILLO, activo=activo))
            return
        if not utils.quedan_barcos(flota_maquina):
            mostrar(tablero_jugador, tablero_maquina, activo, revelar=True)
            print(colores.pintar("¡Has hundido toda la flota enemiga! GANAS.",
                                 colores.VERDE_CLARO, colores.NEGRITA, activo=activo))
            return

        turno_maquina(estrategia, tablero_jugador, indice_jugador, activo)
        if not utils.quedan_barcos(flota_jugador):
            mostrar(tablero_jugador, tablero_maquina, activo, revelar=True)
            print(colores.pintar("La máquina ha hundido tu flota. PIERDES.",
                                 colores.ROJO, colores.NEGRITA, activo=activo))
            return


def main():
    activo = colores.preparar()
    print(colores.pintar(utils.BANNER, colores.CIAN, activo=activo))
    print(utils.leyenda(activo))
    print()
    try:
        jugar(activo)
    except (KeyboardInterrupt, EOFError):
        print(colores.pintar("\nPartida interrumpida.", colores.AMARILLO, activo=activo))
    print(colores.pintar("Gracias por jugar a Hundir la Flota.", colores.GRIS, activo=activo))


if __name__ == "__main__":
    main()
