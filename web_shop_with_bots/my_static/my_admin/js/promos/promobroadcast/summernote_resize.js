document.addEventListener("DOMContentLoaded", function () {
    function waitForIframe() {
        var iframe = document.querySelector('iframe#id_body_iframe');
        if (!iframe) {
            setTimeout(waitForIframe, 100);
            return;
        }

        iframe.addEventListener('load', function () {
            setTimeout(function () {
                requestAnimationFrame(function() {
                    requestAnimationFrame(function() {
                        var iDoc = iframe.contentDocument || iframe.contentWindow.document;
                        var editable = iDoc.querySelector('.note-editable');
                        if (!editable) return;

                        // Telegram-like стили
                        var style = iDoc.createElement('style');
                        style.textContent = `
    * { box-sizing: border-box; }
    body {
        font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
        font-size: 14px;
        line-height: 1.4;
        margin: 8px 12px;
        overflow-x: hidden;
    }
    p {
        margin: 0 0 4px 0;
    }
    .note-editable {
        height: auto !important;
        min-height: 0 !important;
        overflow: visible !important;
    }
`;
                        iDoc.head.appendChild(style);

                        editable.style.setProperty('height', 'auto', 'important');
                        editable.style.setProperty('min-height', '0', 'important');
                        editable.style.setProperty('overflow', 'visible', 'important');

                        function applyHeight() {
                            var contentHeight = editable.scrollHeight;
                            iframe.style.setProperty('height', (contentHeight + 60) + 'px', 'important');
                            iframe.style.setProperty('resize', 'vertical', 'important');
                            iframe.style.setProperty('overflow', 'auto', 'important');
                            iframe.contentWindow.scrollTo(0, 0);
                        }

                        // Вызываем после применения стилей
                        requestAnimationFrame(function() {
                            applyHeight();
                        });

                        editable.addEventListener('input', applyHeight);
                        editable.addEventListener('keyup', applyHeight);

                        var observer = new MutationObserver(applyHeight);
                        observer.observe(editable, { childList: true, subtree: true, characterData: true });
                    });
                });
            }, 2000);
        });
    }

    waitForIframe();
});
