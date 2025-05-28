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
        if (data.status === 'success') {
            console.log('Thread creado con éxito:', data.message);
        } else {
            console.error('Error al crear thread:', data.message);
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
                messages.innerHTML += `<div class="message received">Error: La respuesta no es válida o es HTML en lugar de JSeON.${contentType}</div>`;
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

    const terries = document.querySelector(".terries");

  let isDragging = false;
  let startX;
  let scrollLeft;

  terries.addEventListener("mousedown", (e) => {
    isDragging = true;
    terries.classList.add("active");
    startX = e.pageX - terries.offsetLeft;
    scrollLeft = terries.scrollLeft;
  });

  terries.addEventListener("mouseleave", () => {
    isDragging = false;
    terries.classList.remove("active");
  });

  terries.addEventListener("mouseup", () => {
    isDragging = false;
    terries.classList.remove("active");
  });

  terries.addEventListener("mousemove", (e) => {
    if (!isDragging) return;
    e.preventDefault();
    const x = e.pageX - terries.offsetLeft;
    const walk = (x - startX) * 2; // Ajusta la velocidad del desplazamiento
    terries.scrollLeft = scrollLeft - walk;
  });

  const terriesItems = document.querySelectorAll(".terries ul li"); // Cambié el nombre aquí
  const icon = document.querySelector(".grupo-409-icon");

  terriesItems.forEach((terry) => {
    terry.addEventListener("click", () => {
      const selectedClass = Array.from(terry.classList).find((cls) => cls.startsWith("terry_"));

      if (selectedClass) {
        icon.className = "grupo-409-icon";
        icon.classList.add(selectedClass);
      }
    });
  });


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
