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

    // Add first stavka by default
    addStavka();

    // Add stavka button handler
    document.getElementById('addStavkaBtn').addEventListener('click', addStavka);
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
            fetch(`/api/komitenti/search?q=${encodeURIComponent(query)}`)
                .then(response => response.json())
                .then(data => {
                    renderKomitentResults(data);
                })
                .catch(error => {
                    console.error('Komitent search error:', error);
                    resultsDiv.innerHTML = '<div class="list-group-item text-danger">Greška pri pretrazi komitenata</div>';
                    resultsDiv.style.display = 'block';
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
 */
function addStavka() {
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

    // Initialize artikal autocomplete for this row
    initializeArtikalAutocomplete(newRow);

    // Initialize auto-calculation for this row
    initializeStavkaCalculation(newRow);

    // Initialize remove button
    const removeBtn = newRow.querySelector('.remove-stavka');
    removeBtn.addEventListener('click', function() {
        removeStavka(newRow);
    });
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
            fetch(`/api/artikli/search?q=${encodeURIComponent(query)}`)
                .then(response => response.json())
                .then(data => {
                    renderArtikalResults(data, resultsDiv, searchInput, artikalIdInput, nazivInput, kolicinaInput, jedinicaInput, cenaInput);
                })
                .catch(error => {
                    console.error('Artikal search error:', error);
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
            cenaInput.value = a.podrazumevana_cena;

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
 * Calculate stavka ukupno
 */
function calculateStavkaUkupno(stavkaRow) {
    const kolicina = parseFloat(stavkaRow.querySelector('.stavka-kolicina').value) || 0;
    const cena = parseFloat(stavkaRow.querySelector('.stavka-cena').value) || 0;
    const ukupno = kolicina * cena;

    stavkaRow.querySelector('.stavka-ukupno').textContent = ukupno.toFixed(2);

    // Update total
    calculateUkupanIznos();
}

/**
 * Calculate ukupan iznos fakture (sum of all stavke)
 */
function calculateUkupanIznos() {
    let total = 0;

    document.querySelectorAll('.stavka-row').forEach(stavka => {
        const ukupno = parseFloat(stavka.querySelector('.stavka-ukupno').textContent) || 0;
        total += ukupno;
    });

    document.getElementById('ukupan_iznos').textContent = total.toFixed(2) + ' RSD';
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
        valutaSelect.addEventListener('change', fetchNBSKurs);
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
 * Handle tip fakture change (show/hide devizni fieldset)
 */
function handleTipFaktureChange(event) {
    const selectedTip = event.target.value;
    const devizniFieldset = document.getElementById('devizni_fieldset');

    if (selectedTip === 'devizna') {
        devizniFieldset.style.display = 'block';
        // Fetch NBS kurs if valuta is selected
        const valuta = document.getElementById('valuta_fakture').value;
        if (valuta && valuta !== '') {
            fetchNBSKurs();
        }
    } else {
        devizniFieldset.style.display = 'none';
        // Clear devizna fields
        document.getElementById('valuta_fakture').value = '';
        document.getElementById('srednji_kurs').value = '';
    }
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
    fetch(`/api/kursevi?valuta=${valuta}&datum=${datum}`)
        .then(response => {
            if (!response.ok) {
                throw new Error('NBS kurs not available');
            }
            return response.json();
        })
        .then(data => {
            document.getElementById('kurs_loading').style.display = 'none';

            // API returns kurs as property with valuta name (e.g., data.EUR)
            const kursValue = parseFloat(data[valuta]);

            if (kursValue && kursValue > 0) {
                // Success - populate kurs
                srednjiKursInput.value = kursValue.toFixed(4);
                document.getElementById('kurs_datum').textContent = data.datum || datum;
                document.getElementById('kurs_success').style.display = 'inline';

                // Recalculate total amount
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
 */
function recalculateUkupanIznos() {
    const tipFakture = document.querySelector('input[name="tip_fakture"]:checked').value;

    if (tipFakture !== 'devizna') {
        return;
    }

    const srednjiKurs = parseFloat(document.getElementById('srednji_kurs').value || 0);

    // Calculate total in original currency
    let ukupanIznosOriginalna = 0;
    document.querySelectorAll('.stavka-row').forEach(row => {
        const ukupno = parseFloat(row.querySelector('.ukupno-input').value || 0);
        ukupanIznosOriginalna += ukupno;
    });

    // Calculate RSD equivalent
    const ukupanIznosRSD = ukupanIznosOriginalna * srednjiKurs;

    // Display dual-currency total (this would be in the UI somewhere)
    // TODO: Update UI to show both amounts
    console.log(`Total: ${ukupanIznosOriginalna.toFixed(2)} (original) = ${ukupanIznosRSD.toFixed(2)} RSD`);
}

/**
 * Validate komitent has IBAN and SWIFT for devizna fakture
 */
function validateKomitentForDevizna(komitent) {
    const tipFakture = document.querySelector('input[name="tip_fakture"]:checked').value;

    if (tipFakture === 'devizna') {
        if (!komitent.iban || !komitent.swift) {
            alert('UPOZORENJE: Izabrani komitent nema IBAN i SWIFT kod.\n\nDevizne fakture zahtevaju da komitent ima IBAN i SWIFT kod. Molimo ažurirajte podatke komitenta pre kreiranja devizne fakture.');
            return false;
        }
    }

    return true;
}
