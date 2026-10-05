// Job search: loads the job list once, then filters and sorts it in the browser.
// Written in plain ES5 so it runs on older phones as well as current Chrome, Safari and Firefox.
(function () {
  "use strict";
  var finder = document.querySelector("[data-finder]");
  if (!finder) return;
  var ROOT = finder.getAttribute("data-root"), SUFFIX = finder.getAttribute("data-suffix"), PAGE = 25;
  var form = document.querySelector("[data-search-form]");
  var qInput = form.querySelector("input[name=q]");
  var list = finder.querySelector("[data-results]");
  var countEl = finder.querySelector("[data-count]");
  var emptyEl = finder.querySelector("[data-empty]");
  var moreBtn = finder.querySelector("[data-more]");
  var sheet = finder.querySelector("[data-sheet]");
  var scrim = finder.querySelector("[data-scrim]");
  var openBtn = finder.querySelector("[data-sheet-open]");
  var activeBadge = finder.querySelector("[data-active-count]");
  var applyLabel = finder.querySelector("[data-apply-label]");
  var field = function (name) { return finder.querySelector("[name=" + name + "]"); };
  var jobs = [], matches = [], shown = 0, company = "";
  var DAY = 86400000;
  var now = new Date();
  var todayUTC = Date.UTC(now.getUTCFullYear(), now.getUTCMonth(), now.getUTCDate());
  var ICON_BUILDING = '<svg class="icon" viewBox="0 0 24 24" aria-hidden="true" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M4 21V5l8-2v18M12 8h8v13M8 8v.01M8 12v.01M8 16v.01M16 12v.01M16 16v.01M2 21h20"/></svg>';
  var ICON_PIN = '<svg class="icon" viewBox="0 0 24 24" aria-hidden="true" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M12 21s-7-6.2-7-11.5A7 7 0 0 1 19 9.5C19 14.8 12 21 12 21z"/><circle cx="12" cy="9.5" r="2.5"/></svg>';

  function parseDay(iso) { var p = iso.split("-"); return Date.UTC(+p[0], +p[1] - 1, +p[2]); } // Safari-safe
  function daysAgo(iso) { return Math.round((todayUTC - parseDay(iso)) / DAY); }
  function ago(iso) {
    var d = daysAgo(iso);
    if (d <= 0) return "Today";
    if (d === 1) return "Yesterday";
    if (d < 30) return d + " days ago";
    if (d < 60) return "1 month ago";
    return Math.floor(d / 30) + " months ago";
  }
  function esc(s) {
    return String(s).replace(/[&<>"']/g, function (c) {
      return { "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c];
    });
  }
  function cssEscape(s) { return window.CSS && CSS.escape ? CSS.escape(s) : s.replace(/["\\]/g, "\\$&"); }

  function readState() {
    var modes = [].map.call(finder.querySelectorAll("[name=mode]:checked"), function (b) { return b.value; });
    return {
      q: qInput.value.trim().toLowerCase(), country: field("country").value, role: field("role").value,
      modes: modes, posted: field("posted").value, type: field("type").value, sort: field("sort").value
    };
  }

  function applyUrl() {
    var p = new URLSearchParams(location.search);
    qInput.value = p.get("q") || "";
    ["country", "role", "posted", "type", "sort"].forEach(function (k) {
      var v = p.get(k);
      if (v && field(k).querySelector('option[value="' + cssEscape(v) + '"]')) field(k).value = v;
    });
    var modes = (p.get("mode") || "").split(",");
    [].forEach.call(finder.querySelectorAll("[name=mode]"), function (b) { b.checked = modes.indexOf(b.value) > -1; });
    company = p.get("company") || "";
  }

  function writeUrl(s) {
    var p = new URLSearchParams();
    if (s.q) p.set("q", qInput.value.trim());
    ["country", "role", "posted", "type"].forEach(function (k) { if (s[k]) p.set(k, s[k]); });
    if (s.modes.length) p.set("mode", s.modes.join(","));
    if (s.sort !== "new") p.set("sort", s.sort);
    if (company) p.set("company", company);
    var qs = p.toString();
    try { history.replaceState(null, "", location.pathname + (qs ? "?" + qs : "") + location.hash); } catch (e) { /* some embedded views block this */ }
  }

  function matchesState(j, s) {
    if (company && j.cs !== company) return false;
    if (s.q && (j.t + " " + j.c + " " + j.l + " " + j.cn).toLowerCase().indexOf(s.q) === -1) return false;
    if (s.country) {
      if (s.country.indexOf("region:") === 0) { if (j.rg !== s.country.slice(7)) return false; }
      else if (j.cc !== s.country) return false;
    }
    if (s.role && j.r !== s.role) return false;
    if (s.type && j.ct !== s.type) return false;
    if (s.modes.length && s.modes.indexOf(j.w) === -1) return false;
    if (s.posted) {
      var d = daysAgo(j.p);
      if (s.posted === "older" ? d <= 30 : d > Number(s.posted)) return false;
    }
    return true;
  }

  function tagsHtml(j) {
    var out = "";
    if (daysAgo(j.p) <= 2) out += '<span class="tag tag-new">New</span>';
    if (j.x) {
      var left = Math.round((parseDay(j.x) - todayUTC) / DAY);
      if (left >= 0 && left <= 7) out += '<span class="tag tag-closing">Closes soon</span>';
    }
    out += '<span class="tag tag-' + j.w.toLowerCase() + '">' + esc(j.w) + "</span>";
    return '<span class="tags">' + out + "</span>";
  }

  function card(j) {
    return '<li class="job-card">' +
      '<span class="avatar tone-' + j.o + '" aria-hidden="true">' + esc(j.a) + "</span>" +
      '<div class="job-main"><a class="job-title" href="' + esc(ROOT + j.u + "/" + SUFFIX) + '">' + esc(j.t) + "</a>" +
      '<div class="job-meta"><span>' + ICON_BUILDING + esc(j.c) + "</span><span>" + ICON_PIN + esc(j.l || j.cn || "See job page") + "</span></div></div>" +
      '<div class="job-side">' + tagsHtml(j) + '<span class="when">' + ago(j.p) + "</span></div></li>";
  }

  function render(reset) {
    if (reset) { shown = 0; list.innerHTML = ""; }
    var next = matches.slice(shown, shown + PAGE);
    list.insertAdjacentHTML("beforeend", next.map(card).join(""));
    shown += next.length;
    var total = matches.length;
    countEl.textContent = total === jobs.length
      ? total.toLocaleString() + " jobs"
      : total.toLocaleString() + " of " + jobs.length.toLocaleString() + " jobs";
    if (applyLabel) applyLabel.textContent = total ? "Show " + total.toLocaleString() + " jobs" : "No matching jobs";
    emptyEl.hidden = total > 0;
    moreBtn.hidden = shown >= total;
  }

  // ----- live counts next to every filter choice -----
  // Each count shows how many jobs that choice would give, taking every OTHER active
  // filter into account (e.g. with Remote ticked, "India (0)").
  var countLabelRe = /\s*\(\d[\d,]*\)$/;
  [].forEach.call(finder.querySelectorAll(".filters select option, [name=mode] + span"), function (el) {
    el.setAttribute("data-label", el.textContent.replace(countLabelRe, ""));
  });

  function without(s, dim) {
    var c = {}; for (var k in s) c[k] = s[k];
    if (dim === "modes") c.modes = []; else c[dim] = "";
    return c;
  }

  function tally(list, keyFn) {
    var out = {};
    list.forEach(function (j) { keyFn(j).forEach(function (k) { out[k] = (out[k] || 0) + 1; }); });
    return out;
  }

  function setOption(opt, n, selected) {
    var base = opt.getAttribute("data-label");
    if (!opt.value) { opt.textContent = base; return; }          // "All countries" etc.
    opt.textContent = base + " (" + n.toLocaleString() + ")";
    opt.disabled = n === 0 && !selected;
  }

  function updateCounts(s) {
    var pool;
    // country and region
    pool = jobs.filter(function (j) { return matchesState(j, without(s, "country")); });
    var byCountry = tally(pool, function (j) { return [j.cc, "region:" + j.rg]; });
    [].forEach.call(field("country").options, function (o) { setOption(o, byCountry[o.value] || 0, o.value === s.country); });
    // role
    pool = jobs.filter(function (j) { return matchesState(j, without(s, "role")); });
    var byRole = tally(pool, function (j) { return [j.r]; });
    [].forEach.call(field("role").options, function (o) { setOption(o, byRole[o.value] || 0, o.value === s.role); });
    // employer type
    pool = jobs.filter(function (j) { return matchesState(j, without(s, "type")); });
    var byType = tally(pool, function (j) { return [j.ct]; });
    [].forEach.call(field("type").options, function (o) { setOption(o, byType[o.value] || 0, o.value === s.type); });
    // posted date (the ranges overlap: a job from yesterday is also in "last week")
    pool = jobs.filter(function (j) { return matchesState(j, without(s, "posted")); });
    var byPosted = tally(pool, function (j) {
      var d = daysAgo(j.p);
      return d > 30 ? ["older"] : ["1", "2", "7", "30"].filter(function (v) { return d <= Number(v); });
    });
    [].forEach.call(field("posted").options, function (o) { setOption(o, byPosted[o.value] || 0, o.value === s.posted); });
    // work mode buttons
    pool = jobs.filter(function (j) { return matchesState(j, without(s, "modes")); });
    var byMode = tally(pool, function (j) { return [j.w]; });
    [].forEach.call(finder.querySelectorAll("[name=mode]"), function (box) {
      var n = byMode[box.value] || 0, span = box.nextElementSibling;
      span.textContent = span.getAttribute("data-label") + " (" + n.toLocaleString() + ")";
      box.disabled = n === 0 && !box.checked;
      box.parentNode.classList.toggle("is-empty", box.disabled);
    });
  }

  function activeFilters(s) {
    return (s.country ? 1 : 0) + (s.role ? 1 : 0) + (s.posted ? 1 : 0) + (s.type ? 1 : 0) + s.modes.length + (company ? 1 : 0);
  }

  function update() {
    var s = readState();
    matches = jobs.filter(function (j) { return matchesState(j, s); });
    if (s.sort === "closing") {
      matches.sort(function (a, b) {
        if (a.x && b.x) return a.x < b.x ? -1 : a.x > b.x ? 1 : 0;
        if (a.x) return -1;
        if (b.x) return 1;
        return a.p < b.p ? 1 : -1;
      });
    } else {
      matches.sort(function (a, b) { return a.p < b.p ? 1 : a.p > b.p ? -1 : 0; });
    }
    var n = activeFilters(s);
    activeBadge.textContent = n;
    activeBadge.hidden = n === 0;
    writeUrl(s);
    updateCounts(s);
    render(true);
  }

  // ----- the filter sheet on phones -----
  var lastFocus = null;
  function openSheet() {
    lastFocus = document.activeElement;
    sheet.classList.add("is-open");
    scrim.classList.add("is-open");
    document.body.classList.add("sheet-open");
    openBtn.setAttribute("aria-expanded", "true");
    var first = sheet.querySelector("select, input, button");
    if (first) setTimeout(function () { first.focus({ preventScroll: true }); }, 50);
  }
  function closeSheet() {
    if (!sheet.classList.contains("is-open")) return;
    sheet.classList.remove("is-open");
    scrim.classList.remove("is-open");
    document.body.classList.remove("sheet-open");
    openBtn.setAttribute("aria-expanded", "false");
    if (lastFocus && lastFocus.focus) lastFocus.focus({ preventScroll: true });
    var bar = finder.querySelector(".results-bar");
    if (bar && bar.getBoundingClientRect().top < 0) finder.scrollIntoView();
  }
  openBtn.addEventListener("click", openSheet);
  scrim.addEventListener("click", closeSheet);
  [].forEach.call(finder.querySelectorAll("[data-sheet-close]"), function (b) { b.addEventListener("click", closeSheet); });
  document.addEventListener("keydown", function (e) { if (e.key === "Escape") closeSheet(); });

  // ----- events -----
  form.addEventListener("submit", function (e) {
    e.preventDefault();
    qInput.blur(); // closes the phone keyboard
    update();
    var smooth = !(window.matchMedia && matchMedia("(prefers-reduced-motion: reduce)").matches);
    try { finder.scrollIntoView({ behavior: smooth ? "smooth" : "auto", block: "start" }); } catch (err) { finder.scrollIntoView(); }
  });
  qInput.addEventListener("input", function () { if (jobs.length) update(); });
  finder.addEventListener("change", function () { if (jobs.length) update(); });
  moreBtn.addEventListener("click", function () { render(false); });
  finder.querySelector("[data-reset]").addEventListener("click", function () {
    [].forEach.call(finder.querySelectorAll(".filters select"), function (s) { s.selectedIndex = 0; });
    [].forEach.call(finder.querySelectorAll("[name=mode]"), function (b) { b.checked = false; });
    qInput.value = ""; company = "";
    update();
  });

  applyUrl();
  fetch(finder.getAttribute("data-index"))
    .then(function (r) { if (!r.ok) throw new Error(r.status); return r.json(); })
    .then(function (data) { jobs = data.jobs; update(); })
    .catch(function () { countEl.textContent = "Showing the newest jobs. Refresh to use filters."; });
})();
