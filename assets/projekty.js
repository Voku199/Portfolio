/* /projekty/: filtr, hledání, řazení, výběr projektu a ovládání klávesnicí. */
(function () {
  'use strict';

  var $$ = function (s, r) { return Array.prototype.slice.call((r || document).querySelectorAll(s)); };
  var list = document.getElementById('list');
  var pane = document.getElementById('pane');
  var q = document.getElementById('q');
  var sortSel = document.getElementById('sort');
  var empty = document.getElementById('empty');
  var countEl = document.getElementById('count');
  var cards = $$('.p', list);
  var bySlug = {};
  var cat = 'all';
  var current = null;
  var wide = matchMedia('(min-width: 980px) and (min-height: 560px)');
  var fold = function (s) { return s.normalize('NFD').replace(/[̀-ͯ]/g, '').toLowerCase(); };

  cards.forEach(function (c) {
    bySlug[c.id] = c;
    c._text = fold(c.textContent);
    var row = c.querySelector('.p__row');
    row.addEventListener('click', function () { choose(c, { user: true }); });
  });

  function visible() { return cards.filter(function (c) { return !c.classList.contains('is-hidden'); }); }

  function hash(slug) {
    if (history.replaceState) history.replaceState(null, '', slug ? '#' + slug : location.pathname + location.search);
  }

  function showPane(c) {
    if (!pane) return;
    pane.innerHTML = c.querySelector('.p__more').innerHTML;
    pane.scrollTop = 0;
    $$('[data-ping]', pane).forEach(function (el) { delete el.dataset.pinged; if (window.VOKU) VOKU.ping(el); });
  }

  function choose(c, o) {
    o = o || {};
    if (!wide.matches && o.user && current === c) {
      /* na mobilu druhé klepnutí detail zavře */
      c.classList.remove('is-on');
      c.querySelector('.p__row').setAttribute('aria-expanded', 'false');
      current = null;
      hash('');
      return;
    }
    if (current) {
      current.classList.remove('is-on');
      current.querySelector('.p__row').setAttribute('aria-expanded', 'false');
    }
    current = c;
    if (!c) { if (pane) pane.innerHTML = ''; return; }
    c.classList.add('is-on');
    c.querySelector('.p__row').setAttribute('aria-expanded', 'true');
    if (wide.matches) showPane(c);
    else $$('[data-ping]', c).forEach(function (el) { if (window.VOKU) VOKU.ping(el); });
    if (o.hash !== false) hash(c.id);
    if (o.scroll) c.scrollIntoView({ block: 'nearest', behavior: 'auto' });
  }

  function apply() {
    var needle = fold(q.value.trim());
    var shown = 0;
    cards.forEach(function (c) {
      var inCat = cat === 'all' || (cat === 'try' ? c.dataset.can === "1" : c.dataset.cat === cat);
      var ok = inCat && (!needle || c._text.indexOf(needle) !== -1);
      c.classList.toggle('is-hidden', !ok);
      if (ok) shown++;
    });
    empty.classList.toggle('is-on', shown === 0);
    if (countEl) countEl.textContent = shown;
    if (wide.matches && (!current || current.classList.contains('is-hidden'))) {
      var first = visible()[0];
      if (first) choose(first, { hash: false });
      else if (pane) { choose(null); }
    }
  }

  function sort() {
    var by = sortSel.value;
    cards.sort(function (a, b) {
      if (by === 'lines') return b.dataset.lines - a.dataset.lines;
      if (by === 'name') return a.dataset.name.localeCompare(b.dataset.name, document.documentElement.lang);
      return a.dataset.date < b.dataset.date ? 1 : a.dataset.date > b.dataset.date ? -1 : 0;
    });
    cards.forEach(function (c) { list.insertBefore(c, empty); });
    apply();
    list.scrollTop = 0;
  }

  $$('.filters button').forEach(function (b) {
    b.addEventListener('click', function () {
      cat = b.dataset.f;
      $$('.filters button').forEach(function (x) {
        var on = x === b;
        x.classList.toggle('on', on);
        x.setAttribute('aria-pressed', on);
      });
      apply();
      list.scrollTop = 0;
    });
  });
  q.addEventListener('input', function () { apply(); list.scrollTop = 0; });
  sortSel.addEventListener('change', sort);

  /* ── klávesnice ── */
  function step(by) {
    var v = visible();
    if (!v.length) return;
    var i = v.indexOf(current);
    var next = v[Math.max(0, Math.min(v.length - 1, i + by))];
    choose(next, { scroll: true });
    next.querySelector('.p__row').focus({ preventScroll: true });
  }
  document.addEventListener('keydown', function (e) {
    if (e.ctrlKey || e.metaKey || e.altKey) return;
    var inField = /^(INPUT|SELECT|TEXTAREA)$/.test(e.target.tagName);
    if (e.key === '/' && !inField) { e.preventDefault(); q.focus(); q.select(); return; }
    if (e.target === q) {
      if (e.key === 'Escape') { q.value = ''; apply(); q.blur(); }
      if (e.key === 'ArrowDown') { e.preventDefault(); q.blur(); step(current ? 0 : 1); }
      if (e.key === 'Enter') { e.preventDefault(); var v = visible(); if (v[0]) { q.blur(); choose(current && !current.classList.contains('is-hidden') ? current : v[0], { scroll: true }); (current || v[0]).querySelector('.p__row').focus({ preventScroll: true }); } }
      return;
    }
    if (inField) return;
    if (e.key === 'ArrowDown' || e.key === 'j') { e.preventDefault(); step(1); }
    if (e.key === 'ArrowUp' || e.key === 'k') { e.preventDefault(); step(-1); }
    if (e.key === 'Enter' && e.target.classList && e.target.classList.contains('p__row') && wide.matches && current) {
      var link = current.querySelector('.d__go');
      if (link) { e.preventDefault(); window.open(link.href, '_blank', 'noopener'); }
    }
  });

  /* ── jazyk: detail se překreslí z přeloženého zdroje ── */
  if (window.VOKU) {
    VOKU.onLang(function () {
      cards.forEach(function (c) { c._text = fold(c.textContent); });
      if (current && wide.matches) showPane(current);
    });
  }
  wide.addEventListener('change', function () {
    if (wide.matches) {
      if (!current) { var f = visible()[0]; if (f) choose(f, { hash: false }); }
      else showPane(current);
    }
  });

  /* ── odkaz na konkrétní projekt, i když už je stránka otevřená ── */
  window.addEventListener('hashchange', function () {
    var c = bySlug[decodeURIComponent(location.hash.slice(1))];
    if (c && c !== current) {
      c.classList.remove('is-hidden');
      choose(c, { hash: false, scroll: true });
    }
  });

  /* ── první výběr: odkaz na konkrétní projekt, jinak nejnovější ── */
  var start = bySlug[decodeURIComponent(location.hash.slice(1))];
  if (start) choose(start, { hash: false, scroll: true });
  apply();
  /* mobil s odkazem: rozbalený projekt musí být vidět i pod lepicí lištou */
  if (start && !wide.matches) {
    requestAnimationFrame(function () {
      var y = start.getBoundingClientRect().top + scrollY - 140;
      scrollTo(0, y);
    });
  }
})();
