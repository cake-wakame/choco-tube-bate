document.addEventListener('DOMContentLoaded', function() {
    const searchInput = document.querySelector('.search-input');
    if (searchInput) {
        searchInput.addEventListener('focus', function() {
            this.parentElement.style.borderColor = '#d2691e';
        });
        
        searchInput.addEventListener('blur', function() {
            this.parentElement.style.borderColor = '';
        });
    }

    const images = document.querySelectorAll('img[loading="lazy"]');
    images.forEach(img => {
        img.addEventListener('error', function() {
            this.src = 'data:image/svg+xml,<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 16 9"><rect fill="%231a1a2e"/><text x="8" y="5" text-anchor="middle" fill="%23888" font-size="2">読み込みエラー</text></svg>';
        });
    });
});
