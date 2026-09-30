class UnsortedTableMap:
    def __init__(self):
        self._table = []

    def _buscar(self, k):
        for j in range(len(self._table)):
            if self._table[j][0] == k:
                return j
        return -1

    def __len__(self):
        return len(self._table)

    def __getitem__(self, k):
        j = self._buscar(k)
        if j == -1:
            raise KeyError(k)
        return self._table[j][1]

    def __setitem__(self, k, v):
        j = self._buscar(k)
        if j == -1:
            self._table.append([k, v])
        else:
            self._table[j][1] = v

    def __delitem__(self, k):
        j = self._buscar(k)
        if j == -1:
            raise KeyError(k)
        self._table.pop(j)

    def __contains__(self, k):
        return self._buscar(k) != -1

    def __iter__(self):
        for item in self._table:
            yield item[0]

    def __eq__(self, otro):
        if len(self) != len(otro):
            return False
        for item in self._table:
            k, v = item[0], item[1]
            if k not in otro or otro[k] != v:
                return False
        return True

    def __repr__(self):
        return '{' + ', '.join(f'{k!r}: {v!r}' for k, v in self._table) + '}'
