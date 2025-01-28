# file_manager/subtasks.py

from Module_Manager.Tasks import SubTask


class FMSubTask(SubTask):
    def __init__(self):
        super().__init__()
        self.documento=""
        self.producto=""
        self.lote=""
        self.NS=""
        