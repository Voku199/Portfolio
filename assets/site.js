/* Společné chování všech stránek: tmavý režim, jazyk, odkrývání a drobné animace.
   České texty jsou přímo v HTML, anglické v <script id="i18n">, takže se nic nepíše dvakrát. */
(function () {
  'use strict';

  var root = document.documentElement;
  var $$ = function (s, r) { return Array.prototype.slice.call((r || document).querySelectorAll(s)); };
  var $ = function (s, r) { return (r || document).querySelector(s); };
  var calm = matchMedia('(prefers-reduced-motion: reduce)').matches;
  var store = function (k, v) {
    try { if (v === undefined) return localStorage.getItem(k); localStorage.setItem(k, v); } catch (e) { return null; }
  };

  var I18N = {};
  var node = $('#i18n');
  if (node) { try { I18N = JSON.parse(node.textContent); } catch (e) { I18N = {}; } }

  var COMMON = {
    cs: {
      skip: 'Přeskočit na obsah', navHow: 'Jak funguju', navProjects: 'Projekty', navMenu: 'Menu',
      toDark: 'Zapnout tmavý režim', toLight: 'Zapnout světlý režim',
      footQuote: '„Neboj se říct <span class="brush">svůj názor</span>.“', footLines: 'řádků kódu',
      footType: 'Obraz je z ASCII znaků a každý znak je jeden tah štětcem.',
      pingWait: 'Zkouším spojení…', pingOn: 'Běží', pingOff: 'Teď neodpovídá'
    },
    en: {
      skip: 'Skip to content', navHow: 'How I work', navProjects: 'Projects', navMenu: 'Menu',
      toDark: 'Switch to dark mode', toLight: 'Switch to light mode',
      footQuote: '“Don’t be afraid to <span class="brush">speak your mind</span>.”', footLines: 'lines of code',
      footType: 'The painting is made of ASCII characters, each one a brush stroke.',
      pingWait: 'Checking…', pingOn: 'Online', pingOff: 'Not answering'
    }
  };

  /* ── tmavý režim: ranní papír, nebo noc ── */
  var themeBtn = $('.theme');
  var themeMeta = $('meta[name="theme-color"]');
  var lang = 'cs';

  function paintThemeUi() {
    var dark = root.dataset.theme === 'dark';
    if (themeMeta) themeMeta.content = dark ? '#191815' : '#F0EEE6';
    if (themeBtn) {
      var label = COMMON[lang][dark ? 'toLight' : 'toDark'];
      themeBtn.setAttribute('aria-pressed', dark);
      themeBtn.setAttribute('aria-label', label);
      themeBtn.title = label;
    }
  }

  function setTheme(next) {
    root.dataset.theme = next;
    paintThemeUi();
    document.dispatchEvent(new CustomEvent('voku:theme', { detail: next }));
  }

  if (themeBtn) {
    themeBtn.addEventListener('click', function () {
      var next = root.dataset.theme === 'dark' ? 'light' : 'dark';
      store('theme', next);
      if (!document.startViewTransition || calm) { setTheme(next); return; }
      /* nová barva se rozlije od tlačítka jako inkoust */
      var box = themeBtn.getBoundingClientRect();
      var x = box.left + box.width / 2, y = box.top + box.height / 2;
      var end = Math.hypot(Math.max(x, innerWidth - x), Math.max(y, innerHeight - y));
      root.classList.add('is-theming');
      var vt = document.startViewTransition(function () { setTheme(next); });
      vt.ready.then(function () {
        root.animate(
          { clipPath: ['circle(0px at ' + x + 'px ' + y + 'px)', 'circle(' + end + 'px at ' + x + 'px ' + y + 'px)'] },
          { duration: 760, easing: 'cubic-bezier(.65, 0, .35, 1)', pseudoElement: '::view-transition-new(root)' }
        );
      }).catch(function () {});
      vt.finished.then(function () { root.classList.remove('is-theming'); }, function () { root.classList.remove('is-theming'); });
    });
  }

  /* ── jazyk ── */
  var CS = { html: new WeakMap(), attr: new WeakMap(), title: document.title };
  var langListeners = [];

  function text(key) {
    var pack = lang === 'en' ? I18N.en : null;
    return (pack && pack[key]) || COMMON[lang][key] || (I18N.cs && I18N.cs[key]) || COMMON.cs[key] || key;
  }

  function setLang(l) {
    if (l !== 'cs' && l !== 'en') return;
    lang = l;
    root.lang = l;
    var en = I18N.en || {};
    var k = l === 'cs' ? 0 : 1;

    $$('[data-t]').forEach(function (el) {
      var key = el.dataset.t;
      if (!CS.html.has(el)) CS.html.set(el, el.innerHTML);
      if (l === 'cs') el.innerHTML = CS.html.get(el);
      else if (en[key] != null) el.innerHTML = en[key];
      else if (COMMON.en[key] != null) el.innerHTML = COMMON.en[key];
    });
    [['tAria', 'aria-label'], ['tAlt', 'alt'], ['tPh', 'placeholder'], ['tTitle', 'title'], ['tHref', 'href']].forEach(function (pair) {
      $$('[data-' + pair[0].replace(/[A-Z]/g, function (m) { return '-' + m.toLowerCase(); }) + ']').forEach(function (el) {
        var id = pair[1] + ':' + el.dataset[pair[0]];
        if (!CS.attr.has(el)) CS.attr.set(el, {});
        var bag = CS.attr.get(el);
        if (!(id in bag)) bag[id] = el.getAttribute(pair[1]);
        var v = l === 'cs' ? bag[id] : (en[el.dataset[pair[0]]] != null ? en[el.dataset[pair[0]]] : COMMON.en[el.dataset[pair[0]]]);
        if (v != null) el.setAttribute(pair[1], v);
      });
    });
    ['p', 'try', 'note'].forEach(function (group) {
      if (!I18N[group]) return;
      $$('[data-' + group + ']').forEach(function (el) {
        var v = I18N[group][el.dataset[group]];
        if (v) el.textContent = v[k];
      });
    });
    if (I18N.cats) {
      $$('[data-cat-label]').forEach(function (el) {
        var c = I18N.cats[el.dataset.catLabel];
        if (c) el.textContent = c[k];
      });
    }
    $$('.ping[data-state]').forEach(function (p) { p.textContent = COMMON[l][p.dataset.state]; });
    document.title = l === 'cs' ? CS.title : (en.title || CS.title);
    $$('.lang-switch button').forEach(function (b) {
      var on = b.dataset.lang === l;
      b.classList.toggle('active', on);
      b.setAttribute('aria-pressed', on);
    });
    store('lang', l);
    paintThemeUi();
    langListeners.forEach(function (fn) { fn(l); });
  }

  $$('.lang-switch button').forEach(function (b) {
    b.addEventListener('click', function () { setLang(b.dataset.lang); });
  });

  /* ── odpovídá server? no-cors: stačí, že se spojení povede ── */
  function ping(el) {
    var dot = $('.ping', el) || el;
    if (el.dataset.pinged) return;
    el.dataset.pinged = '1';
    dot.dataset.state = 'pingWait';
    dot.textContent = COMMON[lang].pingWait;
    var ctl = 'AbortController' in window ? new AbortController() : null;
    var timer = setTimeout(function () { if (ctl) ctl.abort(); }, 7000);
    fetch(el.dataset.ping, { mode: 'no-cors', cache: 'no-store', signal: ctl && ctl.signal })
      .then(function () { dot.dataset.state = 'pingOn'; dot.classList.add('is-on'); })
      .catch(function () { dot.dataset.state = 'pingOff'; dot.classList.add('is-off'); })
      .then(function () { clearTimeout(timer); dot.textContent = COMMON[lang][dot.dataset.state]; });
  }

  function onSeen(items, fn, margin) {
    if (!('IntersectionObserver' in window)) { items.forEach(fn); return; }
    var io = new IntersectionObserver(function (es) {
      es.forEach(function (e) { if (e.isIntersecting) { fn(e.target); io.unobserve(e.target); } });
    }, { rootMargin: margin || '0px 0px -8% 0px' });
    items.forEach(function (el) { io.observe(el); });
  }

  /* ── nadpisky se z náhodných znaků „dopíšou“ ── */
  var NOISE = '*~+=:.-/\\o';
  function scramble(el) {
    if (calm || el.children.length) return;
    var finalText = el.textContent;
    var start = performance.now(), dur = Math.min(760, 240 + finalText.length * 34);
    (function frame(now) {
      if (el.textContent.length !== finalText.length && !el.dataset.busy) return;
      el.dataset.busy = '1';
      var p = (now - start) / dur;
      if (p >= 1) { el.textContent = finalText; delete el.dataset.busy; return; }
      var shown = Math.floor(p * finalText.length), out = finalText.slice(0, shown);
      for (var i = shown; i < finalText.length; i++) {
        out += finalText[i] === ' ' ? ' ' : NOISE[Math.floor(Math.random() * NOISE.length)];
      }
      el.textContent = out;
      requestAnimationFrame(frame);
    })(start);
  }

  /* ── čísla se dopočítají, když na ně dojde řada ── */
  function countUp(el) {
    var m = /^(\D*)(\d+)(.*)$/.exec(el.textContent.trim());
    if (!m || calm) return;
    var to = +m[2], start = performance.now(), dur = 1100;
    (function frame(now) {
      var p = Math.min(1, (now - start) / dur);
      el.textContent = m[1] + Math.round(to * (1 - Math.pow(1 - p, 3))) + m[3];
      if (p < 1) requestAnimationFrame(frame);
    })(start);
  }

  /* ── ASCII hladina v předělech a v patičce ── */
  function waves(el) {
    var width = 260;
    function row(chance) {
      var out = '';
      for (var i = 0; i < width; i++) out += Math.random() < chance ? (Math.random() < .7 ? '~' : '-') : ' ';
      return out;
    }
    ['a', 'b'].forEach(function (name) {
      var s = document.createElement('span');
      s.className = 'waves__' + name;
      s.textContent = row(.22) + '\n' + row(.13);
      el.appendChild(s);
    });
  }

  /* ── kde na dlouhé stránce zrovna jsem ── */
  function rail() {
    var links = $$('.rail a');
    if (!links.length || !('IntersectionObserver' in window)) return;
    var map = new Map();
    links.forEach(function (a) { var s = $(a.getAttribute('href')); if (s) map.set(s, a); });
    var io = new IntersectionObserver(function (es) {
      es.forEach(function (e) {
        if (!e.isIntersecting) return;
        links.forEach(function (a) { a.removeAttribute('aria-current'); });
        map.get(e.target).setAttribute('aria-current', 'true');
      });
    }, { rootMargin: '-45% 0px -50% 0px' });
    map.forEach(function (_, s) { io.observe(s); });
  }

  /* ── fotka: vážně, nebo vtipně ── */
  function photo() {
    var btn = $('.photo');
    if (!btn) return;
    btn.addEventListener('click', function () {
      var on = btn.getAttribute('aria-pressed') !== 'true';
      btn.setAttribute('aria-pressed', on);
    });
  }

  /* ── průběh zakázky na /jak-funguju/: krok posouvá obraz ── */
  function process() {
    var canvas = $('#proc-canvas');
    if (!canvas || !window.VokuAscii) return;
    var art = window.VokuAscii.mount(canvas, { stage: 1 });
    var steps = $$('.step');
    var bar = $('#proc-bar'), name = $('#proc-name'), num = $('#proc-num');
    var total = steps.length;
    function activate(step) {
      var i = steps.indexOf(step);
      steps.forEach(function (s, j) {
        s.classList.toggle('is-on', j === i);
        s.classList.toggle('is-done', j < i);
      });
      art.setStage(+step.dataset.stage, 1100);
      if (bar) bar.textContent = '[' + new Array(i + 2).join('#') + new Array(total - i).join('-') + ']';
      if (num) num.textContent = (i + 1) + '/' + total;
      if (name) name.innerHTML = $('.step__state', step).innerHTML;
    }
    activate(steps[0]);
    if ('IntersectionObserver' in window) {
      var io = new IntersectionObserver(function (es) {
        es.forEach(function (e) { if (e.isIntersecting) activate(e.target); });
      }, { rootMargin: '-48% 0px -48% 0px' });
      steps.forEach(function (s) { io.observe(s); });
    } else {
      art.setStage(7);
    }
    langListeners.push(function () {
      var on = $('.step.is-on');
      if (on && name) name.innerHTML = $('.step__state', on).innerHTML;
    });
  }

  /* ── spuštění ── */
  $$('[data-waves]').forEach(waves);
  setLang(store('lang') === 'en' ? 'en' : 'cs');
  paintThemeUi();

  var heroCanvas = $('#hero-canvas');
  if (heroCanvas && window.VokuAscii) {
    window.VokuAscii.mount(heroCanvas, { intro: true, host: $('.hero'), quietEl: $('.hero__text') });
  }
  process();
  rail();
  photo();

  var rv = $$('.rv-auto, .block__head, .block__body > *, .cells > *, .sec-head, .doors > *');
  rv.forEach(function (el, i) { el.classList.add('rv'); });
  onSeen(rv, function (el) { el.classList.add('is-in'); });
  onSeen($$('.kicker span, [data-scramble]'), scramble);
  onSeen($$('[data-count]'), countUp);
  onSeen($$('[data-ping]'), ping, '0px');

  window.VOKU = {
    text: text,
    onLang: function (fn) { langListeners.push(fn); },
    get lang() { return lang; },
    ping: ping, store: store, calm: calm
  };
})();
