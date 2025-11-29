document.addEventListener('DOMContentLoaded', function() {
    const themeToggle = document.getElementById('themeToggle');
    const html = document.documentElement;
    
    function getCookie(name) {
        const v = document.cookie.match('(^|;)\\s*' + name + '\\s*=\\s*([^;]+)');
        return v ? decodeURIComponent(v.pop()) : null;
    }
    
    function setCookie(name, value, days) {
        const d = new Date();
        d.setTime(d.getTime() + (days || 30) * 24 * 60 * 60 * 1000);
        document.cookie = name + '=' + encodeURIComponent(value) + ';expires=' + d.toUTCString() + ';path=/';
    }
    
    const savedTheme = getCookie('theme') || 'dark';
    html.setAttribute('data-theme', savedTheme);
    
    if (themeToggle) {
        themeToggle.addEventListener('click', function() {
            const currentTheme = html.getAttribute('data-theme');
            const newTheme = currentTheme === 'dark' ? 'light' : 'dark';
            html.setAttribute('data-theme', newTheme);
            setCookie('theme', newTheme, 365);
        });
    }
    
    const searchbox = document.getElementById('searchbox');
    if (searchbox) {
        let suggestionTimeout;
        let suggestionsContainer;
        
        function createSuggestionsContainer() {
            if (!suggestionsContainer) {
                suggestionsContainer = document.createElement('div');
                suggestionsContainer.className = 'suggestions-container';
                suggestionsContainer.style.cssText = `
                    position: absolute;
                    top: 100%;
                    left: 0;
                    right: 0;
                    background: var(--bg-card);
                    border: 1px solid var(--border-color);
                    border-radius: 0 0 12px 12px;
                    max-height: 300px;
                    overflow-y: auto;
                    z-index: 1001;
                    display: none;
                `;
                searchbox.parentElement.style.position = 'relative';
                searchbox.parentElement.appendChild(suggestionsContainer);
            }
            return suggestionsContainer;
        }
        
        function showSuggestions(suggestions) {
            const container = createSuggestionsContainer();
            if (suggestions.length === 0) {
                container.style.display = 'none';
                return;
            }
            
            container.innerHTML = suggestions.map(function(s) {
                return '<div class="suggestion-item" style="padding: 12px 16px; cursor: pointer; transition: background 0.2s;">' + escapeHtml(s) + '</div>';
            }).join('');
            
            container.style.display = 'block';
            
            container.querySelectorAll('.suggestion-item').forEach(function(item) {
                item.addEventListener('click', function() {
                    searchbox.value = this.textContent;
                    container.style.display = 'none';
                    searchbox.form.submit();
                });
                
                item.addEventListener('mouseenter', function() {
                    this.style.background = 'rgba(255, 255, 255, 0.1)';
                });
                
                item.addEventListener('mouseleave', function() {
                    this.style.background = 'transparent';
                });
            });
        }
        
        function escapeHtml(text) {
            const div = document.createElement('div');
            div.textContent = text;
            return div.innerHTML;
        }
        
        searchbox.addEventListener('input', function() {
            clearTimeout(suggestionTimeout);
            const query = this.value.trim();
            
            if (query.length < 2) {
                if (suggestionsContainer) {
                    suggestionsContainer.style.display = 'none';
                }
                return;
            }
            
            suggestionTimeout = setTimeout(function() {
                fetch('/suggest?keyword=' + encodeURIComponent(query))
                    .then(function(res) { return res.json(); })
                    .then(showSuggestions)
                    .catch(function() {
                        if (suggestionsContainer) {
                            suggestionsContainer.style.display = 'none';
                        }
                    });
            }, 300);
        });
        
        document.addEventListener('click', function(e) {
            if (suggestionsContainer && !searchbox.contains(e.target) && !suggestionsContainer.contains(e.target)) {
                suggestionsContainer.style.display = 'none';
            }
        });
    }
});
