// Small helpers used on every page: the phone menu.
(function () {
  "use strict";
  var btn = document.querySelector("[data-menu]");
  var nav = document.getElementById("top-nav");
  if (!btn || !nav) return;
  function setOpen(open) {
    nav.classList.toggle("is-open", open);
    btn.setAttribute("aria-expanded", open ? "true" : "false");
  }
  btn.addEventListener("click", function (e) {
    e.stopPropagation();
    setOpen(!nav.classList.contains("is-open"));
  });
  document.addEventListener("click", function (e) {
    if (nav.classList.contains("is-open") && !nav.contains(e.target)) setOpen(false);
  });
  document.addEventListener("keydown", function (e) { if (e.key === "Escape") setOpen(false); });
  nav.addEventListener("click", function (e) { if (e.target.closest("a")) setOpen(false); });
})();
