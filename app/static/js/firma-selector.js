/**
 * Firma Selector Component
 * Admin "God Mode" functionality for switching between firms
 *
 * Dependencies: app.js (apiFetch, showErrorMessage)
 *
 * Usage: Include this script on pages where admin firm selector is present.
 *        Requires data attributes on elements for configuration.
 */

(function() {
    'use strict';

    const firmaSearchInput = document.getElementById('firmaSearchInput');
    const firmeList = document.getElementById('firmeList');
    const firmaDropdown = document.getElementById('firmaDropdown');

    // Get configuration from data attributes
    const baseUrl = document.body.dataset.baseUrl || '';
    const csrfTokenMeta = document.querySelector('meta[name="csrf-token"]');
    const csrfToken = csrfTokenMeta ? csrfTokenMeta.getAttribute('content') : '';

    // Get selected firma ID from dropdown container data attribute
    const dropdownContainer = document.getElementById('firmaDropdown');
    const selectedFirmaId = dropdownContainer ?
        parseInt(dropdownContainer.dataset.selectedFirmaId) || null :
        null;

    let searchTimeout = null;

    /**
     * Load firme from API with optional search query
     * @param {string} searchQuery - Search term to filter firme
     */
    function loadFirme(searchQuery = '') {
        const url = `${baseUrl}/api/admin/firme/search?q=${encodeURIComponent(searchQuery)}&limit=50`;

        // Show loading state
        firmeList.innerHTML = '<li><span class="dropdown-item text-muted py-3 text-center"><i class="fa-solid fa-spinner fa-spin me-2"></i> Učitavanje...</span></li>';

        apiFetch(url)
            .then(data => {
                renderFirme(data.firme);
            })
            .catch(error => {
                console.error('Error loading firme:', error);
                firmeList.innerHTML = '<li><span class="dropdown-item text-danger py-2"><i class="fa-solid fa-circle-exclamation me-2"></i> Greška pri učitavanju</span></li>';

                // Show user-friendly error message
                if (error.isNetworkError) {
                    showErrorMessage('Greška u komunikaciji sa serverom. Proverite internet konekciju.');
                } else {
                    showErrorMessage(error.message || 'Greška pri učitavanju liste firmi.');
                }
            });
    }

    /**
     * Render list of firme in dropdown
     * @param {Array} firme - Array of firma objects from API
     */
    function renderFirme(firme) {
        if (firme.length === 0) {
            firmeList.innerHTML = '<li><span class="dropdown-item text-muted">Nema rezultata</span></li>';
            return;
        }

        const html = firme.map(firma => {
            const isActive = selectedFirmaId === firma.id ? 'active fw-semibold' : '';
            return `
                <li>
                    <form method="POST" action="${baseUrl}/admin/switch-firma/${firma.id}" style="display: inline; width: 100%;">
                        <input type="hidden" name="csrf_token" value="${csrfToken}"/>
                        <button type="submit" class="dropdown-item py-2 ${isActive}">
                            <i class="fa-solid fa-building me-2 ${isActive ? '' : 'text-muted'}"></i>
                            <span class="fw-semibold">${firma.naziv}</span>
                            <br>
                            <small class="text-muted ms-4">PIB: ${firma.pib}</small>
                        </button>
                    </form>
                </li>
            `;
        }).join('');

        firmeList.innerHTML = html;
    }

    /**
     * Initialize firma selector
     */
    function init() {
        if (!firmaSearchInput || !firmeList || !firmaDropdown) {
            console.warn('Firma selector: Required elements not found');
            return;
        }

        // Search input handler (debounced)
        firmaSearchInput.addEventListener('input', function(e) {
            clearTimeout(searchTimeout);
            searchTimeout = setTimeout(() => {
                loadFirme(e.target.value);
            }, 300); // 300ms debounce
        });

        // Initial load when dropdown opens
        firmaDropdown.addEventListener('click', function() {
            // Only load if list is empty or showing loading text
            if (firmeList.innerHTML.includes('Učitavanje') || firmeList.children.length === 0) {
                loadFirme();
            }
        });
    }

    // Initialize on DOM ready
    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', init);
    } else {
        init();
    }

})();
