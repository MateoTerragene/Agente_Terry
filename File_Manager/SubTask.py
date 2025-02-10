from Module_Manager.Tasks import SubTask


class FMSubTask(SubTask):
    def __init__(self):
        super().__init__()
        self._documento = ""
        self._producto = ""
        self._lote = ""
        self._NS = ""
        self.required_fields = ["documento"]  # Lista para almacenar los campos obligatorios
    @property
    def documento(self):
        return self._documento

    @documento.setter
    def documento(self, value):
        if not self._documento:  # Solo permite asignar si está vacío
            self._documento = value
        else:
            print("El documento ya está asignado y no puede ser modificado.")

    @property
    def producto(self):
        return self._producto

    @producto.setter
    def producto(self, value):
        if not self._producto:  # Solo permite asignar si está vacío
            self._producto = value
        else:
            print("El producto ya está asignado y no puede ser modificado.")

    @property
    def lote(self):
        return self._lote

    @lote.setter
    def lote(self, value):
        if not self._lote:  # Solo permite asignar si está vacío
            self._lote = value
        else:
            print("El lote ya está asignado y no puede ser modificado.")

    @property
    def NS(self):
        return self._NS

    @NS.setter
    def NS(self, value):
        if not self._NS:  # Solo permite asignar si está vacío
            self._NS = value
        else:
            print("El número de serie ya está asignado y no puede ser modificado.")
