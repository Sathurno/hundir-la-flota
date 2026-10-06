import random
from collections import Counter

from .ia import AGUA, HUNDIDO, TOCADO


class EstrategiaAprendizaje:
    def __init__(self, tamano, flota):
        self.tamano = tamano
        self.esloras = Counter(flota)
        self.disparadas = set()
        self.bloqueadas = set()
        self.aciertos = set()

    def registrar(self, casilla, resultado, barco=None):
        self.disparadas.add(casilla)
        if resultado == AGUA:
            self.bloqueadas.add(casilla)
        elif resultado == TOCADO:
            self.aciertos.add(casilla)
        elif resultado == HUNDIDO:
            celdas = set(barco) if barco else {casilla}
            self.disparadas |= celdas
            self.bloqueadas |= celdas
            self.aciertos -= celdas
            eslora = len(celdas)
            self.esloras[eslora] -= 1
            if self.esloras[eslora] <= 0:
                del self.esloras[eslora]

    def _colocaciones(self, eslora):
        ventanas = []
        for fila in range(self.tamano):
            for col in range(self.tamano - eslora + 1):
                ventanas.append(frozenset((fila, col + i) for i in range(eslora)))
        for col in range(self.tamano):
            for fila in range(self.tamano - eslora + 1):
                ventanas.append(frozenset((fila + i, col) for i in range(eslora)))
        return ventanas

    def _puntuacion(self):
        puntuacion = [[0.0] * self.tamano for _ in range(self.tamano)]
        con_evidencia = bool(self.aciertos)
        for eslora, cantidad in self.esloras.items():
            validas = []
            for ventana in self._colocaciones(eslora):
                if ventana & self.bloqueadas:
                    continue
                if con_evidencia and not (ventana & self.aciertos):
                    continue
                validas.append(ventana)
            if not validas:
                continue
            peso = cantidad / len(validas)
            for ventana in validas:
                for fila, col in ventana:
                    puntuacion[fila][col] += peso
        return puntuacion

    def elegir_disparo(self):
        puntuacion = self._puntuacion()
        mejor = -1.0
        candidatas = []
        for fila in range(self.tamano):
            for col in range(self.tamano):
                casilla = (fila, col)
                if casilla in self.disparadas:
                    continue
                valor = puntuacion[fila][col]
                if valor > mejor:
                    mejor = valor
                    candidatas = [casilla]
                elif valor == mejor:
                    candidatas.append(casilla)
        if not candidatas:
            return None
        return random.choice(candidatas)
