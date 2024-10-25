document.addEventListener('DOMContentLoaded', function () {
    const userId = document.getElementById('user_id') ? document.getElementById('user_id').value : null;

    // Funcionalidad para el botón de logout
    const logoutButton = document.querySelector('.logout');
    if (logoutButton) {
        logoutButton.addEventListener('click', function () {
            window.location.href = '/logout/'; // Redirige al logout
        });
    }

    // Al hacer clic en la mano, ocultar el mensaje de bienvenida y mostrar el login
    const handIcon = document.getElementById('hand-icon');
    if (handIcon) {
        handIcon.addEventListener('click', function () {
            document.getElementById('welcome-message').style.display = 'none';  // Ocultar el mensaje de bienvenida
            document.getElementById('login-container').style.display = 'flex';  // Mostrar el login
        });
    }
   // Función para crear un nuevo thread
   async function createNewThread() {
        if (!userId) return;

        try {
            const response = await fetch('/create-thread/', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRFToken': '{{ csrf_token }}',  // Incluye el token CSRF si es necesario
                },
                body: JSON.stringify({ 
                    action: 'create_thread'  // Enviar el parámetro especial para crear el thread
                })
            });

            const data = await response.json();
            if (response.ok) {
                alert(data.message);
            } else {
                alert(`Error: ${data.message}`);
            }
        } catch (error) {
            console.error('Error al crear nuevo thread:', error);
            alert('Error de conexión.');
        }
    }
   


    // Función para enviar consulta con texto personalizado o el input del usuario
    async function sendQuery(prefixedQuery = '') {
        const query = prefixedQuery || document.getElementById('query').value.trim();
        if (!userId || query === '') return;

        const sendButton = document.getElementById('sendButton');
        sendButton.style.pointerEvents = 'none';  // Desactiva el botón de enviar temporalmente

        const messages = document.getElementById('messages');

        // Validación para evitar enviar mensajes vacíos o solo con espacios en blanco
        if (query) {
            const messageContainer = document.createElement("div");
            messageContainer.classList.add("message", "sent");

            const messageText = document.createElement("p");
            messageText.textContent = query;

            const timeStamp = document.createElement("span");
            timeStamp.classList.add("time");
            timeStamp.textContent = new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });

            messageContainer.appendChild(messageText);
            messageContainer.appendChild(timeStamp);

            messages.appendChild(messageContainer);

            document.getElementById("query").value = ''; // Limpiar el input

            // Scroll automático al final del chat
            messages.scrollTop = messages.scrollHeight;
        } else {
            sendButton.style.pointerEvents = 'auto';  // Reactivar el botón si no hay texto
            return;
        }

        try {
            const response = await fetch('/module_manager/web-service/', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({ user_id: userId, query })
            });

            const contentType = response.headers.get('content-type');
            if (contentType && contentType.includes('application/json')) {
                const data = await response.json();

                if (response.ok) {
                    let formattedResponse = data.response
                        .replace(/\n/g, '<br>')
                        .replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>');

                    const messageContainerReceived = document.createElement("div");
                    messageContainerReceived.classList.add("message", "received");

                    const messageTextReceived = document.createElement("p");
                    messageTextReceived.innerHTML = formattedResponse;

                    const timeStampReceived = document.createElement("span");
                    timeStampReceived.classList.add("time");
                    timeStampReceived.textContent = new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });

                    messageContainerReceived.appendChild(messageTextReceived);
                    messageContainerReceived.appendChild(timeStampReceived);

                    messages.appendChild(messageContainerReceived);

                    // Scroll automático al final del chat
                    messages.scrollTop = messages.scrollHeight;
                } else {
                    messages.innerHTML += `<div class="message received">Error: ${data.error}</div>`;
                }
            } else {
                messages.innerHTML += `<div class="message received">Error: La respuesta no es válida o es HTML en lugar de JSON.</div>`;
            }
        } catch (error) {
            console.error("Error: ", error);
            messages.innerHTML += `<div class="message received">Error al procesar la consulta.</div>`;
        } finally {
            sendButton.style.pointerEvents = 'auto';  // Reactiva el botón de envío
        }
    }

    // Manejo del evento "Enter" para enviar mensajes
    function handleKeyPress(event) {
        if (event.key === 'Enter') {
            sendQuery();
        }
    }

    // Asignar eventos de Enter y click para el input de consulta
    const queryInput = document.getElementById('query');
    if (queryInput) {
        queryInput.addEventListener('keypress', handleKeyPress);
    }

    const sendButton = document.getElementById('sendButton');
    if (sendButton) {
        sendButton.addEventListener('click', () => sendQuery());

    }

    // Funcionalidad para expandir el chat al hacer clic en expand-icon
    const expandIcon = document.querySelector('.expand-icon');
    if (expandIcon) {
        expandIcon.addEventListener('click', function () {
            const chatContainer = document.querySelector('.chat-container');
            chatContainer.classList.toggle('expanded');
            
            // Ajustar la altura y el scroll de los mensajes cuando se expande
            const messages = document.getElementById('messages');
            setTimeout(() => {
                messages.scrollTop = messages.scrollHeight;  // Mantiene el scroll al final cuando se expande
            }, 300);
        });
    }
});
