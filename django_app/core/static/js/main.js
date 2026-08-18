document.addEventListener("DOMContentLoaded", () => {

    let productos = {}
    let centros = {}

    function getCookie(name) {
        let cookieValue = null;
        if (document.cookie && document.cookie !== '') {
            const cookies = document.cookie.split(';');
            for (let c of cookies) {
                c = c.trim();
                if (c.startsWith(name + '=')) {
                    cookieValue = decodeURIComponent(c.substring(name.length + 1));
                    break;
                }
            }
        }
        return cookieValue
    }

    function obtenerFiltros() {
        const filtros = {};

        document.querySelectorAll('.dropdown').forEach(dropdown => {
            const name = dropdown.dataset.name;

            const selectedOptions = [];

            dropdown.querySelectorAll(".options li.selected").forEach(option => {
                selectedOptions.push(option.dataset.value)
            });

            if (selectedOptions.includes("Todos") || selectedOptions.includes("Todas")) {
                filtros[name] = [];
            } else {
                filtros[name] = selectedOptions;
            }

        });

        return filtros;
    }

    function obtenerParametros() {
        const parametros = {};

        document.querySelectorAll('.param').forEach(param => {
            const name = param.dataset.name;

            const input = param.querySelector('input');

            parametros[name] = input.value;
        })

        return parametros
    }

    document.querySelectorAll('.dropdown').forEach(dropdown => {

        const select = dropdown.querySelector('.select');
        const caret = dropdown.querySelector('.caret');
        const menu = dropdown.querySelector('.menu');
        const search = dropdown.querySelector('.search');
        const options = dropdown.querySelectorAll('.options li');
        const selectedText = dropdown.querySelector('.selected-text');
        const defaultText = selectedText.innerText
        const clearBtn = dropdown.querySelector('.clear');

        // abrir / cerrar
        select.addEventListener('click', () => {
            select.classList.toggle('select-clicked');
            caret.classList.toggle('caret-rotate');
            menu.classList.toggle('menu-open');
        });

        // buscador
        search.addEventListener('keyup', () => {
            const value = search.value.toLowerCase();

            options.forEach(opt => {
                const text = opt.innerText.toLowerCase();
                opt.style.display = text.includes(value) ? 'block' : 'none';
            });
        });

        // 🔥 selección tipo toggle
        options.forEach(opt => {
            opt.addEventListener('click', () => {

                const isTodas = ["Todas", "Todos"].includes(opt.dataset.value);

                if (isTodas) {
                    options.forEach(o => o.classList.remove('selected'));
                    opt.classList.add('selected');
                } else {
                    opt.classList.toggle('selected');
                    
                    options.forEach(o => {
                        if (["Todas", "Todos"].includes(o.dataset.value)) {
                            o.classList.remove('selected');
                        }
                    });

                }

                const seleccionados = [];

                options.forEach(o => {
                    if (o.classList.contains('selected')) {
                        seleccionados.push(o.dataset.value);
                    }
                });

                selectedText.innerText = seleccionados.length > 0
                    ? seleccionados.join(', ')
                    : defaultText;
            });
        });

        // limpiar
        clearBtn.addEventListener('click', () => {
            options.forEach(o => o.classList.remove('selected'));
            selectedText.innerText = defaultText;
        });

    });

    // SI EL CLICK DEL USUARIO ESTA FUERA DE UN DROPDOWN CIERRA EL QUE ESTE ABIERTO 
    // Y SE REALIZA LA QUERY SOBRE PRODUCTOS Y CENTROS
    document.addEventListener("click", (e) => {

        let clickedInside = false;

        document.querySelectorAll(".dropdown").forEach(dropdown => {
            if (dropdown.contains(e.target)) {
                clickedInside = true;
            }
        });

        if (!clickedInside) {
            document.querySelectorAll(".dropdown").forEach(dropdown => {    
                dropdown.querySelector(".menu").classList.remove("menu-open");
                dropdown.querySelector(".caret").classList.remove("caret-rotate");
                dropdown.querySelector(".select").classList.remove("select-clicked");
            });
            
            const filtros = obtenerFiltros();

            fetch('/api/filtros/', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRFToken': getCookie('csrftoken')
                },
                body: JSON.stringify(filtros)
            })
            .then(res => res.json())
            .then(data => {
                productos = data.productos_filtrados;
                centros = data.centros_filtrados;
                document.getElementById("productos-count").innerText = data.productos;
                document.getElementById("centros-count").innerText = data.centros;
            });
        }
    });

    // LANZAR RESTOCK CUANDO SE HAGA CLIC EN EL BOTON DE 'LANZAR'
    document.getElementById("launch").addEventListener("click", function() {

        // Mostrar loader
        document.getElementById("loading_dots").style.display = "block";
        document.getElementById("msg").style.display = "block";

        // Desactivar botón
        this.disabled = true;

        const parametros = obtenerParametros()
        
        const body_movimientos = {
            'productos': productos,
            'centros': centros,
            'parametros': parametros
        };

        fetch('/api/movimientos/', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRFToken': getCookie('csrftoken')
                },
                body: JSON.stringify(body_movimientos)
            })
            .then(res => res.json())
            .then(data => {
                
            });

        setTimeout(() => {

            // Ocultar loader
            document.getElementById("loading_dots").style.display = "none";
            document.getElementById("msg").style.display = "none";

            // Restaurar botón
            this.disabled = false;

            
            // Mostrar la seccion de movimientos
            document.getElementById("seccion_movimientos").style.display = "block";


        }, 3000);

    });

});