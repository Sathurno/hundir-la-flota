"""Codigos ANSI para pintar la terminal y su activacion en Windows."""
import os
import sys

RESET = "\033[0m"
NEGRITA = "\033[1m"

NEGRO = "\033[30m"
ROJO = "\033[31m"
VERDE = "\033[32m"
AMARILLO = "\033[33m"
AZUL = "\033[34m"
MAGENTA = "\033[35m"
CIAN = "\033[36m"
BLANCO = "\033[37m"

GRIS = "\033[90m"
ROJO_CLARO = "\033[91m"
VERDE_CLARO = "\033[92m"
AMARILLO_CLARO = "\033[93m"
AZUL_CLARO = "\033[94m"
CIAN_CLARO = "\033[96m"

FONDO_AZUL = "\033[44m"
FONDO_ROJO = "\033[41m"


def _activar_windows():
    if os.name != "nt":
        return
    try:
        import ctypes

        kernel32 = ctypes.windll.kernel32
        handle = kernel32.GetStdHandle(-11)
        modo = ctypes.c_uint32()
        kernel32.GetConsoleMode(handle, ctypes.byref(modo))
        kernel32.SetConsoleMode(handle, modo.value | 0x0004)
    except Exception:
        pass


def color_soportado():
    if os.environ.get("NO_COLOR"):
        return False
    return sys.stdout.isatty()


def preparar():
    _activar_windows()
    return color_soportado()


def pintar(texto, *codigos, activo=True):
    if not activo or not codigos:
        return texto
    return "".join(codigos) + texto + RESET
