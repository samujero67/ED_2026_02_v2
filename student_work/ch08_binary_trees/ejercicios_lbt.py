from goodrich.ch08.linked_binary_tree import LinkedBinaryTree


def es_completo(T):
    if T.is_empty():
        return True

    cola = [T.root()]
    encontro_hueco = False

    while cola:
        nodo = cola.pop(0)

        izq = T.left(nodo)
        if izq:
            if encontro_hueco:
                return False
            cola.append(izq)
        else:
            encontro_hueco = True

        der = T.right(nodo)
        if der:
            if encontro_hueco:
                return False
            cola.append(der)
        else:
            encontro_hueco = True

    return True


def camino(T, p, q):
    ancestros_p = []
    actual = p
    while True:
        ancestros_p.append(actual)
        if T.is_root(actual):
            break
        actual = T.parent(actual)

    ancestros_q = []
    actual = q
    while True:
        ancestros_q.append(actual)
        if T.is_root(actual):
            break
        actual = T.parent(actual)

    lca = None
    for nodo_p in ancestros_p:
        if nodo_p in ancestros_q:
            lca = nodo_p
            break

    idx_p = ancestros_p.index(lca)
    sub_p = ancestros_p[:idx_p + 1]

    idx_q = ancestros_q.index(lca)
    sub_q = ancestros_q[:idx_q]
    sub_q.reverse()

    camino_nodos = sub_p + sub_q

    elementos = [str(nodo.element()) for nodo in camino_nodos]
    return " -> ".join(elementos)


if __name__ == "__main__":
    pass
