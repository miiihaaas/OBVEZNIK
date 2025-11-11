/**
 * OBVEZNIK - Global JavaScript Utilities
 * @description Globalne funkcije za error handling, AJAX pozive, i UI interakcije
 */

// =============================================================================
// GLOBAL FETCH WRAPPER WITH ERROR HANDLING
// =============================================================================

/**
 * Global fetch wrapper sa network error handling-om
 * @param {string} url - API endpoint URL
 * @param {object} options - Fetch options (method, headers, body, etc.)
 * @returns {Promise<any>} - Response JSON ili baca error
 */
async function apiFetch(url, options = {}) {
    try {
        const response = await fetch(url, options);

        // HTTP error response (400, 404, 500, etc.)
        if (!response.ok) {
            let errorData;
            try {
                errorData = await response.json();
            } catch (parseError) {
                // Response nije JSON format
                errorData = { message: `HTTP greška: ${response.status} ${response.statusText}` };
            }

            const errorMessage = errorData.message || errorData.error || `HTTP greška: ${response.status}`;
            throw new Error(errorMessage);
        }

        // Uspešan response - vrati JSON
        return await response.json();
    } catch (error) {
        // Network error (no connection, timeout, CORS, itd.)
        if (error instanceof TypeError && (error.message === 'Failed to fetch' || error.message.includes('NetworkError'))) {
            const networkError = new Error('Greška u komunikaciji sa serverom. Proverite internet konekciju i pokušajte ponovo.');
            networkError.isNetworkError = true;
            throw networkError;
        }

        // Re-throw error ako nije network error
        throw error;
    }
}

// =============================================================================
// FLASH MESSAGE DISPLAY FUNCTIONS
// =============================================================================

/**
 * Prikazuje error poruku korisniku (crveni alert)
 * @param {string} message - Tekst error poruke
 * @param {boolean} dismissible - Da li je poruka dismissible (default: true)
 */
function showErrorMessage(message, dismissible = true) {
    showFlashMessage(message, 'danger', dismissible);
}

/**
 * Prikazuje success poruku korisniku (zeleni alert)
 * @param {string} message - Tekst success poruke
 * @param {boolean} autoDismiss - Da li automatski sakriti poruku nakon 5s (default: true)
 */
function showSuccessMessage(message, autoDismiss = true) {
    showFlashMessage(message, 'success', true, autoDismiss);
}

/**
 * Prikazuje warning poruku korisniku (žuti alert)
 * @param {string} message - Tekst warning poruke
 * @param {boolean} autoDismiss - Da li automatski sakriti poruku nakon 10s (default: true)
 */
function showWarningMessage(message, autoDismiss = true) {
    showFlashMessage(message, 'warning', true, autoDismiss);
}

/**
 * Prikazuje info poruku korisniku (plavi alert)
 * @param {string} message - Tekst info poruke
 * @param {boolean} autoDismiss - Da li automatski sakriti poruku nakon 5s (default: true)
 */
function showInfoMessage(message, autoDismiss = true) {
    showFlashMessage(message, 'info', true, autoDismiss);
}

/**
 * Prikazuje flash message dinamički (generic funkcija)
 * @param {string} message - Tekst poruke
 * @param {string} category - Bootstrap alert kategorija (success, danger, warning, info)
 * @param {boolean} dismissible - Da li je poruka dismissible
 * @param {boolean} autoDismiss - Da li automatski sakriti poruku nakon X sekundi
 */
function showFlashMessage(message, category = 'info', dismissible = true, autoDismiss = false) {
    // Icon prema kategoriji
    let icon = 'fa-circle-info';
    if (category === 'success') icon = 'fa-circle-check';
    else if (category === 'danger') icon = 'fa-circle-exclamation';
    else if (category === 'warning') icon = 'fa-triangle-exclamation';

    // Kreiraj HTML za alert
    const alertHtml = `
        <div class="alert alert-${category} ${dismissible ? 'alert-dismissible' : ''} fade show d-flex align-items-center shadow-sm" role="alert">
            <i class="fa-solid ${icon} me-3 fs-5"></i>
            <div class="flex-grow-1">${message}</div>
            ${dismissible ? '<button type="button" class="btn-close" data-bs-dismiss="alert" aria-label="Zatvori"></button>' : ''}
        </div>
    `;

    // Pronađi container za flash messages ili main content
    let container = document.querySelector('.container.mt-4');
    if (!container) {
        // Ako ne postoji flash message container, pronađi prvi .container ili .content
        container = document.querySelector('.content .container');
        if (!container) {
            container = document.querySelector('.content');
        }
    }

    if (container) {
        // Dodaj alert na vrh container-a
        container.insertAdjacentHTML('afterbegin', alertHtml);

        // Auto-dismiss ako je enabled
        if (autoDismiss) {
            const alertElement = container.querySelector('.alert');
            const dismissTime = category === 'warning' ? 10000 : 5000; // 10s za warning, 5s za ostale

            setTimeout(() => {
                if (alertElement && bootstrap.Alert) {
                    const bsAlert = new bootstrap.Alert(alertElement);
                    bsAlert.close();
                }
            }, dismissTime);
        }
    } else {
        // Fallback: alert() ako ne može da pronađe container
        console.error('Flash message container not found, using alert():', message);
        alert(message);
    }
}

// =============================================================================
// NETWORK ERROR HANDLER
// =============================================================================

/**
 * Handles network errors i prikazuje user-friendly poruku sa retry opcijom
 * @param {Error} error - Error objekat
 * @param {Function} retryCallback - Callback funkcija za retry (opciono)
 */
function handleNetworkError(error, retryCallback = null) {
    console.error('Network error occurred:', error);

    let message = error.message || 'Greška u komunikaciji sa serverom.';

    // Dodaj retry button ako je callback prosleđen
    if (retryCallback && typeof retryCallback === 'function') {
        const retryId = 'retry-btn-' + Date.now();
        message += ` <button class="btn btn-sm btn-light ms-2" id="${retryId}" onclick="(${retryCallback.toString()})()">
            <i class="fa-solid fa-rotate-right me-1"></i> Pokušaj ponovo
        </button>`;
    }

    showErrorMessage(message, true);
}

// =============================================================================
// AUTO-DISMISS INITIALIZATION (runs on page load)
// =============================================================================

document.addEventListener('DOMContentLoaded', function() {
    // Auto-dismiss success messages after 5 seconds
    const successAlerts = document.querySelectorAll('.alert-success.alert-dismissible');
    successAlerts.forEach(function(alert) {
        setTimeout(function() {
            if (bootstrap.Alert) {
                const bsAlert = new bootstrap.Alert(alert);
                bsAlert.close();
            }
        }, 5000);
    });

    // Auto-dismiss warning messages after 10 seconds
    const warningAlerts = document.querySelectorAll('.alert-warning.alert-dismissible');
    warningAlerts.forEach(function(alert) {
        setTimeout(function() {
            if (bootstrap.Alert) {
                const bsAlert = new bootstrap.Alert(alert);
                bsAlert.close();
            }
        }, 10000);
    });

    // Info messages auto-dismiss after 5 seconds (opciono)
    const infoAlerts = document.querySelectorAll('.alert-info.alert-dismissible');
    infoAlerts.forEach(function(alert) {
        setTimeout(function() {
            if (bootstrap.Alert) {
                const bsAlert = new bootstrap.Alert(alert);
                bsAlert.close();
            }
        }, 5000);
    });

    // Error messages ostaju vidljive (ONLY manual dismiss)

    // Initialize confirmation modals
    initializeConfirmationModals();
});

// =============================================================================
// CONFIRMATION MODAL FUNCTIONALITY (Story 5.7)
// =============================================================================

/**
 * Initialize confirmation modals with accessibility features
 * - Focus trap: focus stays within modal
 * - ESC key: closes modal
 * - ARIA attributes: already set in macro templates
 */
function initializeConfirmationModals() {
    const modals = document.querySelectorAll('.modal');

    modals.forEach(function(modal) {
        // ESC key to close modal (Bootstrap 5 handles this by default)
        // Focus trap is also handled by Bootstrap 5 by default

        // Focus first button when modal opens
        modal.addEventListener('shown.bs.modal', function() {
            // Find first focusable element (usually the confirm button)
            const confirmButton = modal.querySelector('.btn-danger, .btn-warning, .btn-primary');
            if (confirmButton) {
                confirmButton.focus();
            }
        });

        // Clear focus when modal closes
        modal.addEventListener('hidden.bs.modal', function() {
            // Return focus to trigger button
            const triggerButton = document.querySelector(`[data-bs-target="#${modal.id}"]`);
            if (triggerButton) {
                triggerButton.focus();
            }
        });
    });
}

/**
 * Show confirmation modal programmatically
 * @param {string} modalId - ID of modal to show
 */
function showConfirmationModal(modalId) {
    const modalElement = document.getElementById(modalId);
    if (modalElement && bootstrap.Modal) {
        const modal = new bootstrap.Modal(modalElement);
        modal.show();
    }
}

/**
 * Hide confirmation modal programmatically
 * @param {string} modalId - ID of modal to hide
 */
function hideConfirmationModal(modalId) {
    const modalElement = document.getElementById(modalId);
    if (modalElement && bootstrap.Modal) {
        const modal = bootstrap.Modal.getInstance(modalElement);
        if (modal) {
            modal.hide();
        }
    }
}

// =============================================================================
// LOADING STATE HELPERS
// =============================================================================

/**
 * Show button loading state
 * @param {string} buttonId - ID button elementa
 */
function showButtonLoading(buttonId) {
    const button = document.getElementById(buttonId);
    if (button) {
        button.disabled = true;
        button.classList.add('loading');
    }
}

/**
 * Hide button loading state
 * @param {string} buttonId - ID button elementa
 */
function hideButtonLoading(buttonId) {
    const button = document.getElementById(buttonId);
    if (button) {
        button.disabled = false;
        button.classList.remove('loading');
    }
}

/**
 * Show full-page spinner overlay
 * @param {string} spinnerId - ID spinner elementa
 */
function showFullPageSpinner(spinnerId) {
    const spinner = document.getElementById(spinnerId);
    if (spinner) {
        spinner.style.display = 'flex';
    }
}

/**
 * Hide full-page spinner overlay
 * @param {string} spinnerId - ID spinner elementa
 */
function hideFullPageSpinner(spinnerId) {
    const spinner = document.getElementById(spinnerId);
    if (spinner) {
        spinner.style.display = 'none';
    }
}

/**
 * Show inline spinner
 * @param {string} spinnerId - ID spinner elementa
 */
function showInlineSpinner(spinnerId) {
    const spinner = document.getElementById(spinnerId);
    if (spinner) {
        spinner.style.display = 'flex';
    }
}

/**
 * Hide inline spinner
 * @param {string} spinnerId - ID spinner elementa
 */
function hideInlineSpinner(spinnerId) {
    const spinner = document.getElementById(spinnerId);
    if (spinner) {
        spinner.style.display = 'none';
    }
}
