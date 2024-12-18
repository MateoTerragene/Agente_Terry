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
    //const handIcon = document.getElementById('hand-icon');
   // if (handIcon) {
    //    handIcon.addEventListener('click', function () {
    //        document.getElementById('welcome-message').style.display = 'none';  // Ocultar el mensaje de bienvenida
    //        document.getElementById('login-container').style.display = 'flex';  // Mostrar el login
    //    });
   // }

  // Seleccionamos el ícono de nuevo thread por su id
  const newThreadIcon = document.getElementById('new-thread-icon');
  if (newThreadIcon) {
      newThreadIcon.addEventListener('click', createNewThread);  // Llamar a la función cuando se haga clic
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
        console.log(data); // Agrega esta línea temporalmente
        if (data.status === 'success') {
            console.log('Thread creado con éxito:', data.message);
        } else {
            console.error('Error al crear thread:', data.message);
        }
    }

    // Control de envío de texto y manejo de los íconos
    const queryInput = document.getElementById('query');
    const attachButton = document.getElementById('attachButton');
    const micButton = document.getElementById('micButton');  // El botón de grabar
    const sendButton = document.getElementById('sendButton');
    const fileInput = document.getElementById('fileInput');
    const messages = document.getElementById('messages');

    // Ocultar los botones de mic y attach cuando se empieza a escribir
    if (queryInput) {
        queryInput.addEventListener('input', function () {
            if (queryInput.value.trim() !== "") {
                attachButton.style.display = 'none';
                micButton.style.display = 'none';
                sendButton.style.display = 'inline-block';  // Mostrar el botón de enviar
            } else {
                attachButton.style.display = 'inline-block';
                micButton.style.display = 'inline-block';
                sendButton.style.display = 'none';  // Ocultar el botón de enviar
            }
        });
    }

    if (sendButton) {
        sendButton.addEventListener('click', () => sendQuery());
    }

    async function sendQuery(prefixedQuery = '') {
        const query = prefixedQuery || queryInput.value.trim();
        if (!userId || query === '') return;

        sendButton.style.pointerEvents = 'none';  // Desactiva el botón de enviar temporalmente

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
            queryInput.value = '';  // Limpiar el input
            messages.scrollTop = messages.scrollHeight;  // Scroll automático
        }

        try {
            const response = await fetch('/module_manager/web-service/', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({ user_id: userId, query })
            });

            const data = await response.json();
            if (response.ok) {
                const messageContainerReceived = document.createElement("div");
                messageContainerReceived.classList.add("message", "received");

                const messageTextReceived = document.createElement("p");
                // messageTextReceived.innerHTML = data.response.replace(/\n/g, '<br>');
                messageTextReceived.innerHTML = decodeMessage(data.response);  
                
                const timeStampReceived = document.createElement("span");
                timeStampReceived.classList.add("time");
                timeStampReceived.textContent = new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });

                messageContainerReceived.appendChild(messageTextReceived);
                messageContainerReceived.appendChild(timeStampReceived);

                // Agregar un reproductor de audio si hay un archivo de audio en la respuesta
                if (data.audio_response) {
                    const audioPlayer = document.createElement('audio');
                    audioPlayer.controls = true;
                    audioPlayer.src = data.audio_response;  // Asegurarse de que la URL está bien configurada
                    messageContainerReceived.appendChild(audioPlayer);
                }

                messages.appendChild(messageContainerReceived);
                messages.scrollTop = messages.scrollHeight;  // Scroll automático al final del chat
            }
        } catch (error) {
            console.error("Error:", error);
        } finally {
            sendButton.style.pointerEvents = 'auto';  // Reactivar el botón de enviar
             // Restaurar los botones de adjuntar y grabar
            attachButton.style.display = 'inline-block';
            micButton.style.display = 'inline-block';
            sendButton.style.display = 'none';  // Ocultar el botón de enviar nuevamente
        }
    }

    // Manejo del evento "Enter" para enviar el mensaje
    if (queryInput) {
        queryInput.addEventListener('keypress', function (event) {
            if (event.key === 'Enter') {
                sendQuery();
                // Restaurar los botones de adjuntar y grabar
                attachButton.style.display = 'inline-block';
                micButton.style.display = 'inline-block';
                sendButton.style.display = 'none';  // Ocultar el botón de enviar nuevamente
            }
        });
    }

    // Enviar archivo adjunto
    if (attachButton && fileInput) {
        attachButton.addEventListener('click', function () {
            fileInput.click();
        });

        fileInput.addEventListener('change', async function () {
            const file = fileInput.files[0];
            if (!file || !userId) return;
        
            const formData = new FormData();
            formData.append('file', file);
            formData.append('user_id', userId);
        
            const messageContainer = document.createElement("div");
            messageContainer.classList.add("message", "sent");
        
            if (file.type.startsWith('image/')) {
                // Si el archivo es una imagen, mostrar una previsualización
                const imagePreview = document.createElement("img");
                imagePreview.src = URL.createObjectURL(file);
                imagePreview.style.maxWidth = "100%";
                imagePreview.style.borderRadius = "8px";
                messageContainer.appendChild(imagePreview);
            } else {
                // Si no es una imagen, mostrar el nombre del archivo
                const messageText = document.createElement("p");
                messageText.textContent = `Archivo adjuntado: ${file.name}`;
                messageContainer.appendChild(messageText);
            }
        
            // Añadir la hora de envío
            const timeStamp = document.createElement("span");
            timeStamp.classList.add("time");
            timeStamp.textContent = new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
            messageContainer.appendChild(timeStamp);
        
            messages.appendChild(messageContainer);
            messages.scrollTop = messages.scrollHeight;
        
            // Enviar la imagen al servidor
            try {
                const response = await fetch('/module_manager/web-service/', {
                    method: 'POST',
                    body: formData
                });
        
                const data = await response.json();
                if (response.ok) {
                    const messageContainerReceived = document.createElement("div");
                    messageContainerReceived.classList.add("message", "received");
        
                    const messageTextReceived = document.createElement("p");
                    messageTextReceived.textContent = data.response;
        
                    const timeStampReceived = document.createElement("span");
                    timeStampReceived.classList.add("time");
                    timeStampReceived.textContent = new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
        
                    messageContainerReceived.appendChild(messageTextReceived);
                    messageContainerReceived.appendChild(timeStampReceived);
        
                    messages.appendChild(messageContainerReceived);
                    messages.scrollTop = messages.scrollHeight;
                } else {
                    console.error('Error al enviar el archivo:', data.error);
                }
            } catch (error) {
                console.error('Error al procesar el archivo:', error);
            }
        });
    }

    // Grabar audio
    let mediaRecorder;
    const chunks = [];
    let recordingStartTime;
    let recordingTimer;
    let isRecording = false; // Variable para controlar el estado de grabación

    if (micButton) {
        micButton.addEventListener('click', async function () {
            if (!isRecording) {
                // Iniciar la grabación
                micButton.src = '/static/img/stop.png';  // Cambiar el icono al de stop
                chunks.length = 0;    
                try {
                    const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
                    mediaRecorder = new MediaRecorder(stream);

                    mediaRecorder.ondataavailable = function (e) {
                        chunks.push(e.data);
                    };

                    mediaRecorder.onstop = async function () {
                        const audioBlob = new Blob(chunks, { type: 'audio/mp3' });
                        const formData = new FormData();
                        formData.append('file', audioBlob, 'audio.mp3');
                        formData.append('user_id', userId);
                    
                        // Mostrar el reproductor de audio para el audio enviado
                        const audioURL = URL.createObjectURL(audioBlob);
                        const audioElement = document.createElement('audio');
                        audioElement.controls = true;
                        audioElement.src = audioURL;
                    
                        const messageContainer = document.createElement("div");
                        messageContainer.classList.add("message", "sent");
                    
                        const timeStamp = document.createElement("span");
                        timeStamp.classList.add("time");
                        timeStamp.textContent = new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
                    
                        messageContainer.appendChild(audioElement);
                        messageContainer.appendChild(timeStamp);
                        messages.appendChild(messageContainer);
                        messages.scrollTop = messages.scrollHeight;
                    
                        try {
                            const response = await fetch('/module_manager/web-service/', {
                                method: 'POST',
                                body: formData
                            });
                    
                            const data = await response.json();
                            if (response.ok) {
                                // Manejar el texto de respuesta si existe
                                if (data.response) {
                                    const messageContainerReceivedText = document.createElement("div");
                                    messageContainerReceivedText.classList.add("message", "received");
                    
                                    const messageTextReceived = document.createElement("p");
                                    messageTextReceived.innerHTML = data.response.replace(/\n/g, '<br>');  // Mostrar HTML correctamente
                    
                                    const timeStampReceivedText = document.createElement("span");
                                    timeStampReceivedText.classList.add("time");
                                    timeStampReceivedText.textContent = new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
                    
                                    messageContainerReceivedText.appendChild(messageTextReceived);
                                    messageContainerReceivedText.appendChild(timeStampReceivedText);
                    
                                    messages.appendChild(messageContainerReceivedText);
                                }
                    
                                // Manejar el audio de respuesta si existe
                                if (data.audio_response) {
                                    const messageContainerReceivedAudio = document.createElement("div");
                                    messageContainerReceivedAudio.classList.add("message", "received");
                    
                                    const audioPlayerReceived = document.createElement('audio');
                                    audioPlayerReceived.controls = true;
                                    audioPlayerReceived.src = data.audio_response;  // Reproductor de audio recibido
                    
                                    const timeStampReceivedAudio = document.createElement("span");
                                    timeStampReceivedAudio.classList.add("time");
                                    timeStampReceivedAudio.textContent = new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
                    
                                    messageContainerReceivedAudio.appendChild(audioPlayerReceived);
                                    messageContainerReceivedAudio.appendChild(timeStampReceivedAudio);
                    
                                    messages.appendChild(messageContainerReceivedAudio);
                                }
                    
                                // Scroll automático al final del chat
                                messages.scrollTop = messages.scrollHeight;
                            }
                        } catch (error) {
                            console.error('Error al enviar el archivo de audio:', error);
                        }
                    };

                    mediaRecorder.start();
                    recordingStartTime = Date.now();

                    // Mostrar contador
                    recordingTimer = setInterval(function () {
                        const elapsed = Math.floor((Date.now() - recordingStartTime) / 1000);
                        micButton.textContent = `${elapsed}s`;  // Mostrar el tiempo transcurrido
                    }, 1000);

                    isRecording = true; // Cambia el estado a grabando
                } catch (error) {
                    console.error('Error al acceder al micrófono:', error);
                }
            } else {
                // Detener la grabación
                if (mediaRecorder && mediaRecorder.state !== 'inactive') {
                    mediaRecorder.stop();
                    clearInterval(recordingTimer);
                    micButton.src = '/static/img/mic.png';  // Restaurar el icono del micrófono
                    micButton.textContent = '';  // Limpiar el contador
                    isRecording = false; // Cambia el estado a no grabando
                }
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

$(document).ready(function() {
    $('.frase-circ').click(function() {
        $(this).fadeOut(500);
        $('.grupo-707').addClass('show-grupo');
    });
    $(".expand-icon").click(function() {
        $(".grupo-707").toggleClass("expanded");
        $('.grupo-707').toggleClass('show-grupo');
    });
});


$('.grupo-179-icon').click(function() {
    $('.grupo-707').removeClass('show-grupo');
    $(".grupo-707").removeClass("expanded");
    $('.frase-circ').fadeIn(500);
});


circulo = document.getElementById("circulo")
        circlearray = circulo.textContent.split('')
        circulo.textContent = ''
        for(var i = 0; i< circlearray.length; i++){
            circulo.innerHTML += '<span style="transform:rotate('+((i+1)*7)+'deg)">'+ circlearray[i]+'</span>'
        }
