# file_manager/services.py

from .subtasks import FMSubTask

class FileManager:
    def file_request(self, context=None):
        # Lógica para manejar la solicitud de archivos
        if not context or 'lote' not in context:
            return {
                'status': 'waiting_for_info',
                'message': 'Para obtener el COA necesito el Lote del indicador',
                'context': context
            }
        else:
            # Lógica para obtener el documento COA
            document = self.retrieve_document('COA', context)
            return {
                'status': 'completed',
                'document': document
            }

    def retrieve_document(self, document_type, context):
        # Lógica para recuperar el documento solicitado
        return f"{document_type} document for {context['product']} with lote {context['lote']}"

    def create_and_resolve_task(self, task):
        # Crear y resolver subtareas basadas en la solicitud inicial
        if task.task_type == "fileRequest":
            subtask1 = FMSubTask('COA')
            subtask1.add_variable('product', 'BT20')
            task.add_subtask(subtask1)

            subtask2 = FMSubTask('IFU')
            subtask2.add_variable('product', 'BT10')
            task.add_subtask(subtask2)

            self.resolve_task(task)

    def resolve_task(self, task):
        for subtask in task.subtasks:
            if subtask.subtask_type == 'COA':
                response = self.file_request(subtask.variables)
                if response['status'] == 'waiting_for_info':
                    subtask.update_state('waiting_for_info')
                    subtask.set_response(response['message'])
                else:
                    subtask.update_state('completed')
                    subtask.set_response(response['document'])
            elif subtask.subtask_type == 'IFU':
                response = self.file_request(subtask.variables)
                subtask.update_state('completed')
                subtask.set_response(response['document'])
            # Agregar más lógica de resolución según sea necesario

        # Actualizar el estado de la tarea principal cuando todas las subtareas estén completas
        if all(subtask.state == 'completed' for subtask in task.subtasks):
            task.update_state('completed')
            task.set_response("All subtasks completed")
