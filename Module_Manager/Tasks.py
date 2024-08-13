# module_manager/tasks.py
import copy
class Task:
    def __init__(self):
        self.task_type = None
        self.state = 'pending'  # or 'in_progress', 'waiting_for_info', 'completed'
        self.subtasks = []
        self.context = {}
        self.response = None  # This can be a single response or a dictionary of responses

    def add_subtask(self, subtask):
        self.subtasks.append(subtask)

    # def update_state(self, state):
    #     self.state = state
    def update_state(self, state=None):
        if state is not None:
            self.state = state
        else:
            # Determinar el estado basado en las subtasks
            if all(subtask.state == 'completed' for subtask in self.subtasks):
                self.state = 'completed'
            elif any(subtask.state == 'pending' for subtask in self.subtasks):
                self.state = 'pending'
            elif any(subtask.state == 'in_progress' for subtask in self.subtasks):
                self.state = 'in_progress'
            else:
                # Si no hay subtasks, mantener el estado actual o establecer un estado por defecto
                self.state = 'pending' if not self.subtasks else self.state
                
    def get_state(self):
        if not self.subtasks:
            return self.state
        else:
            if any(subtask.state != 'completed' for subtask in self.subtasks):
                return 'in_progress'
            else:
                return 'completed' 
    def update_context(self, context):
        self.context.update(context)
    def set_type(self, type):
        self.task_type=type
    def set_response(self, response, indice=None):
        if indice is not None:
            if indice < len(self.subtasks):
                self.subtasks[indice].set_response(response)
            else:
                raise IndexError("Subtask index out of range")
        else:
            self.response = response

    def get_response(self, indice=None):
        if len(self.subtasks)==0:
                return self.response
        else:
            if indice is not None:
                if indice < len(self.subtasks):
                    return self.subtasks[indice].get_response()
            else:
                responses = ""
                for i, subtask in enumerate(self.subtasks):
                    subtask_response = subtask.get_response()
                    if subtask_response:  # Ensure the subtask has a response
                        responses += f"{subtask_response} "  # Concatenate responses with a space
                return responses.strip()  # Remove any trailing spaces

    def get_next_pending_subtask(self):
        for subtask in self.subtasks:
            if subtask.state == 'pending':
                return subtask
        return None
    def clone(self):
        return copy.deepcopy(self)
    
class SubTask:
    def __init__(self):
        self.state = 'pending'  # or 'in_progress', 'waiting_for_info', 'completed'
        self.response = None

    def update_state(self, state):
        self.state = state

    def set_response(self, response):
        self.response = response

    def get_response(self):
        return self.response

    # def resolve(self):
    #     raise NotImplementedError("This method should be overridden by subclasses")