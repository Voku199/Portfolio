/* ASCII impresionismus.
   Fuji, torii a větev z GitHub profilu (Voku199/build.py) převedené na živý canvas.
   Každý znak je jeden tah štětcem a sousední znaky mají schválně jiný odstín,
   stejně jako lomené barvy u impresionistů. Zblízka šum, zdálky obraz.

   stage (0 až 7) říká, jak moc je obraz hotový:
     0-1 obrys hory   1-2 obloha a slunce   2-3 skála tužkou   3-4,6 sníh, voda a barvy
     4-5 torii        5-6,2 větev a květy   6-7 obraz ožije (mraky, okvětní lístky, hladina)
   Na úvodní stránce proběhne celé za pár vteřin, na /jak-funguju/ ho posouvá scroll.

   Světlý režim je svítání, tmavý je noc: slunce zapadne za horu a vyjde měsíc. */
(function () {
  'use strict';

  var TAU = Math.PI * 2;
  var LAST = 7;
  var clamp = function (v, a, b) { return Math.min(b === undefined ? 1 : b, Math.max(a === undefined ? 0 : a, v)); };
  var ease = function (t) { return t < .5 ? 4 * t * t * t : 1 - Math.pow(-2 * t + 2, 3) / 2; };

  function rng(seed) { /* mulberry32: stejné semínko = stejný obraz */
    return function () {
      seed = (seed + 0x6D2B79F5) | 0;
      var t = Math.imul(seed ^ (seed >>> 15), 1 | seed);
      t = (t + Math.imul(t ^ (t >>> 7), 61 | t)) ^ t;
      return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
    };
  }
  var pick = function (r, list) { return list[Math.floor(r() * list.length)]; };

  var PAL = {
    dawn: {
      sky: ['#E08A3C', '#EDA24E', '#D9A070', '#9A97C4', '#7FAAD6', '#D9673F'],
      rock: ['#3F5F96', '#5C5FA6', '#7A63B0', '#3F7FBF', '#4F7F8E'],
      warm: ['#C2552F', '#C4803F', '#A85F36', '#A0587E'],
      snow: ['#5F83B8', '#7E78BE', '#D9805F', '#6FA0D0'],
      water: ['#3F7FBF', '#5F8FC8', '#2F6FB0'],
      reflect: ['#5C5FA6', '#6F73B2', '#5F86B8'],
      glitter: ['#E5482A', '#E08A3C', '#D97757'],
      torii: '#C8402B', bark: ['#5A4638', '#6B5344'],
      pink: ['#EE8FAA', '#E5668C', '#CC4874'],
      cloud: ['#9A9DBD', '#AE9FBD', '#CFA27C'],
      orb: '#E5482A', rim: '#EE8A74', sketch: '#7E7C74',
      snowRamp: " .:;", flip: -1
    },
    night: {
      sky: ['#2F3D57', '#3A4A68', '#46405F', '#31495F'],
      rock: ['#7385A6', '#5F6F92', '#8A7FA8', '#4F6A8F'],
      warm: ['#8B93B5', '#A08FB0', '#6F7FA0'],
      snow: ['#DDE6F2', '#C7D4E8', '#E8DFEF', '#B8C9E0'],
      water: ['#3C5A7D', '#45678F', '#355070'],
      reflect: ['#34435A', '#3D4E68', '#473F5E'],
      glitter: ['#F2E6C4', '#D9CDA8', '#A89F86'],
      torii: '#E5533D', bark: ['#75625F', '#8A7470'],
      pink: ['#FFC2D1', '#F48FB1', '#C9688C'],
      cloud: ['#47536A', '#3E4A60', '#54506E'],
      orb: '#F2E6C4', rim: '#A89F86', star: '#AAB6C8', sketch: '#8F8B80',
      snowRamp: '+*#%', flip: 1
    }
  };

  var TORII = [
    '._____________.',
    " '-+-------+-' ",
    '  =+=======+=  ',
    '   |       |   ',
    '   |       |   ',
    '   |       |   '
  ];

  /* ── rozvržení, které je pro oba režimy stejné ── */
  function layout(w, h) {
    var cw = w < 560 ? 7 : 8;
    var ch = Math.round(cw * 1.75);
    var cols = Math.ceil(w / cw) + 1;
    var rows = Math.ceil(h / ch) + 1;
    var aspect = w / h;
    var tall = aspect < 1.05;
    var H = Math.round(rows * (tall ? .7 : .72));
    var peakC = Math.round(cols * (tall ? .56 : .69));
    var wd = cols * (tall ? .46 : .205);
    /* výška hory podle šířky, jinak by v úzkém plátně vyrostla jehla */
    var rise = Math.min(H - rows * .16, wd * (tall ? 2.7 : 2.2) * cw * .62 / ch);
    var peakR = H - rise;
    var top = function (c) {
      var d = Math.max(0, Math.abs(c - peakC) - 2.5);
      return H - rise * Math.exp(-Math.pow(d / wd, 1.15));
    };
    return {
      w: w, h: h, cw: cw, ch: ch, cols: cols, rows: rows, H: H, peakC: peakC, peakR: peakR, wd: wd, top: top,
      fs: cw / .6,
      baseY: function (r) { return (r + 1) * ch - Math.round(ch * .22); },
      orbX: (peakC - cols * (tall ? .24 : .09)) * cw,
      orbY: Math.max(peakR * ch * (tall ? .88 : .95), h * .17),
      orbR: Math.min(w * .09, h * .085, 74) + 8,
      toriiC: Math.round(cols * (tall ? .08 : .1)),
      toriiR: H - 4,
      k: clamp(cols / 125, aspect < .8 ? .85 : .62, 1.35)
    };
  }

  /* ── statická scéna jednoho režimu ── */
  function scene(L, theme, quiet) {
    var P = PAL[theme];
    var r = rng(199);
    var cells = [], branchCells = [];
    var mask = new Uint8Array(L.cols * L.rows);
    var at = function (rr, c) { return rr * L.cols + c; };
    var inside = function (rr, c) { return rr >= 0 && rr < L.rows && c >= 0 && c < L.cols; };
    var isQuiet = function (rr, c) { return quiet && quiet(c * L.cw, rr * L.ch); };

    /* t = kdy se znak objeví, tc = kdy dostane barvu (do té doby je to skica tužkou) */
    var add = function (list, rr, c, ch, col, a, t, tc) {
      list.push({ r: rr, c: c, ch: ch, col: col, a: a, t: t, tc: Math.max(t, tc === undefined ? 3 + r() * .9 : tc) });
    };
    var used = {};
    var put = function (rr, c, ch, col, a, t, tc) {
      c = Math.round(c);
      if (!inside(rr, c)) return;
      var key = at(rr, c);
      if (used[key] !== undefined) { cells[used[key]] = null; }
      used[key] = cells.length;
      add(cells, rr, c, ch, col, a, t, tc);
    };

    /* hora */
    var ramp = ' .:-=+*#';
    var k = L.wd / 30;
    var rockRows = L.H - L.peakR;
    for (var c = 0; c < L.cols; c++) {
      var first = Math.ceil(L.top(c));
      for (var rr = first; rr < L.H; rr++) {
        var dx = (c - L.peakC) / k;
        var height = (L.H - rr) / rockRows;
        var ridge = Math.sin(Math.atan2(dx * .55, (rr - L.peakR) / k + 1.5) * 14);
        var snowline = .66 + .07 * Math.sin(c * .55 / k) + .03 * ridge;
        var fade = clamp(.26 + (L.H - rr) / (rockRows * .7), .26, 1) * (isQuiet(rr, c) ? .2 : 1);
        var sweep = 2 + (1 - height) * .7 + r() * .3;
        mask[at(rr, c)] = 1;
        if (rr === first && height > .1 && Math.abs(dx) < 50) {
          var slope = L.top(c + 1) - L.top(c - 1);
          var edge = Math.abs(slope) < .2 ? '_' : (slope < 0 ? '/' : '\\');
          var sn = height > snowline;
          put(rr, c, edge, pick(r, sn ? P.snow : P.rock), sn ? 1 : fade, (c - (L.peakC - L.wd * 2)) / (L.wd * 4));
        } else if (height > snowline) {
          var si = clamp(Math.floor((.55 - dx / 26 + .18 * ridge) * 4), 0, 3);
          var sc = P.snowRamp[si];
          if (sc !== ' ') put(rr, c, sc, pick(r, P.snow), 1, 3 + r() * .9);
        } else {
          var side = P.flip * -dx / 40;
          var v = .42 + .3 * clamp(side, -1, 1) + .1 * ridge;
          v *= clamp((52 - Math.abs(dx)) / 16);
          var ci = clamp(Math.floor(v * ramp.length), 0, ramp.length - 1);
          if (ramp[ci] !== ' ') {
            var warmSide = dx < 0 ? .3 : .1;
            put(rr, c, ramp[ci], pick(r, r() < warmSide ? P.warm : P.rock), fade, sweep);
          }
        }
      }
    }

    /* obloha: řídké tahy, které houstnou kolem slunce a mizí pod textem */
    for (var sr = 0; sr < L.H; sr++) {
      for (var sc2 = 0; sc2 < L.cols; sc2++) {
        if (mask[at(sr, sc2)]) continue;
        var dist = Math.hypot(sc2 * L.cw - L.orbX, sr * L.ch - L.orbY) / L.orbR;
        var p = .035 + .3 * Math.exp(-Math.pow(dist / 2.6, 2)) + .03 * (sr / L.H);
        var q = isQuiet(sr, sc2);
        if (q) p *= .12;
        if (r() < p) {
          put(sr, sc2, pick(r, ['.', ',', "'", '`', '.']), pick(r, P.sky), (q ? .3 : .55) + r() * (q ? .15 : .4), 1 + r());
        }
      }
    }

    /* obzor: část obrysu, kterou je vidět od první vteřiny */
    for (var hc = 0; hc < L.cols; hc += 1) {
      if (r() < .55 && !mask[at(L.H - 1, hc)]) put(L.H, hc, '-', pick(r, P.water), .6, hc / L.cols);
    }

    /* voda: dlouhé vodorovné tahy a odraz hory */
    var waterFade = function (rr) { return clamp(.95 - (rr - L.H) / (L.rows - L.H) * .6, .3, .95); };
    var streaks = function (rr, lo, hi, n, chars, pal, boost) {
      for (var i = 0; i < n; i++) {
        var len = 3 + Math.floor(r() * 11);
        var start = lo + Math.floor(r() * Math.max(1, hi - lo - len));
        for (var x = start; x < start + len; x++) {
          put(rr, x, pick(r, chars), pick(r, pal), waterFade(rr) * (boost || 1), 3 + (rr - L.H) / (L.rows - L.H) * .45 + r() * .45);
        }
      }
    };
    var orbCol = Math.round(L.orbX / L.cw);
    var density = L.cols / 125;
    for (var w = L.H; w < L.rows; w++) {
      var depth = w - L.H;
      streaks(w, 0, L.cols - 1, Math.max(2, Math.round(3 * density)), '-', P.water);
      var mirrored = L.H - 1 - depth * 1.6;
      var lo = null, hi = null;
      for (var mc = 0; mc < L.cols; mc++) { if (mirrored >= L.top(mc)) { if (lo === null) lo = mc; hi = mc; } }
      if (lo !== null) streaks(w, lo, hi, Math.max(2, Math.round((7 - depth * .6) * density)), '-=-~', P.reflect);
      var half = Math.max(1, Math.round((8 - depth * .6) * L.k));
      streaks(w, orbCol - half, orbCol + half, 1, '=-', P.glitter, 1.1);
    }

    /* torii: hora za bránou se vymaže, jinak by se znaky slily */
    for (var cr = L.toriiR - 1; cr < L.H; cr++) {
      for (var cc2 = L.toriiC - 2; cc2 < L.toriiC + 18; cc2++) {
        var hit = inside(cr, cc2) ? used[at(cr, cc2)] : undefined;
        if (hit !== undefined) { cells[hit] = null; delete used[at(cr, cc2)]; }
        if (inside(cr, cc2)) mask[at(cr, cc2)] = 0;
      }
    }
    TORII.forEach(function (line, i) {
      for (var j = 0; j < line.length; j++) {
        var tr = L.toriiR + i, tc = L.toriiC + j;
        if (inside(tr, tc)) mask[at(tr, tc)] = line[j] === ' ' ? mask[at(tr, tc)] : 1;
        if (line[j] !== ' ') put(tr, tc, line[j], P.torii, 1, 4 + i * .13 + j * .006, 4 + i * .13);
      }
    });
    [L.toriiC + 3, L.toriiC + 11].forEach(function (pc) {
      for (var pr = L.toriiR + TORII.length; pr < L.toriiR + TORII.length + 4; pr++) {
        put(pr, pc, ':', P.torii, .4, 4.8, 4.8);
      }
    });

    /* větev v pravém horním rohu */
    var bx = function (c0) { return L.cols - 1 - (124 - c0) * L.k; };
    var by = function (r0) { return r0 * L.k; };
    var wood = {};
    var line = function (points) {
      for (var i = 0; i < points.length - 1; i++) {
        var a = points[i], b = points[i + 1];
        var c0 = bx(a[0]), r0 = by(a[1]), c1 = bx(b[0]), r1 = by(b[1]);
        var n = Math.ceil(Math.max(Math.abs(c1 - c0), Math.abs(r1 - r0)));
        var prev = Math.round(r0);
        for (var s = 0; s <= n; s++) {
          var rr2 = Math.round(r0 + (r1 - r0) * s / Math.max(1, n));
          var cc = Math.round(c0 + (c1 - c0) * s / Math.max(1, n));
          var chh;
          if (Math.abs(c1 - c0) >= Math.abs(r1 - r0)) chh = rr2 === prev ? '_' : ((c1 - c0) * (r1 - r0) < 0 ? '/' : '\\');
          else chh = c1 === c0 ? '|' : ((c1 - c0) * (r1 - r0) < 0 ? '/' : '\\');
          prev = rr2;
          if (inside(rr2, cc)) {
            wood[at(rr2, cc)] = 1;
            mask[at(rr2, cc)] = 1;
            var from = (L.cols - cc) / (L.cols - bx(90));
            add(branchCells, rr2, cc, chh, pick(r, P.bark), 1, 5 + clamp(from) * .5, 5);
          }
        }
      }
    };
    line([[124, 0], [116, 1], [108, 3], [101, 4], [95, 7]]);
    line([[112, 2], [108, 1], [101, 0]]);
    line([[106, 3], [104, 7], [102, 9]]);
    line([[118, 1], [117, 5], [114, 8]]);
    [[94, 8, 2.6], [101, 1.5, 2.6], [102, 10, 2.4], [114, 9, 2.6], [109, 4.5, 3], [119, 3.5, 3]].forEach(function (cn) {
      var cc = bx(cn[0]), cr = by(cn[1]), rad = cn[2] * L.k;
      for (var rr3 = Math.floor(cr - rad); rr3 <= cr + rad; rr3++) {
        for (var c3 = Math.floor(cc - rad * 2); c3 <= cc + rad * 2; c3++) {
          if (!inside(rr3, c3) || wood[at(rr3, c3)]) continue;
          var d = Math.hypot((c3 - cc) / 2, rr3 - cr) / rad;
          var hue = r();
          if (d < .55 && r() < .8) {
            mask[at(rr3, c3)] = 1;
            add(branchCells, rr3, c3, pick(r, ['*', '*', 'o']), P.pink[hue < .6 ? 0 : hue < .9 ? 1 : 2], 1, 5.4 + r() * .8, 5.4);
          } else if (d < 1 && r() < .28) {
            mask[at(rr3, c3)] = 1;
            add(branchCells, rr3, c3, pick(r, ['*', '.', "'"]), P.pink[hue < .6 ? 1 : 2], 1, 5.4 + r() * .8, 5.4);
          }
        }
      }
    });

    return { cells: cells.filter(Boolean), branch: branchCells, mask: mask, P: P };
  }

  /* ── živé vrstvy jsou pro oba režimy společné, liší se jen barvou ── */
  function life(L, quiet) {
    var r = rng(77);
    var clouds = [];
    [[.09, .15], [.22, .3]].forEach(function (band, b) {
      var n = Math.max(1, Math.round(L.cols / 62));
      for (var i = 0; i < n; i++) {
        var cc = Math.floor(r() * L.cols), cr = Math.round((band[0] + r() * (band[1] - band[0])) * L.rows);
        var len = 14 + Math.floor(r() * 12);
        [.55, 1, .7].forEach(function (sh, row) {
          var half = Math.floor(len * sh / 2);
          var st = cc + Math.floor(r() * 7) - 3;
          for (var x = st - half; x <= st + half; x++) {
            clouds.push({ c: x, r: cr + row, ch: Math.abs(x - st) > half - 2 ? '.' : '-', tone: Math.floor(r() * 3), band: b });
          }
        });
      }
    });

    var stars = [];
    for (var s = 0; s < Math.round(L.cols * L.rows / 190); s++) {
      var sc = Math.floor(r() * L.cols), sr = Math.floor(r() * L.H * .75);
      stars.push({ c: sc, r: sr, ch: r() < .75 ? '.' : (r() < .7 ? '+' : '*'), ph: r() * TAU, sp: .5 + r() * .7, q: !!(quiet && quiet(sc * L.cw, sr * L.ch)) });
    }

    var shimmer = [[], []];
    for (var w = L.H; w < L.rows; w++) {
      for (var l = 0; l < 2; l++) {
        for (var i2 = 0; i2 < Math.max(1, Math.round(2 * L.cols / 125)); i2++) {
          var len2 = 4 + Math.floor(r() * 14), st2 = Math.floor(r() * L.cols);
          for (var x2 = st2; x2 < st2 + len2; x2++) shimmer[l].push({ c: x2, r: w, tone: Math.floor(r() * 3) });
        }
      }
    }

    var petals = [];
    var count = clamp(Math.round(L.w / 70), 6, 22);
    for (var p = 0; p < count; p++) {
      petals.push({
        x: L.w * (.5 + r() * .55), y: -24 + r() * L.h * .24,
        dur: 22 + r() * 18, ph: r(), size: 12 + Math.floor(r() * 3),
        drift: L.w * (.28 + r() * .24), drop: L.h * (.8 + r() * .25), sway: 22 + r() * 24,
        waves: 1.5 + Math.floor(r() * 3) * .75, spin: (r() < .5 ? -1 : 1) * (200 + r() * 220),
        ch: pick(r, ['*', ',', '*', '~']), tone: Math.floor(r() * 3)
      });
    }
    return { clouds: clouds, stars: stars, shimmer: shimmer, petals: petals };
  }

  /* ── plátno ── */
  function mount(canvas, opts) {
    opts = opts || {};
    var calm = matchMedia('(prefers-reduced-motion: reduce)').matches;
    var host = opts.host || canvas;
    var ctx = canvas.getContext('2d');
    var dpr = 1, L = null, world = {}, lives = null, layers = {};
    var stage = opts.intro && !calm ? 0 : (opts.stage === undefined ? LAST : opts.stage);
    var from = stage, target = opts.stage === undefined ? LAST : opts.stage, tweenAt = 0, tweenFor = 0;
    var dusk = document.documentElement.dataset.theme === 'dark' ? 1 : 0;
    var duskFrom = dusk, duskTo = dusk, duskAt = 0;
    var ripples = [], running = false, visible = true, last = 0, raf = 0, dirty = true;
    var lastRipple = { x: -999, y: -999 };

    function offscreen() {
      var c = document.createElement('canvas');
      c.width = canvas.width; c.height = canvas.height;
      var x = c.getContext('2d');
      x.setTransform(dpr, 0, 0, dpr, 0, 0);
      x.textBaseline = 'alphabetic';
      x.font = font();
      return { c: c, x: x, s: -1 };
    }
    function font() { return L.fs.toFixed(2) + 'px "Geist Mono", ui-monospace, "Cascadia Mono", Consolas, monospace'; }

    function rebuild() {
      var box = canvas.getBoundingClientRect();
      var w = Math.round(box.width), h = Math.round(box.height);
      if (!w || !h) return false;
      dpr = Math.min(window.devicePixelRatio || 1, 2);
      canvas.width = Math.round(w * dpr);
      canvas.height = Math.round(h * dpr);
      ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
      L = layout(w, h);
      ctx.font = font();
      ctx.textBaseline = 'alphabetic';
      var quiet = null;
      if (opts.quietEl) {
        var q = opts.quietEl.getBoundingClientRect();
        var pad = 24;
        var x0 = q.left - box.left - pad, y0 = q.top - box.top - pad, x1 = q.right - box.left + pad, y1 = q.bottom - box.top + pad;
        if (x1 < w * .9) quiet = function (x, y) { return x > x0 && x < x1 && y > y0 && y < y1; };
      }
      world = { dawn: scene(L, 'dawn', quiet), night: scene(L, 'night', quiet) };
      lives = life(L, quiet);
      layers = { dawn: { base: offscreen(), branch: offscreen() }, night: { base: offscreen(), branch: offscreen() } };
      dirty = true;
      return true;
    }

    function bakeInto(layer, cells, sketch, s, W, H) {
      if (layer.s === s) return;
      layer.s = s;
      var x = layer.x;
      x.clearRect(0, 0, W, H);
      var fill = '';
      for (var i = 0; i < cells.length; i++) {
        var c = cells[i];
        if (s < c.t) continue;
        var coloured = s >= c.tc;
        var col = coloured ? c.col : sketch;
        if (col !== fill) { x.fillStyle = col; fill = col; }
        x.globalAlpha = coloured ? c.a : Math.max(c.a, .65);
        x.fillText(c.ch, c.c * L.cw, L.baseY(c.r));
      }
      x.globalAlpha = 1;
    }

    function drawOrb(P, mask, cx, cy, alpha, pulse) {
      if (alpha <= 0) return;
      var R = L.orbR;
      var r0 = Math.max(0, Math.floor((cy - R) / L.ch)), r1 = Math.min(L.H - 1, Math.ceil((cy + R) / L.ch));
      var c0 = Math.max(0, Math.floor((cx - R) / L.cw)), c1 = Math.min(L.cols - 1, Math.ceil((cx + R) / L.cw));
      for (var r = r0; r <= r1; r++) {
        for (var c = c0; c <= c1; c++) {
          if (mask[r * L.cols + c]) continue;
          var d = Math.hypot(c * L.cw + L.cw / 2 - cx, L.baseY(r) - 4 - cy);
          if (d >= R) continue;
          var core = d < R - 9;
          ctx.fillStyle = core ? P.orb : P.rim;
          ctx.globalAlpha = alpha * pulse;
          ctx.fillText(core ? 'O' : 'o', c * L.cw, L.baseY(r));
        }
      }
    }

    function render(now) {
      var W = L.w, H = L.h;
      var t = now / 1000;
      ctx.clearRect(0, 0, W, H);
      var s = stage;
      var skyA = clamp(s - 1), liveA = clamp(s - 6);
      var moving = !calm;
      var key = dusk < .5 ? 'dawn' : 'night';
      var P = world[key].P;
      var mask = world.dawn.mask;

      /* hvězdy jen v noci */
      if (dusk > 0) {
        ctx.fillStyle = PAL.night.star;
        lives.stars.forEach(function (st) {
          if (mask[st.r * L.cols + st.c]) return;
          var tw = moving ? .3 + .7 * (.5 + .5 * Math.sin(t * st.sp + st.ph)) : .7;
          ctx.globalAlpha = dusk * skyA * tw * (st.q ? .3 : 1);
          ctx.fillText(st.ch, st.c * L.cw, L.baseY(st.r));
        });
      }

      /* slunce zapadá za horu, měsíc vychází */
      var pulse = moving ? .88 + .12 * Math.sin(t * .5) : 1;
      var dropBy = L.orbR * 4.4;
      drawOrb(PAL.dawn, mask, L.orbX, L.orbY + ease(dusk) * dropBy, skyA * clamp((1 - dusk) * 3), pulse);
      drawOrb(PAL.night, mask, L.orbX, L.orbY + (1 - ease(dusk)) * dropBy, skyA * clamp(dusk * 3), pulse);

      /* mraky jdou za horou, ne přes ni */
      var orbNow = L.orbY + (dusk < .5 ? ease(dusk) : 1 - ease(dusk)) * dropBy;
      if (liveA > 0) {
        lives.clouds.forEach(function (cl) {
          var speed = cl.band ? 1 / 2.6 : 1 / 1.7;
          var off = moving ? t * speed : 0;
          var x = ((cl.c * L.cw - off * L.cw * .9) % (W + 240) + W + 240) % (W + 240) - 120;
          var c = Math.round(x / L.cw);
          if (cl.r < 0 || cl.r >= L.rows || c < 0 || c >= L.cols || mask[cl.r * L.cols + c]) return;
          if (opts.quietEl && cl.r * L.ch < H * .55 && x < W * .5 && W > 760) return;
          /* mrak nepřekrývá slunce ani měsíc */
          if (Math.hypot(x - L.orbX, L.baseY(cl.r) - orbNow) < L.orbR + 10) return;
          ctx.fillStyle = P.cloud[cl.tone];
          ctx.globalAlpha = liveA * .85;
          ctx.fillText(cl.ch, x, L.baseY(cl.r));
        });
      }

      /* namalovaná scéna: při přepnutí režimu se obě prolnou */
      var dW = canvas.width / dpr, dH = canvas.height / dpr;
      [['dawn', 1 - dusk], ['night', dusk]].forEach(function (pair) {
        if (pair[1] <= 0) return;
        var w = world[pair[0]], l = layers[pair[0]];
        bakeInto(l.base, w.cells, w.P.sketch, s, W, H);
        ctx.globalAlpha = pair[1];
        ctx.drawImage(l.base.c, 0, 0, dW, dH);
      });

      /* hladina se hýbe */
      if (liveA > 0 && moving) {
        lives.shimmer.forEach(function (layer, i) {
          var sway = Math.sin(t * (i ? .48 : .7)) * (i ? -11 : 9);
          var alpha = i ? .12 + .22 * (.5 + .5 * Math.sin(t * .48 + 2)) : .12 + .26 * (.5 + .5 * Math.sin(t * .7));
          ctx.globalAlpha = liveA * alpha;
          layer.forEach(function (m) {
            ctx.fillStyle = P.water[m.tone];
            ctx.fillText('~', m.c * L.cw + sway, L.baseY(m.r));
          });
        });
      }

      /* kruhy na vodě po kliknutí nebo pohybu myši */
      ripples = ripples.filter(function (rp) { return now - rp.at < 1700; });
      ripples.forEach(function (rp) {
        var age = (now - rp.at) / 1700;
        var rad = 12 + 110 * age;
        var n = Math.round(rad / 3.2);
        ctx.fillStyle = P.glitter[1];
        ctx.globalAlpha = .9 * (1 - age);
        for (var i = 0; i < n; i++) {
          var a = i / n * TAU;
          var x = rp.x + Math.cos(a) * rad, y = rp.y + Math.sin(a) * rad * .34;
          if (y < L.H * L.ch) continue;
          ctx.fillText(age < .4 ? 'o' : '~', Math.round(x / L.cw) * L.cw, Math.round(y / L.ch) * L.ch);
        }
      });

      /* větev se lehce houpe */
      var swing = moving ? Math.sin(t * .57) * .0096 * liveA : 0;
      [['dawn', 1 - dusk], ['night', dusk]].forEach(function (pair) {
        if (pair[1] <= 0) return;
        var w = world[pair[0]], l = layers[pair[0]];
        bakeInto(l.branch, w.branch, w.P.sketch, s, W, H);
        ctx.save();
        ctx.globalAlpha = pair[1];
        ctx.translate(W, 0);
        ctx.rotate(swing);
        ctx.translate(-W, 0);
        ctx.drawImage(l.branch.c, 0, 0, dW, dH);
        ctx.restore();
      });

      /* padající okvětní lístky */
      if (liveA > 0 && moving) {
        lives.petals.forEach(function (pt) {
          var p = (t / pt.dur + pt.ph) % 1;
          var x = pt.x - pt.drift * p + pt.sway * Math.sin(p * TAU * pt.waves);
          var y = pt.y + pt.drop * p + pt.sway * .25 * Math.sin(p * TAU * pt.waves * 2);
          ctx.save();
          ctx.globalAlpha = liveA * .85 * Math.min(1, p * 8, (1 - p) * 6);
          ctx.translate(x, y);
          ctx.rotate(pt.spin * p * Math.PI / 180);
          ctx.fillStyle = P.pink[pt.tone];
          ctx.fillText(pt.ch, -4, 4);
          ctx.restore();
        });
      }
      ctx.globalAlpha = 1;
    }

    function tick(now) {
      raf = 0;
      if (!L) return;
      var busy = false;
      if (tweenFor && stage !== target) {
        var p = clamp((now - tweenAt) / tweenFor);
        stage = from + (target - from) * (opts.intro ? p : ease(p));
        if (p >= 1) stage = target;
        busy = true;
      }
      if (dusk !== duskTo) {
        var dp = clamp((now - duskAt) / 1500);
        dusk = duskFrom + (duskTo - duskFrom) * dp;
        if (dp >= 1) dusk = duskTo;
        busy = true;
      }
      var alive = !calm && stage > 6;
      var hurry = busy || (ripples.length > 0);
      if (dirty || hurry || (alive && now - last > 32)) {
        last = now;
        dirty = false;
        render(now);
      }
      if (visible && (busy || alive || ripples.length)) schedule();
      else running = false;
    }
    function schedule() {
      running = true;
      if (!raf) raf = requestAnimationFrame(tick);
    }
    function poke() { dirty = true; if (visible) schedule(); }

    function setStage(v, ms) {
      target = clamp(v, 0, LAST);
      from = stage;
      if (calm || !ms) { stage = target; tweenFor = 0; }
      else { tweenAt = performance.now(); tweenFor = ms; }
      poke();
    }

    function setTheme(name) {
      var to = name === 'dark' ? 1 : 0;
      if (calm) { dusk = duskFrom = duskTo = to; poke(); return; }
      duskFrom = dusk; duskTo = to; duskAt = performance.now();
      poke();
    }

    rebuild();
    if (opts.intro && !calm) {
      opts.intro = true;
      setStage(LAST, opts.introFor || 2800);
    } else {
      opts.intro = false;
      poke();
    }

    document.addEventListener('voku:theme', function (e) { setTheme(e.detail); });

    /* písmo se načítá později: znaky se pak jen překreslí */
    if (document.fonts && document.fonts.load) {
      document.fonts.load('14px "Geist Mono"').then(function () {
        if (!L) return;
        ['dawn', 'night'].forEach(function (k) {
          ['base', 'branch'].forEach(function (n) {
            layers[k][n].x.font = font();
            layers[k][n].s = -1;
          });
        });
        ctx.font = font();
        poke();
      }).catch(function () {});
    }

    if ('IntersectionObserver' in window) {
      new IntersectionObserver(function (es) {
        visible = es[es.length - 1].isIntersecting;
        if (visible) poke();
      }).observe(canvas);
    }
    document.addEventListener('visibilitychange', function () {
      visible = !document.hidden;
      if (visible) poke();
    });

    var resizeTimer = 0, seen = canvas.getBoundingClientRect();
    new ResizeObserver(function () {
      var b = canvas.getBoundingClientRect();
      if (Math.abs(b.width - seen.width) < 2 && Math.abs(b.height - seen.height) < 2) return;
      seen = b;
      clearTimeout(resizeTimer);
      resizeTimer = setTimeout(function () { if (rebuild()) poke(); }, 120);
    }).observe(canvas);

    function ripple(e, force) {
      if (calm || !L || stage < 6) return;
      var b = canvas.getBoundingClientRect();
      var x = e.clientX - b.left, y = e.clientY - b.top;
      if (y < L.H * L.ch || y > b.height || x < 0 || x > b.width) return;
      if (!force && Math.hypot(x - lastRipple.x, y - lastRipple.y) < 70) return;
      lastRipple = { x: x, y: y };
      ripples.push({ x: x, y: y, at: performance.now() });
      poke();
    }
    host.addEventListener('pointerdown', function (e) { ripple(e, true); }, { passive: true });
    host.addEventListener('pointermove', function (e) { if (e.pointerType === 'mouse') ripple(e, false); }, { passive: true });

    return { setStage: setStage, get stage() { return stage; } };
  }

  window.VokuAscii = { mount: mount };
})();
