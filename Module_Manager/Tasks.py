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

    def update_state(self, state):
        self.state = state

    def get_state(self):
        return(self.state)

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
    def __init__(self, subtask_type):
        self.subtask_type = subtask_type
        self.state = 'pending'  # or 'in_progress', 'waiting_for_info', 'completed'
        self.variables = {}
        self.response = None

    def update_state(self, state):
        self.state = state

    def add_variable(self, key, value):
        self.variables[key] = value

    def get_variable(self, key):
        return self.variables.get(key)
    
    def set_response(self, response):
        self.response = response

    def get_response(self):
        return self.response

    # def resolve(self):
    #     raise NotImplementedError("This method should be overridden by subclasses")