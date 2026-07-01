// лайтбокс для превью модального окна, чтобы под размер моб телефона

document.addEventListener("DOMContentLoaded", function () {
    // создаём overlay один раз
    const overlay = document.createElement("div");
    overlay.id = "image-lightbox";
    overlay.style.display = "none";
    overlay.innerHTML = `
        <div class="lightbox-backdrop"></div>
        <img class="lightbox-image" src="" />
    `;
    document.body.appendChild(overlay);

    const imgEl = overlay.querySelector(".lightbox-image");

    // открыть
    document.querySelectorAll(".lightbox-trigger").forEach(el => {
        el.addEventListener("click", function (e) {
            e.preventDefault();
            imgEl.src = el.getAttribute("data-src");
            overlay.style.display = "flex";
        });
    });

    // закрыть по клику
    overlay.addEventListener("click", function () {
        overlay.style.display = "none";
        imgEl.src = "";
    });
});
