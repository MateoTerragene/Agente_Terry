document.addEventListener('DOMContentLoaded', function () {
    const userId = document.getElementById('user_id').value;
    
    // Obtener los íconos
    const coaIcon = document.getElementById('coa-icon');
    const ifuIcon = document.getElementById('ifu-icon');
    const productIcon = document.getElementById('product-icon');

    // Modificar sendQuery para aceptar un texto personalizado
    async function sendQuery(prefixedQuery = '') {
        const userId = document.getElementById('user_id').value.trim();
        const queryInput = document.getElementById('query').value.trim();
        const query = prefixedQuery || queryInput;  // Usar el texto prefijado si está disponible, de lo contrario usar el input
        if (userId === '' || query === '') return;
    
        const sendButton = document.getElementById('sendButton');
        sendButton.disabled = true;
    
        const messages = document.getElementById('messages');
        messages.innerHTML += `<div class="message user">${query}</div>`;
        messages.innerHTML += `<div class="message ai loading">Procesando...</div>`;
        document.getElementById('query').value = '';  // Limpiar el input solo cuando el usuario escribe manualmente
    
        try {
            const response = await fetch('/module_manager/web-service/', {  // Apunta al endpoint correcto
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({ user_id: userId, query })
            });
    
            // Verifica si la respuesta es JSON válida
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
    
                    if (window.MathJax) {
                        MathJax.typesetPromise().then(() => {
                            console.log('MathJax typesetting complete');
                        }).catch((err) => console.error('MathJax typesetting failed: ', err));
                    }
                } else {
                    messages.innerHTML += `<div class="message ai">Error: ${data.error}</div>`;
                }
            } else {
                // Si la respuesta no es JSON, es probable que sea HTML (como una página de error o redirección)
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
    
    function handleKeyPress(event) {
        if (event.key === 'Enter') {
            sendQuery();
        }
    }

    // Asignar eventos a los íconos con consultas prefijadas
    coaIcon.addEventListener('click', function() {
        sendQuery("Find COAs");
    });

    ifuIcon.addEventListener('click', function() {
        sendQuery("Find IFUs");
    });

    productIcon.addEventListener('click', function() {
        sendQuery("Hello, I information about a product");
    });

    // Escuchar el evento de tecla Enter y el botón Enviar para el input de consulta
    document.getElementById('query').addEventListener('keypress', handleKeyPress);
    document.getElementById('sendButton').addEventListener('click', sendQuery);
});

$(document).ready(function() {
    // Función para expandir la ventana cuando se hace clic en el ícono de expandir
    $(".expand-icon").click(function() {
        $(".grupo-707").toggleClass("expanded");
    });

    // Función para mostrar el login cuando se haga clic en la mano
    $("#hand-icon").click(function() {
        $("#login-container").toggleClass("hidden");  // Mostrar/ocultar el formulario de login
    });
});
