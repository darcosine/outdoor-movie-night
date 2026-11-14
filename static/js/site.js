if (window.htmx) {
  window.htmx.config.allowEval = false;
  window.htmx.config.allowScriptTags = false;
}

document.addEventListener("click", (event) => {
  const openButton = event.target.closest(".js-open-paid-dialog");
  if (openButton) {
    openButton.nextElementSibling?.showModal();
    return;
  }

  const closeButton = event.target.closest(".js-close-paid-dialog");
  if (closeButton) {
    closeButton.closest("dialog")?.close();
    return;
  }

  if (event.target.closest(".js-print-page")) {
    window.print();
  }
});
