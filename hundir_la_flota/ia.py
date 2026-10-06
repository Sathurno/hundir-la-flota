import random

AGUA = "agua"
TOCADO = "tocado"
HUNDIDO = "hundido"

DESPLAZAMIENTOS = ((-1, 0), (1, 0), (0, -1), (0, 1))


class EstrategiaAleatoria:
    def __init__(self, tamano):
        self.tamano = tamano
        self.disponibles = [(f, c) for f in range(tamano) for c in range(tamano)]
        self.posicion = {casilla: i for i, casilla in enumerate(self.disponibles)}

    def _sacar(self, casilla):
        i = self.posicion.pop(casilla)
        ultima = self.disponibles.pop()
        if ultima != casilla:
            self.disponibles[i] = ultima
            self.posicion[ultima] = i

    def _al_azar(self):
        return self.disponibles[random.randrange(len(self.disponibles))]

    def elegir_disparo(self):
        return self._al_azar()

    def registrar(self, casilla, resultado, barco=None):
        if casilla in self.posicion:
            self._sacar(casilla)


class EstrategiaCaza(EstrategiaAleatoria):
    def __init__(self, tamano):
        super().__init__(tamano)
        self.aciertos = []
        self.objetivos = []

    def elegir_disparo(self):
        while self.objetivos:
            casilla = self.objetivos.pop()
            if casilla in self.posicion:
                return casilla
        return self._al_azar()

    def registrar(self, casilla, resultado, barco=None):
        super().registrar(casilla, resultado)
        if resultado == TOCADO:
            self.aciertos.append(casilla)
            self._actualizar_objetivos()
        elif resultado == HUNDIDO:
            self.aciertos = []
            self.objetivos = []

    def _dentro(self, casilla):
        fila, col = casilla
        return 0 <= fila < self.tamano and 0 <= col < self.tamano

    def _vecinos(self, casilla):
        fila, col = casilla
        return [(fila + df, col + dc) for df, dc in DESPLAZAMIENTOS
                if self._dentro((fila + df, col + dc))]

    def _actualizar_objetivos(self):
        if len(self.aciertos) == 1:
            self.objetivos.extend(self._vecinos(self.aciertos[0]))
            return
        (f0, c0), (f1, _) = self.aciertos[0], self.aciertos[1]
        if f0 == f1:
            columnas = sorted(col for _, col in self.aciertos)
            extremos = [(f0, columnas[0] - 1), (f0, columnas[-1] + 1)]
        else:
            filas = sorted(fila for fila, _ in self.aciertos)
            extremos = [(filas[0] - 1, c0), (filas[-1] + 1, c0)]
        self.objetivos.extend(e for e in extremos if self._dentro(e))
