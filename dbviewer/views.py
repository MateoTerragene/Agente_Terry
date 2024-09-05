from django.shortcuts import render
from django.db import connection
from django.contrib.auth.decorators import login_required
from django.http import HttpResponseBadRequest
import logging
from openai import OpenAI
import os 
from django.contrib.auth.mixins import LoginRequiredMixin
from django.views import View
from django.http import HttpResponseBadRequest
import pandas as pd
from django.http import HttpResponse
# Configurar el logger
logger = logging.getLogger(__name__)
client= OpenAI()
client = OpenAI(api_key=os.getenv('OPENAI_API_KEY'))




# Configurar el logger
logger = logging.getLogger(__name__)

# Configurar OpenAI API
client.api_key = os.getenv('OPENAI_API_KEY')

class DBViewerView(LoginRequiredMixin, View):
    template_name = ''
    def export_to_excel(self, columns, rows, file_name='export.xlsx'):
        """Función para exportar los datos de una tabla a formato Excel."""
        df = pd.DataFrame(rows, columns=columns)
        response = HttpResponse(content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
        response['Content-Disposition'] = f'attachment; filename={file_name}'
        df.to_excel(response, index=False, engine='openpyxl')
        return response
    
    def get_tables(self):
        """Obtener todas las tablas disponibles en la base de datos."""
        with connection.cursor() as cursor:
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
            tables = [row[0] for row in cursor.fetchall()]
            logger.info(f"Tablas disponibles: {tables}")
        return tables
    def get_table_data(self, table_name):
        """Obtener columnas y filas de una tabla específica."""
        query = f"SELECT * FROM {table_name}"
        with connection.cursor() as cursor:
            cursor.execute(query)
            columns = [col[0] for col in cursor.description]
            rows = cursor.fetchall()

        # Devuelve los datos de la tabla (columnas y filas)
        return {'columns': columns, 'rows': rows}
    def render_response(self, request, context):
        """Método de ayuda para renderizar la respuesta."""
        return render(request, self.template_name, context)


class ShowTablesView(DBViewerView):
    template_name = 'dbviewer/show_tables.html'

    def get(self, request):
        tables = self.get_tables()
        return self.render_response(request, {'tables': tables})


class CustomSQLQueryView(DBViewerView):
    template_name = 'dbviewer/custom_sql_query.html'

    def get(self, request):
        table_name = request.GET.get('table_name')

        # Si hay un table_name en la solicitud, significa que es una solicitud AJAX
        if table_name:
            table_data = self.get_table_data(table_name)
            return render(request, 'dbviewer/table_content.html', {
                'columns': table_data['columns'],
                'rows': table_data['rows']
            })
        
        # Si no es una solicitud AJAX, renderizar la página completa
        return self.render_response(request, {
            'custom_query': None,
            'columns': [],
            'rows': [],
            'tables': self.get_tables(),
            'error_message': None,  # Inicializamos sin mensaje de error
        })

    def post(self, request):
        custom_query = request.POST.get("custom_query", "").strip()
        if not custom_query:
            return self.render_response(request, {
                'custom_query': custom_query,
                'columns': [],
                'rows': [],
                'tables': self.get_tables(),
                'error_message': "La consulta SQL no puede estar vacía."
            })

        columns = []
        rows = []
        error_message = None

        try:
            with connection.cursor() as cursor:
                cursor.execute(custom_query)
                if cursor.description:
                    columns = [col[0] for col in cursor.description]
                    rows = cursor.fetchall()
                else:
                    error_message = "La consulta no devolvió resultados."
        except Exception as e:
            logger.error(f"Error al ejecutar la consulta: {str(e)}")
            error_message = f"Error en la consulta SQL: {str(e)}"

        # Si el usuario solicita la descarga en Excel
        if 'download_excel' in request.POST and not error_message:
            return self.export_to_excel(columns, rows, 'custom_sql_query.xlsx')

        return self.render_response(request, {
            'custom_query': custom_query,
            'columns': columns,
            'rows': rows,
            'tables': self.get_tables(),
            'error_message': error_message  # Mostramos el mensaje de error en pantalla
        })


    def get_table_data(self, table_name):
        """Método para obtener solo el contenido de la tabla seleccionada"""
        query = f"SELECT * FROM {table_name}"
        with connection.cursor() as cursor:
            cursor.execute(query)
            columns = [col[0] for col in cursor.description]
            rows = cursor.fetchall()

        # Devuelve los datos de la tabla (columnas y filas)
        return {'columns': columns, 'rows': rows}

class IntelligentQueryView(DBViewerView):
    template_name = 'dbviewer/intelligent_query.html'

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        # Definir el system prompt como un atributo de la instancia
        self.system_prompt = """
        Eres un asistente que genera consultas SQL a partir de las preguntas de los usuarios. 
        Las funcionalidades del chatbot incluyen:
        - Responder consultas técnicas.
        - Devolver documentos (COA, IFU, SDS, DP, CC, FDA, ISO).
        - Generar reclamos.
        - Generar oportunidades de compra.
        Los documentos solicitados se almacenan en la tabla `File_Manager_documentrequest`
        - `documento`: tipo de documento solicitado (COA, IFU, SDS, DP, CC, FDA, ISO).
        - `producto`: es el producto del cual se solicita el documento
        - `lote`: es el lote especifico que se necesita
        - `link`: es el enlace que lleva al documento solicitado.  
        Las consultas se almacenan en la tabla `Module_Manager_userinteraction` con las siguientes columnas:
        - `id`: Identificador único de la consulta.
        - `thread_id`: Número de hilo o thread.
        - `date`: Fecha de la consulta.
        - `endpoint`: El canal a través del cual se realizó la consulta (`classifyqueryview` para la web, `whatsappqueryview` para WhatsApp).
        - `user_id`: ID del usuario.
        - `user_login`: Nombre de usuario.
        - `user_email`: Correo electrónico del usuario.
        - `display_name`: Nombre de pantalla del usuario.
        - `query`: Consulta realizada por el usuario.
        - `response`: Respuesta proporcionada por el chatbot.
        - `task_type`: Tipo de tarea, que puede ser:
            'technical_query': Responder consultas técnicas.
            'fileRequest': Devolver documentos.
            'complaint':Generar reclamos.
            'purchase_opportunity': Generar oportunidades de compra.
        - `phone_number`: Número de teléfono de WhatsApp.

        Los documentos disponibles son: COA, IFU, SDS, DP, CC, FDA, ISO.
       
        Genera una consulta SQL que corresponda a la pregunta del usuario utilizando esta información.
        Basándote en la información anterior, genera una consulta SQL válida. **Responde únicamente con la consulta SQL sin explicaciones adicionales.**
        """
        #  Los productos disponibles son: [Lista completa de productos].

    def post(self, request):
        instruction = request.POST.get("instruction", "").strip()
        sql_query = request.POST.get("generated_sql", None)  # SQL generado previamente
        error_message = None

        # Si se solicitó descargar Excel
        if 'download_excel' in request.POST:
            if sql_query:
                columns = []
                rows = []
                try:
                    with connection.cursor() as cursor:
                        cursor.execute(sql_query)
                        if cursor.description:
                            columns = [col[0] for col in cursor.description]
                            rows = cursor.fetchall()
                    return self.export_to_excel(columns, rows, 'intelligent_query.xlsx')
                except Exception as e:
                    logger.error(f"Error al ejecutar la consulta SQL para descarga en Excel: {str(e)}")
                    error_message = f"Error al ejecutar la consulta SQL para descarga en Excel: {str(e)}"

            return self.render_response(request, {
                'sql_query': sql_query,
                'columns': [],
                'rows': [],
                'tables': self.get_tables(),
                'error_message': "No hay SQL generada para descargar."
            })

        # Si no se proporcionó una consulta previa, generar una nueva
        if not sql_query:
            if not instruction:
                return self.render_response(request, {
                    'sql_query': None,
                    'columns': [],
                    'rows': [],
                    'tables': self.get_tables(),
                    'error_message': "La instrucción no puede estar vacía."
                })
        # Definir el user prompt como un atributo de la instancia
        self.user_prompt = f"""
        El usuario pregunta: {instruction}.
        Basándote en la siguiente información, elabora una consulta SQL válida:

        Funcionalidades del sistema:
        1. Responder consultas técnicas.
        2. Devolver documentos (COA, IFU, SDS, DP, CC, FDA, ISO).
        3. Generar reclamos.
        4. Generar oportunidades de compra.

        Información disponible:
        - Tabla: `Module_Manager_userinteraction`.
        - Campos disponibles: `id`, `thread_id`, `date`, `endpoint`, `user_id`, `user_login`, `user_email`, `display_name`, `query`, `response`, `task_type`, `phone_number`.
        - Documentos disponibles: COA, IFU, SDS, DP, CC, FDA, ISO.
        - Productos disponibles: [Lista de productos].

        Genera la consulta SQL que corresponda a la pregunta del usuario.
        """
        
        sql_query = None
        columns = []
        rows = []

        try:
            # Llamar a OpenAI para generar la consulta SQL
            response = client.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=[
                    {"role": "system", "content": self.system_prompt},
                    {"role": "user", "content": self.user_prompt}
                ]
            )
            sql_query = response.choices[0].message.content.strip()

            # Ejecutar la consulta SQL generada por el LLM
            with connection.cursor() as cursor:
                cursor.execute(sql_query)
                if cursor.description:
                    columns = [col[0] for col in cursor.description]
                    rows = cursor.fetchall()
                else:
                    return HttpResponseBadRequest("La consulta no devolvió resultados.")
        except Exception as e:
            logger.error(f"Error al generar o ejecutar la consulta SQL: {str(e)}")
            return HttpResponseBadRequest(f"Error al ejecutar la consulta SQL: {str(e)}")
                # Si el usuario solicita la descarga en Excel
        if 'download_excel' in request.POST:
            return self.export_to_excel(columns, rows, 'intelligent_query.xlsx')
        return self.render_response(request, {
            'tables': self.get_tables(),    
            'sql_query': sql_query,
            'columns': columns,
            'rows': rows
        })

    def get(self, request):
        table_name = request.GET.get('table_name')

        # Si hay un table_name en la solicitud, significa que es una solicitud AJAX
        if table_name:
            table_data = self.get_table_data(table_name)
            return render(request, 'dbviewer/table_content.html', {
                'columns': table_data['columns'],
                'rows': table_data['rows']
            })

        # Si no es una solicitud AJAX, renderizar la página completa
        return self.render_response(request, {
            'sql_query': None,
            'columns': [],
            'rows': [],
            'tables': self.get_tables(),
        })

    
class ShowTableContentView(DBViewerView):
    template_name = 'dbviewer/show_table_content.html'

    def get(self, request, table_name):
        filters = {}
        # Excluir el parámetro 'download_excel' de los filtros
        for key, value in request.GET.items():
            if key != 'download_excel' and value:
                filters[key] = value

        query = f"SELECT * FROM {table_name}"
        if filters:
            conditions = [f"{column} LIKE %s" for column in filters.keys()]
            query += f" WHERE {' AND '.join(conditions)}"

        with connection.cursor() as cursor:
            if filters:
                cursor.execute(query, [f"%{v}%" for v in filters.values()])
            else:
                cursor.execute(query)

            columns = [col[0] for col in cursor.description]
            rows = cursor.fetchall()

        # Si el usuario solicita la descarga en Excel
        if 'download_excel' in request.GET:
            return self.export_to_excel(columns, rows, f'{table_name}.xlsx')

        return self.render_response(request, {
            'table_name': table_name,
            'columns': columns,
            'rows': rows,
            'filters': filters
        })
