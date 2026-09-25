%%writefile heap.py
<<<<<<< HEAD
=======


>>>>>>> 1c138f0 (Solucion de ejercicio Heap)
class Heap:

    def __init__(self):
        self.arreglo = [float('-inf')]

    def insert(self, valor):
<<<<<<< HEAD
        self.arreglo.append(valor)
=======
        # Insertamos el elemento al final del arreglo
        self.arreglo.append(valor)
        # Hacemos el "percolate-up" (subir el elemento si es menor que su padre)
>>>>>>> 1c138f0 (Solucion de ejercicio Heap)
        i = len(self.arreglo) - 1
        while i > 1:
            padre = i // 2
            if self.arreglo[i] < self.arreglo[padre]:
<<<<<<< HEAD
=======
                # Intercambiamos si es menor
>>>>>>> 1c138f0 (Solucion de ejercicio Heap)
                self.arreglo[i], self.arreglo[padre] = self.arreglo[padre], self.arreglo[i]
                i = padre
            else:
                break

    def remove_smallest(self):
        if len(self.arreglo) <= 1:
            return None
        if len(self.arreglo) == 2:
            return self.arreglo.pop()
        
<<<<<<< HEAD
        minimo = self.arreglo[1]
        
        self.arreglo[1] = self.arreglo.pop()
        
=======
        # Guardamos la raíz (el menor) para retornarlo si es necesario
        minimo = self.arreglo[1]
        
        # Pasamos el último elemento a la raíz y eliminamos el final
        self.arreglo[1] = self.arreglo.pop()
        
        # Hacemos el "percolate-down" (hundir el elemento)
>>>>>>> 1c138f0 (Solucion de ejercicio Heap)
        i = 1
        n = len(self.arreglo) - 1
        while 2 * i <= n:
            hijo_izq = 2 * i
            hijo_der = 2 * i + 1
            menor_hijo = hijo_izq
            
            if hijo_der <= n and self.arreglo[hijo_der] < self.arreglo[hijo_izq]:
                menor_hijo = hijo_der
                
            if self.arreglo[menor_hijo] < self.arreglo[i]:
                self.arreglo[i], self.arreglo[menor_hijo] = self.arreglo[menor_hijo], self.arreglo[i]
                i = menor_hijo
            else:
                break
        return minimo

    def build_heap(self, lista):
<<<<<<< HEAD
        self.arreglo = [float('-inf')] + list(lista)
=======
        # Colocamos el centinela y los elementos de la lista
        self.arreglo = [float('-inf')] + list(lista)
        # Aplicamos sift-down desde el último nodo padre hasta la raíz
>>>>>>> 1c138f0 (Solucion de ejercicio Heap)
        n = len(self.arreglo) - 1
        for i in range(n // 2, 0, -1):
            curr = i
            while 2 * curr <= n:
                hijo_izq = 2 * curr
                hijo_der = 2 * curr + 1
                menor_hijo = hijo_izq
                
                if hijo_der <= n and self.arreglo[hijo_der] < self.arreglo[hijo_izq]:
                    menor_hijo = hijo_der
                    
                if self.arreglo[menor_hijo] < self.arreglo[curr]:
                    self.arreglo[curr], self.arreglo[menor_hijo] = self.arreglo[menor_hijo], self.arreglo[curr]
                    curr = menor_hijo
                else:
                    break
