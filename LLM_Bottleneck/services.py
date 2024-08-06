class LLM_Bottleneck:
    def __init__(self, llm):
        self.llm = llm
        self.tasks = []
        self.responses = []

    def receive_task(self, task):
        response = task.get_response()
        self.responses.append(response)
        self.tasks.append(task)

    def generate_response(self, query):
        # Aquí podrías usar self.llm para generar una respuesta
        # combinando la consulta (query) y las respuestas almacenadas.
        combined_input = query + "\n\n" + "\n".join(self.responses)
        final_response = self.llm.generate(combined_input)
        return final_response

    def beautify_sentence(self, sentence):
        # Usar el LLM para reformatear la oración
        beautified_sentence = self.llm.beautify(sentence)
        return beautified_sentence