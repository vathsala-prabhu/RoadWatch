document.addEventListener("DOMContentLoaded", () => {
  const toggle = document.querySelector(".menu-toggle");
  const links = document.querySelector(".nav-links");
  if (toggle && links) {
    toggle.addEventListener("click", () => {
      const open = links.classList.toggle("nav-open");
      toggle.setAttribute("aria-expanded", String(open));
    });
  }

  const fileInput = document.querySelector("#image");
  const fileLabel = document.querySelector("#file-label");
  if (fileInput && fileLabel) {
    fileInput.addEventListener("change", () => {
      fileLabel.textContent = fileInput.files.length
        ? fileInput.files[0].name
        : "Choose an image to upload";
    });
  }

  document.querySelectorAll(".flash").forEach((flash) => {
    window.setTimeout(() => {
      flash.classList.add("flash-hide");
      window.setTimeout(() => flash.remove(), 350);
    }, 4500);
  });
});
