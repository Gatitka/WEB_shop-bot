// Диаграмма-донат для страницы бота (SVG, без сторонних библиотек)
document.addEventListener('DOMContentLoaded', function () {
    const g = document.getElementById('donut-data');
    if (!g) return;

    const can     = parseInt(g.dataset.can, 10);
    const cannot  = parseInt(g.dataset.cannot, 10);
    const never   = parseInt(g.dataset.never, 10);
    const unknown = parseInt(g.dataset.unknown, 10);
    const total   = parseInt(g.dataset.total, 10);

    const circ = 2 * Math.PI * 55;

    function seg(value) {
        return (value / total * circ).toFixed(2);
    }

    function pct(value) {
        return (value / total * 100).toFixed(1) + '%';
    }

    const unknownLen = parseFloat(seg(unknown));
    const neverLen   = parseFloat(seg(never));
    const cannotLen  = parseFloat(seg(cannot));
    const canLen     = parseFloat(seg(can));

    const segUnknown = document.getElementById('seg-unknown');
    const segNever   = document.getElementById('seg-never');
    const segCannot  = document.getElementById('seg-cannot');
    const segCan     = document.getElementById('seg-can');

    // Старт с верхней точки (-90°)
    const start = -circ / 4;

    function applySegment(el, len, offset) {
        el.setAttribute('stroke-dasharray', `${len.toFixed(2)} ${(circ - len).toFixed(2)}`);
        el.setAttribute('stroke-dashoffset', offset.toFixed(2));
    }

    // Порядок отрисовки: unknown → never → cannot → can
    applySegment(segUnknown, unknownLen, start);
    applySegment(segNever,   neverLen,   start - unknownLen);
    applySegment(segCannot,  cannotLen,  start - unknownLen - neverLen);
    applySegment(segCan,     canLen,     start - unknownLen - neverLen - cannotLen);

    // Проценты в легенде
    document.getElementById('pct-can').textContent     = pct(can);
    document.getElementById('pct-cannot').textContent  = pct(cannot);
    document.getElementById('pct-never').textContent   = pct(never);
    document.getElementById('pct-unknown').textContent = pct(unknown);
});
