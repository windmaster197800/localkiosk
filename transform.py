#!/usr/bin/env python3
"""
Transform masterbook_local.html:
  - Remove duplicate thumbnail <img> tags from HTML (thumbnails were the same
    base64 data as IMAGES[], so the file stored every image twice)
  - Build thumbnails lazily from IMAGES[] in JS instead
  - Add pinch-to-zoom + pan for mobile
  - Add localStorage page persistence
  - Add keyboard zoom (+/-) for desktop
  - CSS touch-action / will-change improvements

Result: file drops from ~7.3 MB to ~4 MB, mobile load time halved.
"""

import sys

INPUT  = '/root/.claude/uploads/4fa9a701-5a8b-4cc8-910f-12cfdcc42081/c86fb309-masterbook_local.html'
OUTPUT = '/home/user/localkiosk/masterbook_local.html'

with open(INPUT, 'r', encoding='utf-8') as f:
    html = f.read()

# ── 1. Remove duplicate thumbnail <img> tags from #thumbBar ──────────────────
# The 16 <img class="thumb"> lines are identical base64 data to IMAGES[].
# We empty the thumbBar; JS will rebuild it lazily.
TB_OPEN  = '<div id="thumbBar">'
TB_CLOSE = '\n</div>'
tb_start = html.index(TB_OPEN)
tb_end   = html.index(TB_CLOSE, tb_start)
html = html[:tb_start + len(TB_OPEN)] + html[tb_end:]

# ── 2. CSS: add touch-action / will-change to #pageImg ───────────────────────
OLD_IMG_CSS = (
    '  #pageImg {\n'
    '    max-width: 100%;\n'
    '    max-height: 100%;\n'
    '    object-fit: contain;\n'
    '    display: block;\n'
    '    transition: opacity 0.15s;\n'
    '    cursor: zoom-in;\n'
    '    user-select: none;\n'
    '    -webkit-user-drag: none;\n'
    '  }'
)
NEW_IMG_CSS = (
    '  #pageImg {\n'
    '    max-width: 100%;\n'
    '    max-height: 100%;\n'
    '    object-fit: contain;\n'
    '    display: block;\n'
    '    transition: opacity 0.15s;\n'
    '    cursor: zoom-in;\n'
    '    user-select: none;\n'
    '    -webkit-user-drag: none;\n'
    '    touch-action: none;\n'
    '    will-change: transform;\n'
    '    transform-origin: center center;\n'
    '  }'
)
html = html.replace(OLD_IMG_CSS, NEW_IMG_CSS, 1)

# ── 3. Replace onclick="toggleZoom()" with data attribute (handler in JS) ────
html = html.replace(' onclick="toggleZoom()"', '', 1)

# ── 4. Replace JS section (everything from "let cur" to end of </script>) ────
JS_START_MARKER = '\nlet cur = 1;'
JS_END_MARKER   = '\ninitPage();\n</script>'

idx_js_start = html.index(JS_START_MARKER)
idx_js_end   = html.index(JS_END_MARKER) + len(JS_END_MARKER)

NEW_JS = r"""
let cur = 1;
let thumbsVisible = true;
let zoomed = false;

// Pinch-zoom & pan state
let scale = 1, baseScale = 1;
let panX = 0, panY = 0, basePanX = 0, basePanY = 0;
let initDist = 0, initMidX = 0, initMidY = 0;
let pinching = false;
let touchStartX = 0, touchStartY = 0;
let lastTapTime = 0;

// Build thumbnail strip from IMAGES[] (no duplicate base64 in HTML)
(function() {
  var bar = document.getElementById('thumbBar');
  for (var i = 1; i <= PAGES; i++) {
    var img = document.createElement('img');
    img.className = 'thumb';
    img.id = 't' + i;
    img.alt = 'Page ' + i;
    (function(n) { img.onclick = function() { goTo(n); }; })(i);
    bar.appendChild(img);
  }
})();

function loadThumb(n) {
  var t = document.getElementById('t' + n);
  if (t && !t.src) t.src = IMAGES[n];
}

function applyTransform() {
  document.getElementById('pageImg').style.transform =
    'translate(' + panX + 'px,' + panY + 'px) scale(' + scale + ')';
}

function resetZoom() {
  scale = 1; baseScale = 1;
  panX = 0; panY = 0; basePanX = 0; basePanY = 0;
  var img = document.getElementById('pageImg');
  img.style.transform = '';
  img.style.cursor = 'zoom-in';
  zoomed = false;
}

function goTo(n) {
  if (n < 1) n = 1;
  if (n > PAGES) n = PAGES;
  cur = n;
  resetZoom();
  var img = document.getElementById('pageImg');
  img.src = IMAGES[cur];
  img.className = 'fade-in';
  document.getElementById('pageInput').value = cur;
  document.getElementById('btnPrev').disabled = cur === 1;
  document.getElementById('btnFirst').disabled = cur === 1;
  document.getElementById('btnNext').disabled = cur === PAGES;
  document.getElementById('btnLast').disabled = cur === PAGES;
  // Lazy-load current + adjacent thumbnails immediately
  loadThumb(cur);
  if (cur > 1) loadThumb(cur - 1);
  if (cur < PAGES) loadThumb(cur + 1);
  // Update thumbnail highlight
  document.querySelectorAll('.thumb').forEach(function(t) { t.classList.remove('active'); });
  var active = document.getElementById('t' + cur);
  if (active) {
    active.classList.add('active');
    active.scrollIntoView({behavior: 'smooth', inline: 'center', block: 'nearest'});
  }
  // URL hash + localStorage
  history.replaceState(null, '', '#p=' + cur);
  try { localStorage.setItem('mb_page', String(cur)); } catch(e) {}
}

function nextPage() { goTo(cur + 1); }
function prevPage() { goTo(cur - 1); }

function toggleThumbs() {
  thumbsVisible = !thumbsVisible;
  document.getElementById('thumbBar').style.display = thumbsVisible ? 'flex' : 'none';
}

function toggleZoom() {
  if (!zoomed) {
    scale = 2; baseScale = 2; panX = 0; panY = 0;
    applyTransform();
    document.getElementById('pageImg').style.cursor = 'zoom-out';
    zoomed = true;
  } else {
    resetZoom();
  }
}

function toggleShortcuts() {
  document.getElementById('shortcuts').classList.toggle('visible');
}

// Click to toggle zoom (desktop)
document.getElementById('pageImg').addEventListener('click', toggleZoom);

// Keyboard navigation
document.addEventListener('keydown', function(e) {
  if (document.getElementById('shortcuts').classList.contains('visible')) {
    if (e.key === 'Escape') toggleShortcuts();
    return;
  }
  if (e.key === 'ArrowRight' || e.key === ' ') { e.preventDefault(); nextPage(); }
  else if (e.key === 'ArrowLeft') prevPage();
  else if (e.key === 'Home') goTo(1);
  else if (e.key === 'End') goTo(PAGES);
  else if (e.key === 't' || e.key === 'T') toggleThumbs();
  else if (e.key === 'f' || e.key === 'F') {
    if (!document.fullscreenElement) {
      document.documentElement.requestFullscreen && document.documentElement.requestFullscreen();
    } else {
      document.exitFullscreen && document.exitFullscreen();
    }
  }
  else if (e.key === 'Escape') { if (zoomed) resetZoom(); }
  else if (e.key === '+' || e.key === '=') {
    scale = Math.min(5, scale + 0.5); baseScale = scale;
    panX = 0; panY = 0; applyTransform(); zoomed = scale > 1;
    document.getElementById('pageImg').style.cursor = 'zoom-out';
  }
  else if (e.key === '-') {
    scale = Math.max(1, scale - 0.5); baseScale = scale;
    if (scale <= 1) { resetZoom(); }
    else { panX = 0; panY = 0; applyTransform(); }
  }
});

// ── Pinch-to-zoom + pan (mobile) ─────────────────────────────────────────────
function pinchDist(t) {
  return Math.hypot(t[0].clientX - t[1].clientX, t[0].clientY - t[1].clientY);
}

var viewer = document.getElementById('viewer');

viewer.addEventListener('touchstart', function(e) {
  if (e.touches.length === 2) {
    pinching = true;
    initDist = pinchDist(e.touches);
    initMidX = (e.touches[0].clientX + e.touches[1].clientX) / 2;
    initMidY = (e.touches[0].clientY + e.touches[1].clientY) / 2;
    baseScale = scale; basePanX = panX; basePanY = panY;
    e.preventDefault();
  } else if (e.touches.length === 1) {
    touchStartX = e.touches[0].clientX;
    touchStartY = e.touches[0].clientY;
    basePanX = panX; basePanY = panY;
    pinching = false;
  }
}, {passive: false});

viewer.addEventListener('touchmove', function(e) {
  if (e.touches.length === 2 && pinching) {
    var d = pinchDist(e.touches);
    var midX = (e.touches[0].clientX + e.touches[1].clientX) / 2;
    var midY = (e.touches[0].clientY + e.touches[1].clientY) / 2;
    scale = Math.max(1, Math.min(5, baseScale * d / initDist));
    panX = basePanX + midX - initMidX;
    panY = basePanY + midY - initMidY;
    applyTransform();
    e.preventDefault();
    zoomed = scale > 1.05;
  } else if (e.touches.length === 1 && scale > 1.05) {
    panX = basePanX + e.touches[0].clientX - touchStartX;
    panY = basePanY + e.touches[0].clientY - touchStartY;
    applyTransform();
    e.preventDefault();
  }
}, {passive: false});

viewer.addEventListener('touchend', function(e) {
  if (e.touches.length === 0) {
    basePanX = panX; basePanY = panY; baseScale = scale;
    if (scale < 1.05) resetZoom();

    // Swipe to navigate (only when not zoomed)
    if (!zoomed && !pinching) {
      var dx = e.changedTouches[0].clientX - touchStartX;
      var dy = e.changedTouches[0].clientY - touchStartY;
      if (Math.abs(dx) > Math.abs(dy) && Math.abs(dx) > 40) {
        pinching = false;
        if (dx < 0) nextPage(); else prevPage();
        return;
      }
    }
    pinching = false;

    // Double-tap to reset zoom
    var now = Date.now();
    if (now - lastTapTime < 300 && zoomed) { resetZoom(); }
    lastTapTime = now;

  } else if (e.touches.length === 1 && pinching) {
    // Finger lifted during pinch — continue as single-finger pan
    basePanX = panX; basePanY = panY; baseScale = scale;
    touchStartX = e.touches[0].clientX;
    touchStartY = e.touches[0].clientY;
    pinching = false;
  }
}, {passive: true});

// ── Initialise ────────────────────────────────────────────────────────────────
function initPage() {
  var match = window.location.hash.match(/#p=(\d+)/);
  var startPage = 1;
  if (match) {
    startPage = parseInt(match[1]);
  } else {
    try {
      var saved = localStorage.getItem('mb_page');
      if (saved) startPage = parseInt(saved);
    } catch(e) {}
  }
  goTo(startPage);

  // Progressively load remaining thumbnails in the background
  var i = 1;
  function loadNext() {
    if (i <= PAGES) { loadThumb(i++); requestAnimationFrame(loadNext); }
  }
  requestAnimationFrame(loadNext);

  // Fade hint after 3 s
  setTimeout(function() {
    var h = document.getElementById('hint');
    if (h) h.classList.add('fade');
  }, 3000);
}

initPage();
</script>
</body>
</html>"""

html = html[:idx_js_start] + NEW_JS

with open(OUTPUT, 'w', encoding='utf-8') as f:
    f.write(html)

size_mb = len(html.encode('utf-8')) / 1_048_576
print(f'Done. Output: {OUTPUT}  ({size_mb:.1f} MB)')
