"""Evaluador del proyecto Data Stream Processor.

Las pruebas viven SOLO en este archivo. Hay dos formas de ejecutarlas y ambas
corren exactamente el mismo codigo:

A) Importando este archivo (desde el cuaderno .ipynb del estudiante, en una celda
   NUEVA, DESPUES de la celda que define la clase):

       import sys
       from pathlib import Path
       d = Path.cwd().resolve()                 # busca evaluador.py hacia arriba
       while not (d / "evaluador.py").exists() and d != d.parent:
           d = d.parent
       sys.path.insert(0, str(d))

       from evaluador import ejecutar
       ejecutar(DataProcessor, estudiante="Nombre Apellido")

B) Copiando una celda. `celda_evaluador.py` contiene el nucleo de este archivo mas
   la llamada final; se pega completo en una celda del cuaderno, sin importar nada.
   Se genera automaticamente (no se edita a mano):

       python evaluador.py --celda               # (re)genera celda_evaluador.py
       python evaluador.py --celda --comprobar   # falla si esta desactualizada

En ambos casos se imprime el informe y se guarda `resultados_<Nombre_Apellido>.txt`
en la carpeta actual: ese es el archivo que se envia al profesor.

Desde terminal, si la solucion esta en un .py:

    python evaluador.py student_work/solucion.py --estudiante "Nombre Apellido"

El profesor comprueba que un informe no fue editado a mano con:

    python evaluador.py --verificar resultados_Nombre_Apellido.txt

Las pruebas solo usan la interfaz del enunciado (add, process_next, undo,
pending, current_value, Empty, KeyError). No dependen de los nombres de los
atributos internos ni del tipo de excepcion elegido para los registros mal
formados, ni de decisiones de diseno que el enunciado no fija.
"""
import datetime
import hashlib
import inspect
import platform
import re
import sys
import threading
import traceback
import unicodedata
from pathlib import Path

_VERSION = "1.1"
_TIMEOUT = 5                    # segundos por prueba (protege contra bucles infinitos)
_SALT = "data-stream-processor-2026-02"
_MARCA = "== INTEGRIDAD =="
_NO = "NO_EXISTE"
_ARCHIVO = sys._getframe().f_code.co_filename   # este mismo codigo (archivo o celda)

_A = ("S01", "temperature", 20)
_B = ("S01", "temperature", 25)
_C = ("S01", "humidity", 60)

_INTERFAZ, _OBLIGATORIAS, _BORDE, _BONUS = [], [], [], []


def _prueba(lista, nombre):
    def deco(f):
        lista.append((nombre, f))
        return f
    return deco


# ------------------------------------------------------------------ utilidades
def _norm(x):
    return tuple(x) if isinstance(x, list) else x


def _eq(obtenido, esperado, que):
    if _norm(obtenido) != esperado:
        raise AssertionError(f"{que}: esperaba {esperado!r}, obtuvo {obtenido!r}")


def _valor(p, sensor, variable):
    try:
        return p.current_value(sensor, variable)
    except KeyError:
        return _NO


def _es_empty(e):
    return any(c.__name__ == "Empty" for c in type(e).__mro__)


def _espera_empty(f, que):
    try:
        f()
    except Exception as e:
        if _es_empty(e):
            return
        raise AssertionError(f"{que}: esperaba Empty, obtuvo {type(e).__name__}: {e}")
    raise AssertionError(f"{que}: esperaba Empty, pero no se lanzo ninguna excepcion")


def _espera_keyerror(f, que):
    try:
        f()
    except KeyError:
        return
    except Exception as e:
        raise AssertionError(f"{que}: esperaba KeyError, obtuvo {type(e).__name__}: {e}")
    raise AssertionError(f"{que}: esperaba KeyError, pero no se lanzo ninguna excepcion")


def _espera_rechazo(p, registro, que):
    """add debe lanzar alguna excepcion (el tipo lo elige el estudiante) y no encolar."""
    antes = p.pending()
    try:
        p.add(registro)
    except Exception:
        if p.pending() != antes:
            raise AssertionError(f"{que}: lanzo excepcion pero el registro quedo en la cola")
        return
    raise AssertionError(f"{que}: add acepto {registro!r} y debia rechazarlo")


def _cargar(P, *registros):
    p = P()
    for r in registros:
        p.add(r)
    return p


def _procesar(p, n=1):
    return [p.process_next() for _ in range(n)]


# ----------------------------------------------------- interfaz y restricciones
@_prueba(_INTERFAZ, "Define add, process_next, undo, pending y current_value")
def _(P):
    faltan = [m for m in ("add", "process_next", "undo", "pending", "current_value")
              if not callable(getattr(P, m, None))]
    if faltan:
        raise AssertionError(f"faltan metodos: {', '.join(faltan)}")


@_prueba(_INTERFAZ, "Se puede crear DataProcessor() sin argumentos")
def _(P):
    P()


def _atributos(P):
    return list(getattr(P(), "__dict__", {}).values())


def _de_tipo(valores, nombre):
    return [v for v in valores if any(c.__name__ == nombre for c in type(v).__mro__)]


@_prueba(_INTERFAZ, "__init__ crea una ArrayQueue, un ArrayStack y una list")
def _(P):
    vals = _atributos(P)
    faltan = []
    if not _de_tipo(vals, "ArrayQueue"):
        faltan.append("ArrayQueue")
    if not _de_tipo(vals, "ArrayStack"):
        faltan.append("ArrayStack")
    if not any(isinstance(v, list) for v in vals):
        faltan.append("list")
    if faltan:
        raise AssertionError(f"no se encontro en los atributos de la instancia: {', '.join(faltan)}")


@_prueba(_INTERFAZ, "No sustituye Queue/Stack por deque u otra estructura")
def _(P):
    if _de_tipo(_atributos(P), "deque"):
        raise AssertionError("un atributo de la instancia es collections.deque")
    try:
        if re.search(r"\bdeque\b", inspect.getsource(P)):
            return "el codigo de la clase menciona 'deque': revisar manualmente"
    except (OSError, TypeError):
        pass


@_prueba(_INTERFAZ, "ArrayQueue y ArrayStack son las del curso (no reimplementadas)")
def _(P):
    vals = _atributos(P)
    raras = []
    for nombre, marca in (("ArrayQueue", "array_queue"), ("ArrayStack", "array_stack")):
        for v in _de_tipo(vals, nombre):
            mod = type(v).__module__
            if not (mod.startswith("goodrich") or marca in mod):
                raras.append(f"{nombre} viene del modulo '{mod}'")
    if raras:
        return "; ".join(raras) + " (revisar si fue reimplementada)"


# ---------------------------------------------------------- pruebas obligatorias
@_prueba(_OBLIGATORIAS, "1. pending() sobre un procesador vacio")
def _(P):
    _eq(P().pending(), 0, "pending() vacio")


@_prueba(_OBLIGATORIAS, "2. Agregar un registro")
def _(P):
    p = _cargar(P, ("S01", "temperature", 23.5))
    _eq(p.pending(), 1, "pending() tras un add")
    _eq(_valor(p, "S01", "temperature"), _NO, "add no debe procesar el registro; valor actual")


@_prueba(_OBLIGATORIAS, "3. Agregar varios registros")
def _(P):
    _eq(_cargar(P, _A, _B, _C).pending(), 3, "pending() tras tres add")


@_prueba(_OBLIGATORIAS, "4. Procesamiento FIFO")
def _(P):
    p = _cargar(P, _A, _B, _C)
    for esperado, orden in ((_A, "primero"), (_B, "segundo"), (_C, "tercero")):
        _eq(p.process_next(), esperado, f"process_next() {orden}")


@_prueba(_OBLIGATORIAS, "5. Procesar un registro")
def _(P):
    p = _cargar(P, ("S01", "temperature", 23.5))
    _eq(p.process_next(), ("S01", "temperature", 23.5), "registro devuelto")
    _eq(_valor(p, "S01", "temperature"), 23.5, "valor actual")
    _eq(p.pending(), 0, "pending() tras procesar")


@_prueba(_OBLIGATORIAS, "6. Procesar varios registros")
def _(P):
    p = _cargar(P, _A, _B, _C)
    p.process_next()
    _eq(p.pending(), 2, "pending() tras procesar uno")
    _procesar(p, 2)
    _eq(p.pending(), 0, "pending() al final")
    _eq(_valor(p, "S01", "temperature"), 25, "S01/temperature")
    _eq(_valor(p, "S01", "humidity"), 60, "S01/humidity")


@_prueba(_OBLIGATORIAS, "7. Actualizar una variable existente")
def _(P):
    p = _cargar(P, ("S01", "temperature", 23.5), ("S01", "temperature", 27.0))
    p.process_next()
    _eq(_valor(p, "S01", "temperature"), 23.5, "tras el primer registro")
    p.process_next()
    _eq(_valor(p, "S01", "temperature"), 27.0, "tras actualizar")


@_prueba(_OBLIGATORIAS, "8. Consultar el valor actual")
def _(P):
    p = _cargar(P, ("S01", "temperature", 23.5), ("S02", "temperature", 25.1),
                ("S01", "humidity", 61.2))
    _procesar(p, 3)
    _eq(p.current_value("S01", "temperature"), 23.5, "S01/temperature")
    _eq(p.current_value("S02", "temperature"), 25.1, "S02/temperature")
    _eq(p.current_value("S01", "humidity"), 61.2, "S01/humidity")


@_prueba(_OBLIGATORIAS, "9. Realizar un undo()")
def _(P):
    p = _cargar(P, _A, _B)
    _procesar(p, 2)
    p.undo()
    _eq(_valor(p, "S01", "temperature"), 20, "tras undo (25 -> 20)")


@_prueba(_OBLIGATORIAS, "10. Varios undo() consecutivos")
def _(P):
    p = _cargar(P, _A, _B, _C)
    _procesar(p, 3)
    p.undo()
    _eq(_valor(p, "S01", "humidity"), _NO, "tras undo #1, humidity")
    _eq(_valor(p, "S01", "temperature"), 25, "tras undo #1, temperature")
    p.undo()
    _eq(_valor(p, "S01", "temperature"), 20, "tras undo #2, temperature")
    p.undo()
    _eq(_valor(p, "S01", "temperature"), _NO, "tras undo #3, temperature")
    _eq(_valor(p, "S01", "humidity"), _NO, "tras undo #3, humidity")


@_prueba(_OBLIGATORIAS, "11. process_next() con la Queue vacia -> Empty")
def _(P):
    _espera_empty(P().process_next, "process_next() vacio")
    p = _cargar(P, _A)
    p.process_next()
    _espera_empty(p.process_next, "process_next() tras vaciar la cola")


@_prueba(_OBLIGATORIAS, "12. undo() con historial vacio -> Empty")
def _(P):
    _espera_empty(P().undo, "undo() vacio")
    p = _cargar(P, _A)
    _espera_empty(p.undo, "undo() con un registro agregado pero no procesado")


@_prueba(_OBLIGATORIAS, "13. Deshacer la creacion de un dato que no existia")
def _(P):
    p = _cargar(P, ("S01", "temperature", 23.5))
    p.process_next()
    _eq(_valor(p, "S01", "temperature"), 23.5, "antes del undo")
    p.undo()
    _espera_keyerror(lambda: p.current_value("S01", "temperature"), "current_value tras undo")


@_prueba(_OBLIGATORIAS, "14. Varios cambios sobre la misma variable")
def _(P):
    p = _cargar(P, ("S01", "temperature", 20), ("S01", "temperature", 25),
                ("S01", "temperature", 30))
    _procesar(p, 3)
    _eq(_valor(p, "S01", "temperature"), 30, "tras 3 cambios")
    for esperado in (25, 20, _NO):
        p.undo()
        _eq(_valor(p, "S01", "temperature"), esperado, "tras undo")


@_prueba(_OBLIGATORIAS, "15. add() con formato incorrecto")
def _(P):
    p = P()
    _espera_rechazo(p, ("S01", "temperature"), "2 componentes")
    _espera_rechazo(p, ("S01", "temperature", 1, 2), "4 componentes")
    _espera_rechazo(p, ("S01",), "1 componente")
    _espera_rechazo(p, (), "tupla vacia")


@_prueba(_OBLIGATORIAS, "16. add() con value no numerico")
def _(P):
    p = P()
    _espera_rechazo(p, ("S01", "temperature", "caliente"), "value str")
    _espera_rechazo(p, ("S01", "temperature", None), "value None")
    _espera_rechazo(p, ("S01", "temperature", [1]), "value lista")


@_prueba(_OBLIGATORIAS, "17. current_value() de un sensor/variable nunca procesado -> KeyError")
def _(P):
    p = P()
    _espera_keyerror(lambda: p.current_value("S99", "pressure"), "par nunca visto")
    p.add(("S01", "temperature", 20))
    _espera_keyerror(lambda: p.current_value("S01", "temperature"), "agregado pero sin procesar")


# ----------------------------------------------------------------- casos borde
@_prueba(_BORDE, "undo de una creacion entre actualizaciones de otra variable")
def _(P):
    p = _cargar(P, ("S01", "t", 1), ("S02", "t", 2), ("S01", "t", 3), ("S03", "h", 4))
    _procesar(p, 4)
    p.undo()
    _eq(_valor(p, "S03", "h"), _NO, "S03/h tras undo")
    _eq(_valor(p, "S01", "t"), 3, "S01/t tras undo")
    _eq(_valor(p, "S02", "t"), 2, "S02/t tras undo")
    p.undo()
    _eq(_valor(p, "S01", "t"), 1, "S01/t restaurado (3 -> 1)")
    _eq(_valor(p, "S02", "t"), 2, "S02/t intacto")
    p.undo()
    p.undo()
    for s, v in (("S01", "t"), ("S02", "t"), ("S03", "h")):
        _eq(_valor(p, s, v), _NO, f"{s}/{v} tras deshacer todo")
    _espera_empty(p.undo, "undo() tras deshacer todo")


@_prueba(_BORDE, "Sensores y variables distintos no se mezclan")
def _(P):
    p = _cargar(P, ("S01", "t", 1), ("S02", "t", 2), ("S01", "h", 3))
    _procesar(p, 3)
    p.add(("S01", "t", 10))
    p.process_next()
    _eq(_valor(p, "S01", "t"), 10, "S01/t")
    _eq(_valor(p, "S02", "t"), 2, "S02/t")
    _eq(_valor(p, "S01", "h"), 3, "S01/h")


@_prueba(_BORDE, "Acepta int y float; sigue funcionando tras un Empty")
def _(P):
    p = _cargar(P, ("S01", "t", 1), ("S01", "t", 2.5))
    _eq(p.pending(), 2, "pending() con int y float")
    _procesar(p, 2)
    _espera_empty(p.process_next, "process_next() con la cola vacia")
    _eq(_valor(p, "S01", "t"), 2.5, "valor tras el Empty")
    p.undo()
    _eq(_valor(p, "S01", "t"), 1, "undo tras el Empty")


# ----------------------------------------------------------------------- bonus
@_prueba(_BONUS, "redo() tras un undo")
def _(P):
    p = _cargar(P, ("S01", "temperature", 20), ("S01", "temperature", 25),
                ("S01", "temperature", 30))
    _procesar(p, 3)
    p.undo()
    _eq(_valor(p, "S01", "temperature"), 25, "tras undo")
    p.redo()
    _eq(_valor(p, "S01", "temperature"), 30, "tras redo")


@_prueba(_BONUS, "Varios undo y varios redo (orden inverso)")
def _(P):
    p = _cargar(P, ("S01", "temperature", 20), ("S01", "temperature", 25),
                ("S01", "temperature", 30))
    _procesar(p, 3)
    p.undo()
    p.undo()
    _eq(_valor(p, "S01", "temperature"), 20, "tras dos undo")
    p.redo()
    _eq(_valor(p, "S01", "temperature"), 25, "primer redo")
    p.redo()
    _eq(_valor(p, "S01", "temperature"), 30, "segundo redo")


@_prueba(_BONUS, "redo() recrea un dato que habia sido deshecho")
def _(P):
    p = _cargar(P, ("S01", "temperature", 23.5))
    p.process_next()
    p.undo()
    _eq(_valor(p, "S01", "temperature"), _NO, "tras undo")
    p.redo()
    _eq(_valor(p, "S01", "temperature"), 23.5, "tras redo")


# ---------------------------------------------------------------------- motor
def _donde(e):
    marcos = [f for f in traceback.extract_tb(e.__traceback__) if f.filename != _ARCHIVO]
    return f" (en {marcos[-1].name}, linea {marcos[-1].lineno})" if marcos else ""


def _correr(f, P, timeout):
    res = {}

    def objetivo():
        try:
            nota = f(P)
            res["estado"], res["msg"] = ("AVISO", nota) if isinstance(nota, str) else ("PASS", "")
        except AssertionError as e:
            res["estado"], res["msg"] = "FAIL", str(e) or "AssertionError" + _donde(e)
        except Exception as e:
            res["estado"] = "FAIL"
            res["msg"] = f"Excepcion inesperada {type(e).__name__}: {e}{_donde(e)}"

    hilo = threading.Thread(target=objetivo, daemon=True)
    hilo.start()
    hilo.join(timeout)
    if hilo.is_alive():
        return "FAIL", f"Tiempo excedido (> {timeout} s): posible bucle infinito"
    return res["estado"], res["msg"]


def _sha(texto):
    return hashlib.sha256(texto.encode("utf-8")).hexdigest()


def _normalizar(texto):
    """Ignora cambios de saltos de linea y espacios finales (correo, editores)."""
    return "\n".join(l.rstrip() for l in texto.replace("\r\n", "\n").split("\n")).strip()


def _hash_informe(cuerpo):
    return _sha(_normalizar(cuerpo) + _SALT)


def _fuente(clase):
    """Codigo de la clase: inspect.getsource o, en un cuaderno, la celda que la define."""
    try:
        return inspect.getsource(clase)
    except (OSError, TypeError):
        pass
    try:
        from IPython import get_ipython
        celdas = get_ipython().history_manager.input_hist_raw
        patron = re.compile(rf"^class\s+{re.escape(clase.__name__)}\b", re.M)
        for celda in reversed(celdas):          # la definicion mas reciente
            if patron.search(celda):
                return celda
    except Exception:
        pass
    return "(codigo fuente no disponible)"


def ejecutar(clase, estudiante, archivo=None, salida=None, timeout=_TIMEOUT, guardar=True):
    """Ejecuta las pruebas sobre `clase`, imprime el informe y lo guarda en un .txt.

    clase      : la clase DataProcessor del estudiante.
    estudiante : nombre completo (obligatorio; aparece en el informe y en el archivo).
    archivo    : ruta opcional del .ipynb/.py de la solucion; se incluye su hash SHA-256.
    salida     : ruta del .txt (por defecto resultados_<estudiante>.txt en la carpeta actual).
    timeout    : segundos maximos por prueba.
    guardar    : False solo imprime el resumen (sin codigo, hashes ni archivo .txt).
    """
    if not estudiante or not str(estudiante).strip():
        raise ValueError("Indique su nombre: ejecutar(DataProcessor, estudiante='Nombre Apellido')")
    estudiante = str(estudiante).strip()
    if estudiante.lower() == "nombre apellido":
        raise ValueError("Reemplace 'Nombre Apellido' por su nombre completo")

    secciones = [("Interfaz y restricciones", _INTERFAZ),
                 ("Pruebas obligatorias (1-17)", _OBLIGATORIAS),
                 ("Casos borde adicionales", _BORDE)]
    if hasattr(clase, "redo"):
        secciones.append(("Bonus: redo() (opcional)", _BONUS))

    L = ["EVALUACION - Data Stream Processor", "=" * 60,
         f"Estudiante : {estudiante}",
         f"Fecha      : {datetime.datetime.now():%Y-%m-%d %H:%M:%S}",
         f"Python     : {platform.python_version()} ({platform.system()})",
         f"Evaluador  : v{_VERSION}",
         f"Clase      : {clase.__name__} (modulo {clase.__module__})", ""]

    conteo = {}
    for titulo, pruebas in secciones:
        L += [f"== {titulo} ==", ""]
        c = {"PASS": 0, "FAIL": 0, "AVISO": 0}
        for nombre, f in pruebas:
            estado, msg = _correr(f, clase, timeout)
            c[estado] += 1
            L.append(f"[{estado:5s}] {nombre}")
            if msg:
                L.append(f"        -> {msg}")
        conteo[titulo] = c
        L += ["", f"   {titulo}: {c['PASS']}/{len(pruebas)} OK"
                  + (f", {c['AVISO']} aviso(s)" if c["AVISO"] else ""), ""]

    if not hasattr(clase, "redo"):
        L += ["== Bonus: redo() (opcional) ==", "", "   No implementado (no aplica).", ""]

    L += ["== RESUMEN ==", ""]
    for titulo, c in conteo.items():
        total = sum(c.values())
        L.append(f"   {titulo:32s} {c['PASS']:2d}/{total:2d} OK   {c['FAIL']} fallo(s)")
    nucleo = [conteo[t] for t, _ in secciones[:3]]
    L += ["", f"   Total sin bonus: {sum(c['PASS'] for c in nucleo)}/"
              f"{sum(sum(c.values()) for c in nucleo)} OK", ""]

    if not guardar:
        print("\n".join(L))
        return

    fuente = _fuente(clase)
    L += ["== CODIGO DE LA CLASE ==", "", fuente.rstrip(), ""]

    L += [_MARCA, f"SHA256 codigo de la clase : {_sha(_normalizar(fuente))}"]
    if archivo:
        L.append(f"SHA256 {Path(archivo).name}: "
                 f"{hashlib.sha256(Path(archivo).read_bytes()).hexdigest()}")
    cuerpo = "\n".join(L)
    informe = cuerpo + f"\nSHA256 de este informe    : {_hash_informe(cuerpo)}\n"

    if salida is None:
        ascii_ = unicodedata.normalize("NFKD", estudiante).encode("ascii", "ignore").decode()
        slug = re.sub(r"[^A-Za-z0-9]+", "_", ascii_).strip("_") or "estudiante"
        salida = Path.cwd() / f"resultados_{slug}.txt"
    salida = Path(salida)
    salida.write_text(informe, encoding="utf-8", newline="\n")

    print(informe)
    print(f">>> Informe guardado en: {salida.resolve()}")
    print(">>> Envie ese archivo .txt al profesor (sin editarlo).")


# ==== FIN DEL NUCLEO (lo de abajo no va en la celda) ====
import argparse
import importlib.util


def verificar(ruta):
    """Comprueba que un informe no fue modificado. Devuelve True si es integro."""
    texto = _normalizar(Path(ruta).read_text(encoding="utf-8"))
    cuerpo, _, cola = texto.partition("SHA256 de este informe    :")
    if not cola:
        print("No se encontro la linea de integridad.")
        return False
    ok_informe = _hash_informe(cuerpo.rstrip()) == cola.strip()
    m = re.search(r"== CODIGO DE LA CLASE ==\n\n(.*?)\n\n" + re.escape(_MARCA), texto, re.S)
    m2 = re.search(r"SHA256 codigo de la clase : (\w+)", texto)
    ok_codigo = bool(m and m2 and _sha(_normalizar(m.group(1))) == m2.group(1))
    print(f"Informe sin modificar : {'SI' if ok_informe else 'NO'}")
    print(f"Codigo coincide con hash: {'SI' if ok_codigo else 'NO'}")
    return ok_informe and ok_codigo


_FIN = "# ==== FIN DEL NUCLEO (lo de abajo no va en la celda) ===="
_CELDA = Path(__file__).with_name("celda_evaluador.py")

_CABECERA = """# ==============================================================================
#  EVALUADOR - Data Stream Processor   (v%s)
#
#  1. Copie esta celda COMPLETA al final de su cuaderno, DESPUES de la celda
#     que define la clase DataProcessor.
#  2. Escriba su nombre completo en la ULTIMA linea de la celda.
#  3. Ejecute la celda. Se crea resultados_<su_nombre>.txt en la carpeta del
#     cuaderno: envielo al profesor sin editarlo.
#
#  (Celda generada automaticamente desde evaluador.py: no la modifique.)
# ==============================================================================

"""

_PIE = """

# ================================ EJECUTAR ====================================
# Escriba su nombre completo entre las comillas y ejecute la celda.
ejecutar(DataProcessor, estudiante="Nombre Apellido")
"""


def texto_celda():
    """Texto de la celda pegable: el nucleo de este archivo mas la llamada final."""
    fuente = Path(__file__).read_text(encoding="utf-8").replace("\r\n", "\n")
    nucleo = fuente.split(_FIN)[0]
    nucleo = re.sub(r'\A""".*?"""\n', "", nucleo, count=1, flags=re.S)   # sin docstring del modulo
    return _CABECERA % _VERSION + nucleo.strip("\n") + "\n" + _PIE


def generar_celda(comprobar=False):
    """Escribe celda_evaluador.py. Con comprobar=True solo verifica que este al dia."""
    texto = texto_celda()
    if comprobar:
        actual = None
        if _CELDA.exists():
            actual = _CELDA.read_text(encoding="utf-8").replace("\r\n", "\n")
        al_dia = actual == texto
        print(f"{_CELDA.name}: {'al dia' if al_dia else 'DESACTUALIZADA (ejecute --celda)'}")
        return al_dia
    _CELDA.write_text(texto, encoding="utf-8", newline="\n")
    print(f"Generada {_CELDA}  ({texto.count(chr(10))} lineas)")
    return True


def _cargar_clase(ruta, nombre):
    ruta = Path(ruta).resolve()
    raiz = ruta.parent
    while not (raiz / "goodrich").is_dir() and raiz != raiz.parent:
        raiz = raiz.parent
    for p in (str(ruta.parent), str(raiz)):
        if p not in sys.path:
            sys.path.insert(0, p)
    spec = importlib.util.spec_from_file_location(ruta.stem, ruta)
    modulo = importlib.util.module_from_spec(spec)
    sys.modules[ruta.stem] = modulo
    spec.loader.exec_module(modulo)
    return getattr(modulo, nombre)


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description="Evaluador de Data Stream Processor")
    ap.add_argument("solucion", nargs="?", help="archivo .py con la clase DataProcessor")
    ap.add_argument("--estudiante", help="nombre del estudiante")
    ap.add_argument("--clase", default="DataProcessor")
    ap.add_argument("--verificar", metavar="TXT", help="verifica la integridad de un informe")
    ap.add_argument("--celda", action="store_true", help="genera celda_evaluador.py")
    ap.add_argument("--comprobar", action="store_true", help="con --celda: solo comprueba que este al dia")
    a = ap.parse_args()
    if a.celda:
        sys.exit(0 if generar_celda(a.comprobar) else 1)
    if a.verificar:
        sys.exit(0 if verificar(a.verificar) else 1)
    if not a.solucion or not a.estudiante:
        ap.error("indique el archivo de la solucion y --estudiante")
    ejecutar(_cargar_clase(a.solucion, a.clase), a.estudiante, archivo=a.solucion)
