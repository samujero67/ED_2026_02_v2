import math
import matplotlib.pyplot as plt


class Heap:

    def __init__(self):
        self.arreglo = [float('-inf')]
        self.ultima_imagen = None    # última figura mostrada (para guardarla en PNG)

    # ------------------------------------------------------------------
    # Operaciones de la página
    # ------------------------------------------------------------------

    def insert(self, valor, imagen=False):
        """Botón Insert: agrega `valor` al final y lo sube (sift up)."""
        self._validar_valor(valor)
        self.arreglo.append(valor)
        self._subir(len(self.arreglo) - 1)
        if imagen:
            self._mostrar_imagen()

    def remove_smallest(self, imagen=False):
        """Botón Remove Smallest: quita y devuelve la raíz (el mínimo).

        Si el heap está vacío no modifica nada y devuelve None,
        igual que la página, que solo avisa que no hay qué quitar.
        """
        if len(self.arreglo) == 1:          # solo queda el -INF
            menor = None
        else:
            menor = self.arreglo[1]
            ultimo = self.arreglo.pop()     # se saca la última hoja
            if len(self.arreglo) > 1:       # si quedan elementos,
                self.arreglo[1] = ultimo    # la última hoja pasa a la raíz
                self._bajar(1)              # y se baja (heapify)
        if imagen:
            self._mostrar_imagen()
        return menor

    def build_heap(self, lista, imagen=False):
        """Botón BuildHeap: reemplaza el contenido por `lista` y lo
        convierte en heap bajando cada nodo interno, desde el último
        padre (n // 2) hasta la raíz (construcción de abajo hacia arriba).
        """
        if not isinstance(lista, list):
            raise TypeError("build_heap espera una lista, recibió "
                            + type(lista).__name__)
        for valor in lista:                 # se valida todo antes de
            self._validar_valor(valor)      # tocar el heap actual
        # El + crea una lista NUEVA: la lista del usuario no se modifica
        self.arreglo = [float('-inf')] + lista
        n = len(self.arreglo) - 1
        for i in range(n // 2, 0, -1):
            self._bajar(i)
        if imagen:
            self._mostrar_imagen()

    # ------------------------------------------------------------------
    # Auxiliares del heap
    # ------------------------------------------------------------------

    def _validar_valor(self, valor):
        """Solo se aceptan números comparables entre sí (int o float)."""
        if isinstance(valor, bool) or not isinstance(valor, (int, float)):
            raise TypeError("El heap solo acepta números, recibió "
                            + repr(valor))
        if valor != valor:                  # NaN es el único valor distinto de sí mismo
            raise ValueError("El heap no acepta NaN: no se puede comparar")

    def _intercambiar(self, i, j):
        self.arreglo[i], self.arreglo[j] = self.arreglo[j], self.arreglo[i]

    def _subir(self, i):
        """Sube el elemento de la posición i mientras sea MENOR que su padre.
        Con valores iguales no se intercambia (igual que la página)."""
        while i > 1 and self.arreglo[i] < self.arreglo[i // 2]:
            self._intercambiar(i, i // 2)
            i = i // 2

    def _bajar(self, i):
        """Baja el elemento de la posición i (heapify) mientras sea MAYOR
        que su hijo menor. Si los dos hijos son iguales se elige el
        izquierdo (igual que la página)."""
        n = len(self.arreglo) - 1
        while 2 * i <= n:                   # mientras i tenga al menos un hijo
            menor = 2 * i                   # hijo izquierdo
            if 2 * i + 1 <= n and self.arreglo[2 * i + 1] < self.arreglo[2 * i]:
                menor = 2 * i + 1           # el derecho es estrictamente menor
            if self.arreglo[i] > self.arreglo[menor]:
                self._intercambiar(i, menor)
                i = menor
            else:
                break

    # ------------------------------------------------------------------
    # Imagen del árbol
    # ------------------------------------------------------------------

    def _posicion(self, i):
        """Coordenadas (x, y) del nodo en la posición i del arreglo.

        El nivel es floor(log2(i)): la raíz (i=1) está en el nivel 0,
        las posiciones 2 y 3 en el nivel 1, de 4 a 7 en el nivel 2...
        Cada nivel divide el ancho [0, 1] en 2**nivel casillas iguales y
        el nodo se dibuja en el centro de la suya, así los hijos
        izquierdos quedan a la izquierda y los derechos a la derecha.
        """
        nivel = int(math.log2(i))
        primero_del_nivel = 2 ** nivel
        casilla = i - primero_del_nivel
        x = (casilla + 0.5) / primero_del_nivel
        y = -nivel
        return x, y

    def _dibujar(self):
        """Construye y devuelve la figura del árbol (estado actual)."""
        n = len(self.arreglo) - 1
        niveles = int(math.log2(n)) + 1 if n > 0 else 1
        ancho = min(max(4, 0.9 * 2 ** (niveles - 1)), 20)
        fig, ax = plt.subplots(figsize=(ancho, 1.3 * niveles + 0.5))
        ax.axis('off')

        if n == 0:
            ax.text(0.5, 0.5, "Heap vacío", ha='center', va='center',
                    fontsize=14, transform=ax.transAxes)
            return fig

        # Aristas: de cada nodo i (desde 2) hacia su padre i // 2
        for i in range(2, n + 1):
            x1, y1 = self._posicion(i // 2)
            x2, y2 = self._posicion(i)
            ax.plot([x1, x2], [y1, y2], color='black', linewidth=1, zorder=1)

        # Nodos: un círculo con su valor (se omite la posición 0, el -INF)
        for i in range(1, n + 1):
            x, y = self._posicion(i)
            ax.scatter(x, y, s=900, color='white', edgecolors='black', zorder=2)
            ax.text(x, y, str(self.arreglo[i]), ha='center', va='center',
                    fontsize=10, zorder=3)

        ax.set_xlim(-0.02, 1.02)
        ax.set_ylim(-niveles + 0.5, 0.5)
        return fig

    def _mostrar_imagen(self):
        fig = self._dibujar()
        self.ultima_imagen = fig    # se guarda para poder hacer savefig después
        plt.show()
        plt.close(fig)      # la quita de pyplot; el objeto sigue sirviendo para savefig

    def __repr__(self):
        return "Heap(" + str(self.arreglo) + ")"
