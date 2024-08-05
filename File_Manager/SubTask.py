# file_manager/subtasks.py

from Module_Manager.Tasks import SubTask


class FMSubTask(SubTask):
    def __init__(self, subtask_type):
        super().__init__(subtask_type)
