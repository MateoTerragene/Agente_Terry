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

    // Seleccionamos el ícono de nuevo thread por su id
    const newThreadIcon = document.getElementById('new-thread-icon');
    if (newThreadIcon) {
        newThreadIcon.addEventListener('click', createNewThread);  // Llamar a la función cuando se haga clic
    }

    // Variables para la grabación de audio
    let mediaRecorder;
    let audioChunks = [];
    let startTime;
    let timerInterval;

    // Mostrar duración mientras se graba
    function startTimer() {
        startTime = Date.now();
        timerInterval = setInterval(() => {
            const elapsedTime = Math.floor((Date.now() - startTime) / 1000);
            const minutes = Math.floor(elapsedTime / 60);
            const seconds = elapsedTime % 60;
            micButton.textContent = `Grabando: ${minutes}:${seconds < 10 ? '0' + seconds : seconds}`;
        }, 1000);
    }

    // Detener el temporizador
    function stopTimer() {
        clearInterval(timerInterval);
        micButton.textContent = "Grabar Audio";
    }

    // Función para crear un nuevo thread
    async function createNewThread() {
        // Limpiar todos los mensajes del chat
        const messagesContainer = document.getElementById('messages');
        if (messagesContainer) {
            messagesContainer.innerHTML = '';  // Limpia el contenido del contenedor de mensajes
        }
        const response = await fetch('/module_manager/web-service/?action=create_thread', {
            method: 'GET',
        });

        const data = await response.json();
        if (data.status === 'success') {
            console.log('Thread creado con éxito:', data.message);
        } else {
            console.error('Error al crear thread:', data.message);
        }
    }

    // Iniciar la grabación de audio
    const micButton = document.getElementById('micButton');
    if (micButton) {
        micButton.addEventListener('click', async function () {
            if (mediaRecorder && mediaRecorder.state === "recording") {
                // Detener la grabación
                mediaRecorder.stop();
                stopTimer();
            } else {
                // Solicitar acceso al micrófono
                const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
                mediaRecorder = new MediaRecorder(stream);
                audioChunks = [];

                mediaRecorder.ondataavailable = (event) => {
                    audioChunks.push(event.data);
                };

                mediaRecorder.onstop = async () => {
                    // Crear un Blob del audio grabado
                    const audioBlob = new Blob(audioChunks, { type: 'audio/mp3' });
                    const audioURL = URL.createObjectURL(audioBlob);

                    // Insertar el reproductor de audio en el chat
                    const messageContainer = document.createElement("div");
                    messageContainer.classList.add("message", "sent");

                    const audioElement = document.createElement("audio");
                    audioElement.controls = true;
                    audioElement.src = audioURL;

                    const timeStamp = document.createElement("span");
                    timeStamp.classList.add("time");
                    timeStamp.textContent = new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });

                    messageContainer.appendChild(audioElement);
                    messageContainer.appendChild(timeStamp);
                    messages.appendChild(messageContainer);

                    // Enviar el archivo al servidor
                    const formData = new FormData();
                    formData.append('file', audioBlob, 'audio.mp3');
                    formData.append('user_id', userId);

                    try {
                        const response = await fetch('/module_manager/web-service/', {
                            method: 'POST',
                            body: formData
                        });

                        const data = await response.json();
                        if (response.ok) {
                            console.log('Audio enviado con éxito:', data);
                        } else {
                            console.error('Error al enviar el archivo:', data.error);
                        }
                    } catch (error) {
                        console.error('Error al procesar el archivo:', error);
                    }
                };

                // Iniciar la grabación y el temporizador
                mediaRecorder.start();
                startTimer();
            }
        });
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
    
                    // Agregar un reproductor de audio si hay un archivo de audio en la respuesta
                    if (data.audio_response) {
                        const audioPlayer = document.createElement('audio');
                        audioPlayer.controls = true;
                        audioPlayer.src = data.audio_response;
                        audioPlayer.classList.add('audio-player');
                    
                        const duration = data.duration ? `${Math.floor(data.duration / 60)}:${(data.duration % 60).toString().padStart(2, '0')}` : '';
                    
                        const durationText = document.createElement('span');
                        durationText.classList.add('time');
                        durationText.textContent = `Duración: ${duration}`;
                    
                        messageContainerReceived.appendChild(audioPlayer);
                        messageContainerReceived.appendChild(durationText);
                    }
                    
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

    // Funcionalidad para adjuntar archivos
    const attachButton = document.getElementById('attachButton');
    const fileInput = document.getElementById('fileInput');
    if (attachButton && fileInput) {
        attachButton.addEventListener('click', function () {
            fileInput.click();  // Simula el clic en el input de archivo
        });

        fileInput.addEventListener('change', async function () {
            const file = fileInput.files[0];
            if (!file || !userId) return;

            const formData = new FormData();
            formData.append('file', file);
            formData.append('user_id', userId);

            try {
                const response = await fetch('/module_manager/web-service/', {
                    method: 'POST',
                    body: formData
                });

                const data = await response.json();
                if (response.ok) {
                    const messageContainer = document.createElement("div");
                    messageContainer.classList.add("message", "sent");

                    const messageText = document.createElement("p");
                    messageText.textContent = `Archivo adjuntado: ${file.name}`;

                    const timeStamp = document.createElement("span");
                    timeStamp.classList.add("time");
                    timeStamp.textContent = new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });

                    messageContainer.appendChild(messageText);
                    messageContainer.appendChild(timeStamp);

                    messages.appendChild(messageContainer);

                    // Scroll automático al final del chat
                    messages.scrollTop = messages.scrollHeight;
                } else {
                    console.error('Error al enviar el archivo:', data.error);
                }
            } catch (error) {
                console.error('Error al procesar el archivo:', error);
            }
        });
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
