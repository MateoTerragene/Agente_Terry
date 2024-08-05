# module_manager/tasks.py

class Task:
    def __init__(self, task_type):
        self.task_type = task_type
        self.state = 'pending'  # or 'in_progress', 'waiting_for_info', 'completed'
        self.subtasks = []
        self.context = {}
        self.response = None

    def add_subtask(self, subtask):
        self.subtasks.append(subtask)

    def update_state(self, state):
        self.state = state

    def update_context(self, context):
        self.context.update(context)

    def set_response(self, response):
        self.response = response

    def get_next_pending_subtask(self):
        for subtask in self.subtasks:
            if subtask.state == 'pending':
                return subtask
        return None

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