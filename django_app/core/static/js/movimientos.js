document.addEventListener("DOMContentLoaded", () => {

    const rootStyles = getComputedStyle(document.documentElement);

    // CAMBIAR LA VISUALIZACION ENTRE 'A ENVIAR' Y 'A RECIBIR'
    const boxes = document.querySelectorAll(".box");

    boxes.forEach(box => {
        box.addEventListener("click", function() {

            // quitar active de todos
            boxes.forEach(b => b.classList.remove("active"));

            // añadir active al clicado
            this.classList.add("active");

        });
    });

    // CAMBIAR LA SELECCION DEL RECEPTOR
    const receptores = document.querySelectorAll(".receptores li");
    receptores.forEach(receptor => {

        receptor.addEventListener("click", function(){

            receptores.forEach(r => r.classList.remove("active"));

            this.classList.add("active");

        });
    });

    // COPIAR CODIGO DE PRODUCTO O CODIGO DE COLOR DE LAS TARJETAS
    document.querySelectorAll(".ref").forEach( btn => {

        btn.addEventListener("click", function() {
            const texto = this.dataset.text;
            navigator.clipboard.writeText(texto)
            
            this.textContent = "Copiado"
            this.style.cursor = "default"
            this.style.opacity = 1
            this.style.color = rootStyles.getPropertyValue('--color-copiado').trim();

            setTimeout(() => {
                this.textContent = texto
                this.style.cursor = "pointer"
                this.style.opacity = 0.8
                this.style.color = rootStyles.getPropertyValue('--blanco').trim();
            }, 1500);

        });

    });

    // MODAL: HACER LA IMAGEN GRANDE AL HACER CLIC
    const modal = document.getElementById("modal");
    const modalImg = document.getElementById("modal_img");

    // todas las imágenes clicables
    document.querySelectorAll(".product_img").forEach(img => {

        img.addEventListener("click", function() {

            modal.style.display = "flex";
            modalImg.src = this.src;

            modal.addEventListener("click", function(e) {
                if (e.target === modal) {
                    modal.style.display = "none";
                }
            });

        });

    });

    // cerrar
    document.getElementById("close").addEventListener("click", function() {
        modal.style.display = "none";
    });

});