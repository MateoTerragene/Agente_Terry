document.addEventListener('DOMContentLoaded', function () {
    const userId = document.getElementById('user_id').value;

    // Función para enviar consulta con texto personalizado o el input del usuario
    async function sendQuery(prefixedQuery = '') {
        const query = prefixedQuery || document.getElementById('query').value.trim();  // Usa el texto prefijado o el input
        if (userId === '' || query === '') return;

        const sendButton = document.getElementById('sendButton');
        sendButton.disabled = true;

        const messages = document.getElementById('messages');

        // Muestra el mensaje del usuario en el área de chat
        messages.innerHTML += `<div class="message sent"><p>${query}</p><span class="time">${new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}</span></div>`;
        document.getElementById('query').value = '';  // Limpiar el input

        try {
            const response = await fetch('/module_manager/web-service/', {  // Apunta al endpoint correcto
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({ user_id: userId, query })
            });

            const contentType = response.headers.get('content-type');
            if (contentType && contentType.includes('application/json')) {
                const data = await response.json();
                const loadingElement = messages.querySelector('.loading');
                if (loadingElement) {
                    loadingElement.remove();
                }

                if (response.ok) {
                    let formattedResponse = data.response
                        .replace(/\n/g, '<br>')
                        .replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>');

                    messages.innerHTML += `<div class="message ai">${formattedResponse}</div>`;
                } else {
                    messages.innerHTML += `<div class="message ai">Error: ${data.error}</div>`;
                }
            } else {
                const loadingElement = messages.querySelector('.loading');
                if (loadingElement) {
                    loadingElement.remove();
                }
                messages.innerHTML += `<div class="message ai">Error: La respuesta no es válida o es HTML en lugar de JSON.</div>`;
            }
        } catch (error) {
            console.error("Error: ", error);
            const loadingElement = messages.querySelector('.loading');
            if (loadingElement) {
                loadingElement.remove();
            }
            messages.innerHTML += `<div class="message ai">Error al procesar la consulta.</div>`;
        } finally {
            sendButton.disabled = false;
        }
    }

    // Manejo del evento "Enter" para enviar mensajes
    function handleKeyPress(event) {
        if (event.key === 'Enter') {
            sendQuery();
        }
    }

    // Asignar eventos de Enter y click para el input de consulta
    document.getElementById('query').addEventListener('keypress', handleKeyPress);
    document.getElementById('sendButton').addEventListener('click', sendQuery);
});
