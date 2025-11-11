/**
 * Komitent Form
 * Handles dynamic bank accounts (dinarski/devizni računi) and NBS company lookup
 *
 * Dependencies: app.js (apiFetch)
 *
 * Usage: Include this script on komitenti/novi.html and komitenti/edit.html templates.
 *        Requires specific form elements with IDs (see init function).
 */

(function() {
    'use strict';

    // State management
    let dinarskiRacuni = [];
    let devizniRacuni = [];

    // DOM elements
    let dinarskiContainer = null;
    let devizniContainer = null;
    let nbsLookupUrl = '';

    /**
     * Render Dinarski Računi list
     */
    function renderDinarskiRacuni() {
        if (!dinarskiContainer) return;

        dinarskiContainer.innerHTML = '';
        dinarskiRacuni.forEach((racun, index) => {
            const div = document.createElement('div');
            div.className = 'card mb-2';
            div.innerHTML = `
                <div class="card-body">
                    <div class="row">
                        <div class="col-md-5">
                            <input type="text"
                                   class="form-control"
                                   placeholder="Naziv banke"
                                   value="${racun.banka}"
                                   onchange="updateDinarskiRacun(${index}, 'banka', this.value)">
                        </div>
                        <div class="col-md-5">
                            <input type="text"
                                   class="form-control"
                                   placeholder="Broj računa (###-###########-##)"
                                   value="${racun.racun}"
                                   onchange="updateDinarskiRacun(${index}, 'racun', this.value)">
                        </div>
                        <div class="col-md-2">
                            <button type="button"
                                    class="btn btn-danger w-100"
                                    onclick="removeDinarskiRacun(${index})"
                                    aria-label="Ukloni dinarski račun">
                                <i class="fa-solid fa-trash"></i>
                            </button>
                        </div>
                    </div>
                </div>
            `;
            dinarskiContainer.appendChild(div);
        });

        // Update hidden JSON field
        const jsonField = document.getElementById('dinarski_racuni_json');
        if (jsonField) {
            jsonField.value = JSON.stringify(dinarskiRacuni);
        }
    }

    /**
     * Add new Dinarski Račun
     */
    function addDinarskiRacun() {
        dinarskiRacuni.push({ banka: '', racun: '' });
        renderDinarskiRacuni();
    }

    /**
     * Remove Dinarski Račun by index
     * @param {number} index - Index of račun to remove
     */
    function removeDinarskiRacun(index) {
        dinarskiRacuni.splice(index, 1);
        renderDinarskiRacuni();
    }

    /**
     * Update Dinarski Račun field
     * @param {number} index - Index of račun to update
     * @param {string} field - Field name ('banka' or 'racun')
     * @param {string} value - New value
     */
    function updateDinarskiRacun(index, field, value) {
        if (dinarskiRacuni[index]) {
            dinarskiRacuni[index][field] = value;
            const jsonField = document.getElementById('dinarski_racuni_json');
            if (jsonField) {
                jsonField.value = JSON.stringify(dinarskiRacuni);
            }
        }
    }

    /**
     * Render Devizni Računi list
     */
    function renderDevizniRacuni() {
        if (!devizniContainer) return;

        devizniContainer.innerHTML = '';
        devizniRacuni.forEach((racun, index) => {
            const div = document.createElement('div');
            div.className = 'card mb-2';
            div.innerHTML = `
                <div class="card-body">
                    <div class="row">
                        <div class="col-md-3">
                            <input type="text"
                                   class="form-control"
                                   placeholder="Naziv banke"
                                   value="${racun.banka}"
                                   onchange="updateDevizniRacun(${index}, 'banka', this.value)">
                        </div>
                        <div class="col-md-3">
                            <input type="text"
                                   class="form-control"
                                   placeholder="IBAN"
                                   value="${racun.iban}"
                                   onchange="updateDevizniRacun(${index}, 'iban', this.value)">
                        </div>
                        <div class="col-md-2">
                            <input type="text"
                                   class="form-control"
                                   placeholder="SWIFT"
                                   value="${racun.swift}"
                                   onchange="updateDevizniRacun(${index}, 'swift', this.value)">
                        </div>
                        <div class="col-md-2">
                            <select class="form-select"
                                    onchange="updateDevizniRacun(${index}, 'valuta', this.value)">
                                <option value="EUR" ${racun.valuta === 'EUR' ? 'selected' : ''}>EUR</option>
                                <option value="USD" ${racun.valuta === 'USD' ? 'selected' : ''}>USD</option>
                                <option value="GBP" ${racun.valuta === 'GBP' ? 'selected' : ''}>GBP</option>
                                <option value="CHF" ${racun.valuta === 'CHF' ? 'selected' : ''}>CHF</option>
                            </select>
                        </div>
                        <div class="col-md-2">
                            <button type="button"
                                    class="btn btn-danger w-100"
                                    onclick="removeDevizniRacun(${index})"
                                    aria-label="Ukloni devizni račun">
                                <i class="fa-solid fa-trash"></i>
                            </button>
                        </div>
                    </div>
                </div>
            `;
            devizniContainer.appendChild(div);
        });

        // Update hidden JSON field
        const jsonField = document.getElementById('devizni_racuni_json');
        if (jsonField) {
            jsonField.value = JSON.stringify(devizniRacuni);
        }
    }

    /**
     * Add new Devizni Račun
     */
    function addDevizniRacun() {
        devizniRacuni.push({ banka: '', iban: '', swift: '', valuta: 'EUR' });
        renderDevizniRacuni();
    }

    /**
     * Remove Devizni Račun by index
     * @param {number} index - Index of račun to remove
     */
    function removeDevizniRacun(index) {
        devizniRacuni.splice(index, 1);
        renderDevizniRacuni();
    }

    /**
     * Update Devizni Račun field
     * @param {number} index - Index of račun to update
     * @param {string} field - Field name ('banka', 'iban', 'swift', or 'valuta')
     * @param {string} value - New value
     */
    function updateDevizniRacun(index, field, value) {
        if (devizniRacuni[index]) {
            devizniRacuni[index][field] = value;
            const jsonField = document.getElementById('devizni_racuni_json');
            if (jsonField) {
                jsonField.value = JSON.stringify(devizniRacuni);
            }
        }
    }

    /**
     * Setup NBS company lookup
     */
    function setupNbsLookup() {
        const nbsSearchBtn = document.getElementById('nbsSearchBtn');
        const pibInput = document.getElementById('pib');
        const alertDiv = document.getElementById('nbsAlert');

        if (!nbsSearchBtn || !pibInput || !alertDiv) return;

        nbsSearchBtn.addEventListener('click', function() {
            const pib = pibInput.value.trim();

            if (!pib || (pib.length !== 8 && pib.length !== 9)) {
                alertDiv.className = 'alert alert-warning';
                alertDiv.textContent = 'Molimo unesite validan PIB (8 ili 9 cifara).';
                alertDiv.style.display = 'block';
                return;
            }

            // Show loading state
            this.disabled = true;
            this.innerHTML = '<i class="fa-solid fa-spinner fa-spin"></i> Pretražujem...';

            // Construct URL (replace PLACEHOLDER with actual PIB)
            const url = nbsLookupUrl + pib;

            apiFetch(url)
                .then(data => {
                    if (data.success && data.data) {
                        // Auto-fill form fields
                        const fields = {
                            'naziv': data.data.naziv || '',
                            'maticni_broj': data.data.maticni_broj || '',
                            'adresa': data.data.adresa || '',
                            'broj': data.data.broj || 'bb',
                            'mesto': data.data.mesto || ''
                        };

                        Object.keys(fields).forEach(fieldId => {
                            const field = document.getElementById(fieldId);
                            if (field) {
                                field.value = fields[fieldId];
                            }
                        });

                        // Set postanski_broj if available
                        if (data.data.postanski_broj) {
                            const postanskiBrojField = document.getElementById('postanski_broj');
                            if (postanskiBrojField) {
                                postanskiBrojField.value = data.data.postanski_broj;
                            }
                        }

                        // Make fields readonly (can be overridden via double-click)
                        ['naziv', 'maticni_broj', 'adresa', 'broj', 'mesto'].forEach(id => {
                            const field = document.getElementById(id);
                            if (field) {
                                field.setAttribute('readonly', true);
                                field.classList.add('bg-light');
                            }
                        });

                        alertDiv.className = 'alert alert-success';
                        alertDiv.innerHTML = '<i class="fa-solid fa-check-circle"></i> Podaci uspešno preuzeti iz NBS baze! Dvoklik na polje za ručno menjanje.';
                        alertDiv.style.display = 'block';
                    } else {
                        alertDiv.className = 'alert alert-warning';
                        alertDiv.innerHTML = '<i class="fa-solid fa-triangle-exclamation"></i> ' + (data.message || 'Komitent nije pronađen u NBS bazi. Molimo unesite podatke ručno.');
                        alertDiv.style.display = 'block';
                    }
                })
                .catch(error => {
                    console.error('NBS API error:', error);
                    alertDiv.className = 'alert alert-danger';

                    // User-friendly error message based on error type
                    if (error.isNetworkError) {
                        alertDiv.innerHTML = '<i class="fa-solid fa-circle-exclamation"></i> Greška u komunikaciji sa serverom. Proverite internet konekciju i pokušajte ponovo.';
                    } else {
                        alertDiv.innerHTML = '<i class="fa-solid fa-circle-exclamation"></i> Greška pri pretrazi NBS baze. ' + (error.message || 'Molimo unesite podatke ručno.');
                    }
                    alertDiv.style.display = 'block';
                })
                .finally(() => {
                    this.disabled = false;
                    this.innerHTML = '<i class="fa-solid fa-magnifying-glass"></i> Pretraži NBS';
                });
        });
    }

    /**
     * Setup manual override for readonly fields
     * Double-click on readonly field to enable editing
     */
    function setupManualOverride() {
        const fields = ['naziv', 'maticni_broj', 'adresa', 'broj', 'mesto'];

        fields.forEach(id => {
            const field = document.getElementById(id);
            if (field) {
                field.addEventListener('dblclick', function() {
                    this.removeAttribute('readonly');
                    this.classList.remove('bg-light');
                    this.focus();
                });
            }
        });
    }

    /**
     * Initialize komitent form
     */
    function init() {
        // Get DOM elements
        dinarskiContainer = document.getElementById('dinarskiRacuniContainer');
        devizniContainer = document.getElementById('devizniRacuniContainer');

        // Get NBS lookup URL from data attribute
        const komitentFormContainer = document.getElementById('komitentFormContainer');
        if (komitentFormContainer) {
            nbsLookupUrl = komitentFormContainer.dataset.nbsLookupUrl || '';
        }

        // Setup dynamic računi
        if (dinarskiContainer) {
            const addDinarskiBtn = document.getElementById('addDinarskiRacun');
            if (addDinarskiBtn) {
                addDinarskiBtn.addEventListener('click', addDinarskiRacun);
            }
        }

        if (devizniContainer) {
            const addDevizniBtn = document.getElementById('addDevizniRacun');
            if (addDevizniBtn) {
                addDevizniBtn.addEventListener('click', addDevizniRacun);
            }
        }

        // Setup NBS lookup
        setupNbsLookup();

        // Setup manual override
        setupManualOverride();

        // Expose functions globally for onclick handlers (legacy support)
        window.addDinarskiRacun = addDinarskiRacun;
        window.removeDinarskiRacun = removeDinarskiRacun;
        window.updateDinarskiRacun = updateDinarskiRacun;
        window.addDevizniRacun = addDevizniRacun;
        window.removeDevizniRacun = removeDevizniRacun;
        window.updateDevizniRacun = updateDevizniRacun;
    }

    // Initialize on DOM ready
    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', init);
    } else {
        init();
    }

})();
