/**
 * Faktura Form JavaScript
 * Handles autocomplete, dynamic stavke, and auto-calculations
 */

// Global state
let stavkaCounter = 0;
let selectedKomitent = null;

// Initialize on page load
document.addEventListener('DOMContentLoaded', function() {
    initializeDatumPrometa();
    initializeKomitentAutocomplete();
    initializeDatumCalculation();
    initializeFormSubmit();
    initializeDeviznaFaktura(); // NEW: Initialize foreign currency functionality
    initializeLimitWidget(); // Story 5.4: Initialize limit tracking widget

    // Check if we have initial stavke (for edit mode)
    if (typeof window.INITIAL_STAVKE !== 'undefined' && window.INITIAL_STAVKE.length > 0) {
        // Prepopulate stavke from existing faktura (edit mode)
        window.INITIAL_STAVKE.forEach(stavkaData => {
            addStavka(stavkaData);
        });
    } else {
        // Add first empty stavka by default (new faktura mode)
        addStavka();
    }

    // Add stavka button handler
    document.getElementById('addStavkaBtn').addEventListener('click', () => addStavka());
});

/**
 * Set default datum prometa to today
 */
function initializeDatumPrometa() {
    const datumPrometaInput = document.getElementById('datum_prometa');
    if (datumPrometaInput && !datumPrometaInput.value) {
        const today = new Date().toISOString().split('T')[0];
        datumPrometaInput.value = today;
        calculateDatumDospeca(); // Trigger initial calculation
    }
}

/**
 * Initialize komitent autocomplete
 */
function initializeKomitentAutocomplete() {
    const searchInput = document.getElementById('komitent_search');
    const resultsDiv = document.getElementById('komitent_results');
    const hiddenInput = document.getElementById('komitent_id');
    const selectedDiv = document.getElementById('selected_komitent');

    let searchTimeout;

    searchInput.addEventListener('input', function() {
        const query = this.value.trim();

        // Clear previous timeout
        if (searchTimeout) {
            clearTimeout(searchTimeout);
        }

        // Hide results if query is too short
        if (query.length < 2) {
            resultsDiv.style.display = 'none';
            return;
        }

        // Debounce search
        searchTimeout = setTimeout(() => {
            apiFetch(`${window.API_URLS.komitentiSearch}?q=${encodeURIComponent(query)}`)
                .then(data => {
                    renderKomitentResults(data);
                })
                .catch(error => {
                    console.error('Komitent search error:', error);
                    resultsDiv.innerHTML = '<div class="list-group-item text-danger"><i class="fa-solid fa-circle-exclamation me-2"></i>Greška pri pretrazi komitenata</div>';
                    resultsDiv.style.display = 'block';

                    // Show user-friendly error message
                    if (error.isNetworkError) {
                        showErrorMessage('Greška u komunikaciji sa serverom. Proverite internet konekciju.');
                    } else {
                        showErrorMessage(error.message || 'Greška pri pretrazi komitenata.');
                    }
                });
        }, 300);
    });

    // Hide results when clicking outside
    document.addEventListener('click', function(e) {
        if (!searchInput.contains(e.target) && !resultsDiv.contains(e.target)) {
            resultsDiv.style.display = 'none';
        }
    });
}

/**
 * Render komitent search results
 */
function renderKomitentResults(komitenti) {
    const resultsDiv = document.getElementById('komitent_results');

    if (komitenti.length === 0) {
        resultsDiv.innerHTML = '<div class="list-group-item text-muted">Nema rezultata</div>';
        resultsDiv.style.display = 'block';
        return;
    }

    resultsDiv.innerHTML = '';

    komitenti.forEach(k => {
        const item = document.createElement('a');
        item.href = '#';
        item.className = 'list-group-item list-group-item-action';
        item.innerHTML = `
            <strong>${k.naziv}</strong><br>
            <small class="text-muted">PIB: ${k.pib} | ${k.adresa}</small>
        `;

        item.addEventListener('click', function(e) {
            e.preventDefault();
            selectKomitent(k);
        });

        resultsDiv.appendChild(item);
    });

    resultsDiv.style.display = 'block';
}

/**
 * Select a komitent
 */
function selectKomitent(komitent) {
    // Validate komitent for devizna fakture (IBAN/SWIFT check)
    if (!validateKomitentForDevizna(komitent)) {
        return; // Don't select if validation fails
    }

    selectedKomitent = komitent;

    // Set hidden input
    document.getElementById('komitent_id').value = komitent.id;

    // Clear search input
    document.getElementById('komitent_search').value = '';

    // Hide results
    document.getElementById('komitent_results').style.display = 'none';

    // Show selected komitent
    const selectedDiv = document.getElementById('selected_komitent');
    document.getElementById('selected_komitent_naziv').textContent = komitent.naziv;
    document.getElementById('selected_komitent_info').textContent = `PIB: ${komitent.pib} | ${komitent.adresa}`;
    selectedDiv.style.display = 'block';
}

/**
 * Initialize datum dospeća calculation
 */
function initializeDatumCalculation() {
    document.getElementById('datum_prometa').addEventListener('change', calculateDatumDospeca);
    document.getElementById('valuta_placanja').addEventListener('input', calculateDatumDospeca);
}

/**
 * Calculate datum dospeća with weekend adjustment
 */
function calculateDatumDospeca() {
    const datumPrometa = document.getElementById('datum_prometa').value;
    const valutaPlacanja = parseInt(document.getElementById('valuta_placanja').value || 0);

    if (!datumPrometa || valutaPlacanja < 1) {
        return;
    }

    // Parse datum prometa
    const prometa = new Date(datumPrometa + 'T00:00:00');

    // Add valuta placanja days
    prometa.setDate(prometa.getDate() + valutaPlacanja);

    // Weekend adjustment: Saturday (6) -> Monday, Sunday (0) -> Monday
    const dayOfWeek = prometa.getDay();
    if (dayOfWeek === 6) { // Saturday
        prometa.setDate(prometa.getDate() + 2);
    } else if (dayOfWeek === 0) { // Sunday
        prometa.setDate(prometa.getDate() + 1);
    }

    // Set datum dospeca
    const datumDospeca = prometa.toISOString().split('T')[0];
    document.getElementById('datum_dospeca').value = datumDospeca;
}

/**
 * Add a new stavka row
 * @param {Object} initialData - Optional initial data for prepopulating stavka (edit mode)
 * @param {number} initialData.artikal_id - Artikal ID
 * @param {string} initialData.naziv - Naziv usluge/artikla
 * @param {number} initialData.kolicina - Količina
 * @param {string} initialData.jedinica_mere - Jedinica mere
 * @param {number} initialData.cena - Cena
 */
function addStavka(initialData = null) {
    stavkaCounter++;

    // Clone template
    const template = document.getElementById('stavka_template');
    const clone = template.content.cloneNode(true);

    // Set redni broj
    clone.querySelector('.redni-broj').value = stavkaCounter;

    // Add to container
    const container = document.getElementById('stavke_container');
    container.appendChild(clone);

    // Get the newly added stavka row
    const stavkaRows = container.querySelectorAll('.stavka-row');
    const newRow = stavkaRows[stavkaRows.length - 1];

    // Prepopulate with initial data if provided (edit mode)
    if (initialData) {
        if (initialData.artikal_id) {
            newRow.querySelector('.artikal-id').value = initialData.artikal_id;
        }
        newRow.querySelector('.artikal-search').value = initialData.naziv;
        newRow.querySelector('.stavka-naziv').value = initialData.naziv;
        newRow.querySelector('.stavka-kolicina').value = initialData.kolicina;
        newRow.querySelector('.stavka-jedinica').value = initialData.jedinica_mere;
        newRow.querySelector('.stavka-cena').value = initialData.cena;
    }

    // Initialize artikal autocomplete for this row
    initializeArtikalAutocomplete(newRow);

    // Initialize auto-calculation for this row
    initializeStavkaCalculation(newRow);

    // Initialize remove button
    const removeBtn = newRow.querySelector('.remove-stavka');
    removeBtn.addEventListener('click', function() {
        removeStavka(newRow);
    });

    // Update currency label for the new stavka
    updateStavkaCurrencyLabels();

    // Trigger calculation if initial data provided (to update totals)
    if (initialData) {
        const kolicina = newRow.querySelector('.stavka-kolicina');
        kolicina.dispatchEvent(new Event('input'));
    }
}

/**
 * Remove stavka row
 */
function removeStavka(stavkaRow) {
    const container = document.getElementById('stavke_container');

    // Don't allow removing the last stavka
    if (container.querySelectorAll('.stavka-row').length <= 1) {
        alert('Mora postojati bar jedna stavka!');
        return;
    }

    stavkaRow.remove();
    renumberStavke();
    calculateUkupanIznos();
}

/**
 * Renumber stavke after deletion
 */
function renumberStavke() {
    const stavke = document.querySelectorAll('.stavka-row');
    stavke.forEach((stavka, index) => {
        stavka.querySelector('.redni-broj').value = index + 1;
    });
    stavkaCounter = stavke.length;
}

/**
 * Initialize artikal autocomplete for a stavka row
 */
function initializeArtikalAutocomplete(stavkaRow) {
    const searchInput = stavkaRow.querySelector('.artikal-search');
    const resultsDiv = stavkaRow.querySelector('.artikal-results');
    const artikalIdInput = stavkaRow.querySelector('.artikal-id');
    const nazivInput = stavkaRow.querySelector('.stavka-naziv');
    const kolicinaInput = stavkaRow.querySelector('.stavka-kolicina');
    const jedinicaInput = stavkaRow.querySelector('.stavka-jedinica');
    const cenaInput = stavkaRow.querySelector('.stavka-cena');

    let searchTimeout;

    searchInput.addEventListener('input', function() {
        const query = this.value.trim();

        // Update hidden naziv field for manual entry
        nazivInput.value = query;

        // Clear previous timeout
        if (searchTimeout) {
            clearTimeout(searchTimeout);
        }

        // Hide results if query is too short
        if (query.length < 2) {
            resultsDiv.style.display = 'none';
            return;
        }

        // Debounce search
        searchTimeout = setTimeout(() => {
            apiFetch(`${window.API_URLS.artikliSearch}?q=${encodeURIComponent(query)}`)
                .then(data => {
                    renderArtikalResults(data, resultsDiv, searchInput, artikalIdInput, nazivInput, kolicinaInput, jedinicaInput, cenaInput);
                })
                .catch(error => {
                    console.error('Artikal search error:', error);

                    // Show user-friendly error message
                    if (error.isNetworkError) {
                        showErrorMessage('Greška u komunikaciji sa serverom. Proverite internet konekciju.');
                    } else {
                        showErrorMessage(error.message || 'Greška pri pretrazi artikala.');
                    }
                });
        }, 300);
    });

    // Hide results when clicking outside
    document.addEventListener('click', function(e) {
        if (!searchInput.contains(e.target) && !resultsDiv.contains(e.target)) {
            resultsDiv.style.display = 'none';
        }
    });
}

/**
 * Render artikal search results
 */
function renderArtikalResults(artikli, resultsDiv, searchInput, artikalIdInput, nazivInput, kolicinaInput, jedinicaInput, cenaInput) {
    if (artikli.length === 0) {
        resultsDiv.style.display = 'none';
        return;
    }

    resultsDiv.innerHTML = '';

    artikli.forEach(a => {
        const item = document.createElement('a');
        item.href = '#';
        item.className = 'list-group-item list-group-item-action list-group-item-sm';
        item.innerHTML = `
            <strong>${a.naziv}</strong><br>
            <small class="text-muted">${a.podrazumevana_cena} RSD / ${a.jedinica_mere}</small>
        `;

        item.addEventListener('click', function(e) {
            e.preventDefault();

            // Set values
            searchInput.value = a.naziv;
            artikalIdInput.value = a.id;
            nazivInput.value = a.naziv;
            jedinicaInput.value = a.jedinica_mere;

            // Auto-convert cena for devizna fakture (RSD → foreign currency)
            const tipFakture = document.querySelector('input[name="tip_fakture"]:checked');
            const srednjiKursInput = document.getElementById('srednji_kurs');

            if (tipFakture && tipFakture.value === 'devizna' && srednjiKursInput) {
                const kurs = parseFloat(srednjiKursInput.value);
                if (kurs > 0) {
                    // Convert RSD → EUR (or other currency)
                    const cenaRSD = parseFloat(a.podrazumevana_cena);
                    const cenaForeign = cenaRSD / kurs;
                    cenaInput.value = cenaForeign.toFixed(2);
                } else {
                    // No kurs yet - use RSD value (will need manual adjustment)
                    cenaInput.value = a.podrazumevana_cena;
                }
            } else {
                // Domestic invoice - use RSD directly
                cenaInput.value = a.podrazumevana_cena;
            }

            // Set default quantity if empty
            if (!kolicinaInput.value) {
                kolicinaInput.value = '1.00';
            }

            // Hide results
            resultsDiv.style.display = 'none';

            // Trigger calculation
            calculateStavkaUkupno(searchInput.closest('.stavka-row'));
        });

        resultsDiv.appendChild(item);
    });

    resultsDiv.style.display = 'block';
}

/**
 * Initialize stavka calculation (kolicina * cena = ukupno)
 */
function initializeStavkaCalculation(stavkaRow) {
    const kolicinaInput = stavkaRow.querySelector('.stavka-kolicina');
    const cenaInput = stavkaRow.querySelector('.stavka-cena');

    kolicinaInput.addEventListener('input', () => calculateStavkaUkupno(stavkaRow));
    cenaInput.addEventListener('input', () => calculateStavkaUkupno(stavkaRow));
}

/**
 * Calculate stavka ukupno (in foreign currency for devizna, RSD for standard)
 *
 * OPCIJA A LOGIC:
 * - For devizna fakture: cena is in EUR → ukupno = kolicina * cena (EUR), then RSD = EUR * kurs
 * - For standard fakture: cena is in RSD → ukupno = kolicina * cena (RSD)
 * - Display for devizna: "Ukupno: 102.35 EUR (12,000 RSD)"
 */
function calculateStavkaUkupno(stavkaRow) {
    const kolicina = parseFloat(stavkaRow.querySelector('.stavka-kolicina').value) || 0;
    const cena = parseFloat(stavkaRow.querySelector('.stavka-cena').value) || 0;

    const tipFakture = document.querySelector('input[name="tip_fakture"]:checked').value;

    if (tipFakture === 'devizna') {
        // DEVIZNA: cena is in foreign currency (EUR/USD/etc)
        const valuta = document.getElementById('valuta_fakture').value || 'EUR';
        const srednjiKurs = parseFloat(document.getElementById('srednji_kurs').value || 0);

        const ukupnoForeign = kolicina * cena;  // Primary amount in EUR

        // Show foreign amount as primary
        stavkaRow.querySelector('.stavka-ukupno').textContent = ukupnoForeign.toFixed(2);
        stavkaRow.querySelector('.stavka-ukupno-currency').textContent = valuta;  // Show EUR as primary

        const foreignContainer = stavkaRow.querySelector('.stavka-ukupno-foreign');
        const foreignValue = stavkaRow.querySelector('.stavka-ukupno-foreign-value');
        const foreignCurrency = stavkaRow.querySelector('.stavka-ukupno-foreign-currency');

        if (srednjiKurs > 0) {
            const ukupnoRSD = ukupnoForeign * srednjiKurs;  // Calculated amount in RSD
            foreignValue.textContent = ukupnoRSD.toFixed(2);
            foreignCurrency.textContent = 'RSD';
            foreignContainer.style.display = 'inline';
        } else {
            foreignContainer.style.display = 'none';
        }
    } else {
        // STANDARD: cena is in RSD
        const ukupnoRSD = kolicina * cena;
        stavkaRow.querySelector('.stavka-ukupno').textContent = ukupnoRSD.toFixed(2);
        stavkaRow.querySelector('.stavka-ukupno-currency').textContent = 'RSD';  // Show RSD

        // Hide foreign currency for standard invoices
        const foreignContainer = stavkaRow.querySelector('.stavka-ukupno-foreign');
        if (foreignContainer) {
            foreignContainer.style.display = 'none';
        }
    }

    // Update total
    calculateUkupanIznos();
}

/**
 * Calculate ukupan iznos fakture (sum of all stavke)
 * Handles both standard (RSD) and devizna (dual-currency) invoices
 *
 * OPCIJA A LOGIC:
 * - For devizna: sum all stavke in EUR (primary), then multiply by kurs to get RSD (calculated)
 * - For standard: sum all stavke in RSD only
 * - Display for devizna: Foreign amount first, RSD second
 */
function calculateUkupanIznos() {
    const tipFakture = document.querySelector('input[name="tip_fakture"]:checked').value;
    let ukupanIznosRSD = 0;

    if (tipFakture === 'devizna') {
        // Devizna faktura - sum in foreign currency
        const valuta = document.getElementById('valuta_fakture').value || 'EUR';
        const srednjiKurs = parseFloat(document.getElementById('srednji_kurs').value || 0);

        let totalForeign = 0;

        // Sum all stavke (already in foreign currency)
        document.querySelectorAll('.stavka-row').forEach(stavka => {
            const ukupno = parseFloat(stavka.querySelector('.stavka-ukupno').textContent) || 0;
            totalForeign += ukupno;
        });

        if (srednjiKurs > 0) {
            // Calculate RSD amount: foreign * kurs = RSD
            const totalRSD = totalForeign * srednjiKurs;
            ukupanIznosRSD = totalRSD;

            // Show foreign currency amount (primary display for devizna)
            document.getElementById('ukupan_iznos_originalna_container').style.display = 'block';
            document.getElementById('ukupan_iznos_originalna').textContent = totalForeign.toFixed(2) + ' ' + valuta;
            document.getElementById('display_kurs').textContent = srednjiKurs.toFixed(4);
            document.getElementById('ukupan_iznos_label').textContent = 'Iznos u RSD:';

            // Show RSD equivalent (secondary display)
            document.getElementById('ukupan_iznos_rsd').textContent = totalRSD.toFixed(2) + ' RSD';
        } else {
            // No kurs available - just show foreign amount
            document.getElementById('ukupan_iznos_originalna_container').style.display = 'block';
            document.getElementById('ukupan_iznos_originalna').textContent = totalForeign.toFixed(2) + ' ' + valuta;
            document.getElementById('ukupan_iznos_label').textContent = 'Ukupan Iznos:';
            document.getElementById('ukupan_iznos_rsd').textContent = '(Kurs nije dostupan)';
            ukupanIznosRSD = 0; // Can't calculate RSD without kurs
        }
    } else {
        // Standardna faktura - sum in RSD only
        let totalRSD = 0;

        document.querySelectorAll('.stavka-row').forEach(stavka => {
            const ukupno = parseFloat(stavka.querySelector('.stavka-ukupno').textContent) || 0;
            totalRSD += ukupno;
        });

        ukupanIznosRSD = totalRSD;

        document.getElementById('ukupan_iznos_originalna_container').style.display = 'none';
        document.getElementById('ukupan_iznos_label').textContent = 'Ukupan Iznos:';
        document.getElementById('ukupan_iznos_rsd').textContent = totalRSD.toFixed(2) + ' RSD';
    }

    // NEW: Update limit widget with new invoice amount (Task 5 - Story 5.4)
    if (typeof loadLimitData === 'function') {
        loadLimitData(ukupanIznosRSD);
    }
}

/**
 * Initialize form submit
 */
function initializeFormSubmit() {
    const form = document.getElementById('fakturaForm');

    form.addEventListener('submit', function(e) {
        // Validate at least one stavka
        const stavke = document.querySelectorAll('.stavka-row');
        if (stavke.length === 0) {
            e.preventDefault();
            alert('Morate dodati bar jednu stavku!');
            return false;
        }

        // Validate komitent selected
        if (!document.getElementById('komitent_id').value) {
            e.preventDefault();
            alert('Morate izabrati komitenta!');
            return false;
        }

        // Collect stavke data and append to form
        collectStavkeData();

        return true;
    });
}

/**
 * Collect stavke data before form submit
 */
function collectStavkeData() {
    const stavke = document.querySelectorAll('.stavka-row');

    stavke.forEach((stavka, index) => {
        const artikalId = stavka.querySelector('.artikal-id').value;
        const naziv = stavka.querySelector('.stavka-naziv').value || stavka.querySelector('.artikal-search').value;
        const kolicina = stavka.querySelector('.stavka-kolicina').value;
        const jedinica = stavka.querySelector('.stavka-jedinica').value;
        const cena = stavka.querySelector('.stavka-cena').value;

        // Create hidden inputs for each stavka field
        if (artikalId) {
            createHiddenInput(`stavke-${index}-artikal_id`, artikalId);
        }
        createHiddenInput(`stavke-${index}-naziv`, naziv);
        createHiddenInput(`stavke-${index}-kolicina`, kolicina);
        createHiddenInput(`stavke-${index}-jedinica_mere`, jedinica);
        createHiddenInput(`stavke-${index}-cena`, cena);
    });
}

/**
 * Create hidden input for form submission
 */
function createHiddenInput(name, value) {
    const form = document.getElementById('fakturaForm');

    // Remove existing input if any
    const existing = form.querySelector(`input[name="${name}"]`);
    if (existing) {
        existing.remove();
    }

    // Create new hidden input
    const input = document.createElement('input');
    input.type = 'hidden';
    input.name = name;
    input.value = value;
    form.appendChild(input);
}

/**
 * ========================================
 * FOREIGN CURRENCY (DEVIZNA) FUNCTIONALITY
 * ========================================
 */

/**
 * Initialize devizna faktura functionality
 */
function initializeDeviznaFaktura() {
    // Event listener on tip_fakture radio buttons
    const tipRadios = document.querySelectorAll('input[name="tip_fakture"]');
    tipRadios.forEach(radio => {
        radio.addEventListener('change', handleTipFaktureChange);
    });

    // Event listener on valuta dropdown
    const valutaSelect = document.getElementById('valuta_fakture');
    if (valutaSelect) {
        valutaSelect.addEventListener('change', function() {
            fetchNBSKurs();
            // Update currency labels in all stavke
            updateStavkaCurrencyLabels();
            // Update currency display in all stavke
            recalculateUkupanIznos();
        });
    }

    // Event listener on datum_prometa (refresh kurs when date changes)
    const datumPrometa = document.getElementById('datum_prometa');
    if (datumPrometa) {
        datumPrometa.addEventListener('change', function() {
            const tipFakture = document.querySelector('input[name="tip_fakture"]:checked').value;
            if (tipFakture === 'devizna') {
                fetchNBSKurs();
            }
        });
    }

    // Manual kurs toggle button
    const manualKursToggle = document.getElementById('manualKursToggle');
    if (manualKursToggle) {
        manualKursToggle.addEventListener('click', toggleManualKurs);
    }

    // Event listener on srednji_kurs input (for manual override)
    const srednjiKursInput = document.getElementById('srednji_kurs');
    if (srednjiKursInput) {
        srednjiKursInput.addEventListener('input', recalculateUkupanIznos);
    }
}

/**
 * Convert stavka prices when switching between standard ↔ devizna
 * @param {string} direction - 'rsd_to_foreign' or 'foreign_to_rsd'
 */
function convertStavkaPrices(direction) {
    const srednjiKursInput = document.getElementById('srednji_kurs');
    const kurs = parseFloat(srednjiKursInput.value || 0);

    if (kurs <= 0) {
        // No kurs available - can't convert
        return;
    }

    document.querySelectorAll('.stavka-row').forEach(row => {
        const cenaInput = row.querySelector('.stavka-cena');
        const currentCena = parseFloat(cenaInput.value || 0);

        if (currentCena > 0) {
            let newCena;
            if (direction === 'rsd_to_foreign') {
                // RSD → EUR: divide by kurs
                newCena = currentCena / kurs;
            } else {
                // EUR → RSD: multiply by kurs
                newCena = currentCena * kurs;
            }
            cenaInput.value = newCena.toFixed(2);
        }
    });
}

/**
 * Update currency labels in all stavke rows
 */
function updateStavkaCurrencyLabels() {
    const tipFakture = document.querySelector('input[name="tip_fakture"]:checked');
    const valutaSelect = document.getElementById('valuta_fakture');

    let currency = 'RSD';
    if (tipFakture && tipFakture.value === 'devizna' && valutaSelect && valutaSelect.value) {
        currency = valutaSelect.value;
    }

    // Update all stavka cena labels
    document.querySelectorAll('.stavka-row').forEach(row => {
        const cenaLabel = row.querySelector('.stavka-cena-label');
        if (cenaLabel) {
            cenaLabel.innerHTML = `Cena (${currency}) *`;
        }
    });
}

/**
 * Handle tip fakture change (show/hide devizni fieldset)
 * Also converts existing stavka prices when switching between standard ↔ devizna
 */
function handleTipFaktureChange(event) {
    const selectedTip = event.target.value;
    const previousTip = event.target.dataset.previousValue || 'standardna';
    const devizniFieldset = document.getElementById('devizni_fieldset');

    if (selectedTip === 'devizna') {
        devizniFieldset.style.display = 'block';
        // Fetch NBS kurs if valuta is selected
        const valuta = document.getElementById('valuta_fakture').value;
        if (valuta && valuta !== '') {
            fetchNBSKurs();
        }

        // Convert existing stavka prices from RSD → EUR if switching from standard
        if (previousTip === 'standardna') {
            convertStavkaPrices('rsd_to_foreign');
        }
    } else {
        devizniFieldset.style.display = 'none';

        // Convert existing stavka prices from EUR → RSD if switching from devizna
        if (previousTip === 'devizna') {
            convertStavkaPrices('foreign_to_rsd');
        }

        // Clear devizna fields
        document.getElementById('valuta_fakture').value = '';
        document.getElementById('srednji_kurs').value = '';
    }

    // Store current value for next change
    event.target.dataset.previousValue = selectedTip;

    // Update currency labels in all stavke
    updateStavkaCurrencyLabels();

    // Recalculate and update display (all stavke and total)
    recalculateUkupanIznos();
}

/**
 * Fetch NBS exchange rate via AJAX
 */
function fetchNBSKurs() {
    const valuta = document.getElementById('valuta_fakture').value;
    const datum = document.getElementById('datum_prometa').value;
    const srednjiKursInput = document.getElementById('srednji_kurs');

    // Don't fetch if manual mode is enabled
    if (!srednjiKursInput.readOnly) {
        return;
    }

    if (!valuta || valuta === '' || !datum) {
        return;
    }

    // Show loading state
    document.getElementById('kurs_loading').style.display = 'inline';
    document.getElementById('kurs_success').style.display = 'none';
    document.getElementById('kurs_error').style.display = 'none';

    // AJAX call to NBS kursna API
    apiFetch(`${window.API_URLS.kursevi}?valuta=${valuta}&datum=${datum}`)
        .then(data => {
            document.getElementById('kurs_loading').style.display = 'none';

            // API returns kurs as property with valuta name (e.g., data.EUR)
            const kursValue = parseFloat(data[valuta]);

            if (kursValue && kursValue > 0) {
                // Success - populate kurs
                srednjiKursInput.value = kursValue.toFixed(4);
                document.getElementById('kurs_datum').textContent = data.datum || datum;
                document.getElementById('kurs_success').style.display = 'inline';

                // Recalculate all stavke and total with dual-currency display
                recalculateUkupanIznos();
            } else {
                // Error - NBS kurs not available
                srednjiKursInput.value = '';
                document.getElementById('kurs_error').style.display = 'inline';
            }
        })
        .catch(error => {
            console.error('NBS kurs fetch error:', error);
            document.getElementById('kurs_loading').style.display = 'none';
            document.getElementById('kurs_error').style.display = 'inline';
            srednjiKursInput.value = '';

            // Show user-friendly error message
            if (error.isNetworkError) {
                showErrorMessage('Greška u komunikaciji sa serverom. Nije moguće učitati NBS kurs.');
            } else {
                showErrorMessage(error.message || 'NBS kurs nije dostupan za izabrani datum.');
            }
        });
}

/**
 * Toggle manual kurs input mode
 */
function toggleManualKurs() {
    const srednjiKursInput = document.getElementById('srednji_kurs');
    const toggleButton = document.getElementById('manualKursToggle');
    const icon = toggleButton.querySelector('i');

    if (srednjiKursInput.readOnly) {
        // Enable manual mode
        srednjiKursInput.readOnly = false;
        srednjiKursInput.classList.add('bg-warning', 'bg-opacity-10');
        icon.className = 'fa-solid fa-unlock';
        toggleButton.title = 'Automatski NBS kurs';

        // Hide kurs info messages
        document.getElementById('kurs_success').style.display = 'none';
        document.getElementById('kurs_error').style.display = 'none';
    } else {
        // Disable manual mode - fetch from NBS again
        srednjiKursInput.readOnly = true;
        srednjiKursInput.classList.remove('bg-warning', 'bg-opacity-10');
        icon.className = 'fa-solid fa-lock';
        toggleButton.title = 'Ručno unesi kurs';

        // Fetch NBS kurs
        fetchNBSKurs();
    }
}

/**
 * Recalculate ukupan iznos (for devizna fakture with dual-currency display)
 * This is called when kurs changes or tip fakture changes
 */
function recalculateUkupanIznos() {
    // Recalculate all stavke to update foreign currency display
    document.querySelectorAll('.stavka-row').forEach(stavkaRow => {
        calculateStavkaUkupno(stavkaRow);
    });

    // Main total is updated by calculateStavkaUkupno calls above
}

/**
 * Validate komitent has devizni računi for devizna fakture
 */
function validateKomitentForDevizna(komitent) {
    const tipFakture = document.querySelector('input[name="tip_fakture"]:checked').value;

    if (tipFakture === 'devizna') {
        // Check if komitent has at least one devizni račun
        if (!komitent.devizni_racuni || komitent.devizni_racuni.length === 0) {
            alert('UPOZORENJE: Izabrani komitent nema devizni račun.\n\nDevizne fakture zahtevaju da komitent ima bar jedan devizni račun (IBAN, SWIFT, valuta). Molimo ažurirajte podatke komitenta pre kreiranja devizne fakture.');
            return false;
        }
    }

    return true;
}

/**
 * ============================================================================
 * LIMIT TRACKING WIDGET (Story 5.4)
 * ============================================================================
 */

/**
 * Initialize limit tracking widget
 * Loads initial limit data when page loads
 */
function initializeLimitWidget() {
    // Check if widget exists on page (only on nova faktura form)
    const widget = document.getElementById('limit_widget');
    if (!widget) {
        return; // Widget not present on this page
    }

    // Load initial limit data (without new invoice simulation)
    loadLimitData(0);
}

/**
 * Load limit widget data from API
 * @param {number} novaFakturaIznos - Amount of new invoice for simulation (default: 0)
 */
function loadLimitData(novaFakturaIznos = 0) {
    // Check if widget exists
    const widget = document.getElementById('limit_widget');
    if (!widget) {
        return;
    }

    // Show loading state
    document.getElementById('limit_loading').style.display = 'block';
    document.getElementById('limit_content').style.display = 'none';
    document.getElementById('limit_error').style.display = 'none';

    // Construct API URL with query parameter
    const apiUrl = `${window.API_URLS.limitWidgetData}?nova_faktura_iznos=${novaFakturaIznos}`;

    // Fetch data from API
    apiFetch(apiUrl)
        .then(data => {
            // Handle success - update widget with data
            updateLimitWidget(data);
        })
        .catch(error => {
            // Handle error
            console.error('Error loading limit widget data:', error);
            document.getElementById('limit_loading').style.display = 'none';
            document.getElementById('limit_content').style.display = 'none';
            document.getElementById('limit_error').style.display = 'block';

            // Show user-friendly error message (optional - widget already shows error state)
            if (error.isNetworkError) {
                showErrorMessage('Greška u komunikaciji sa serverom. Limit widget nije dostupan.');
            }
        });
}

/**
 * Update limit widget display with data from API
 * @param {Object} data - API response data
 */
function updateLimitWidget(data) {
    // Hide loading, show content
    document.getElementById('limit_loading').style.display = 'none';
    document.getElementById('limit_content').style.display = 'block';
    document.getElementById('limit_error').style.display = 'none';

    // Update rolling limit display
    document.getElementById('rolling_limit_display').textContent = formatCurrency(data.rolling_limit);

    // Update promet 365 dana
    document.getElementById('promet_365_display').textContent = formatCurrency(data.promet_365_dana);

    // Update preostali limit with color coding
    const preostaliElement = document.getElementById('preostali_limit_display');
    preostaliElement.textContent = formatCurrency(data.preostali_limit);

    // Color code based on remaining limit
    preostaliElement.classList.remove('text-success', 'text-warning', 'text-danger');
    if (data.preostali_limit > 0) {
        preostaliElement.classList.add('text-success');
    } else {
        preostaliElement.classList.add('text-danger');
    }

    // Update progress bar
    const progressBar = document.getElementById('progress_bar');
    const progressPercentage = Math.round(data.progress_percentage);
    progressBar.style.width = `${data.progress_percentage}%`;
    progressBar.textContent = `${progressPercentage}%`;

    // Update progress bar color
    progressBar.classList.remove('bg-success', 'bg-warning', 'bg-danger');
    progressBar.classList.add(`bg-${data.progress_color}`);

    // Update projekcije displays
    document.getElementById('projekcija_7_display').textContent = formatCurrency(data.projekcija_7);
    document.getElementById('projekcija_15_display').textContent = formatCurrency(data.projekcija_15);
    document.getElementById('projekcija_30_display').textContent = formatCurrency(data.projekcija_30);

    // Show/hide nova faktura simulation section
    if (data.nova_faktura_iznos > 0) {
        document.getElementById('nova_faktura_section').style.display = 'block';
        document.getElementById('nova_faktura_iznos_display').textContent = formatCurrency(data.nova_faktura_iznos);

        const preostaloNakonElement = document.getElementById('preostalo_nakon_display');
        preostaloNakonElement.textContent = formatCurrency(data.preostalo_nakon_nove);

        // Color code preostalo nakon based on value
        preostaloNakonElement.classList.remove('text-success', 'text-danger');
        if (data.preostalo_nakon_nove > 0) {
            preostaloNakonElement.classList.add('text-success');
        } else {
            preostaloNakonElement.classList.add('text-danger');
        }
    } else {
        document.getElementById('nova_faktura_section').style.display = 'none';
    }

    // Show/hide over limit warning
    if (data.over_limit) {
        document.getElementById('over_limit_warning').style.display = 'block';
        document.getElementById('over_limit_amount_display').textContent = formatCurrency(data.over_limit_amount);
    } else {
        document.getElementById('over_limit_warning').style.display = 'none';
    }
}

/**
 * Format number as currency (Serbian locale)
 * @param {number} amount - Amount to format
 * @returns {string} - Formatted currency string (e.g., "1,000,000 RSD")
 */
function formatCurrency(amount) {
    return new Intl.NumberFormat('sr-RS', {
        minimumFractionDigits: 0,
        maximumFractionDigits: 0
    }).format(amount) + ' RSD';
}
