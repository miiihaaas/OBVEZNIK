/**
 * Faktura Detail Page
 * Handles PDF generation retry, email sending, and auto-refresh when PDF is generating
 *
 * Usage: Include this script on fakture/detail.html template.
 *        Requires data attributes for configuration (see init function).
 */

(function() {
    'use strict';

    // Configuration from data attributes
    let config = {
        fakturaId: null,
        retryPdfUrl: null,
        retryEmailUrl: null,
        sendEmailUrl: null,
        pdfGenerating: false,
        csrfToken: ''
    };

    let countdownInterval = null;

    /**
     * Get CSRF token from meta tag
     * @returns {string} CSRF token
     */
    function getCSRFToken() {
        const meta = document.querySelector('meta[name="csrf-token"]');
        return meta ? meta.getAttribute('content') : '';
    }

    /**
     * Auto-refresh countdown when PDF is generating
     * Reloads page after countdown reaches 0
     */
    function startPdfGenerationCountdown() {
        let countdown = 3;
        const countdownElement = document.getElementById('countdown');

        countdownInterval = setInterval(() => {
            countdown--;
            if (countdownElement) {
                countdownElement.textContent = countdown;
            }

            if (countdown <= 0) {
                clearInterval(countdownInterval);
                window.location.reload();
            }
        }, 1000);
    }

    /**
     * Check PDF status (called manually via button click)
     */
    function checkPdfStatus() {
        if (countdownInterval) {
            clearInterval(countdownInterval);
        }
        window.location.reload();
    }

    /**
     * Retry PDF generation for failed faktura
     * @param {number} fakturaId - ID of the faktura
     */
    function retryPdfGeneration(fakturaId) {
        const statusDiv = document.getElementById('retry-status-' + fakturaId);
        if (!statusDiv) {
            console.error('Status div not found for faktura:', fakturaId);
            return;
        }

        // Show loading state
        statusDiv.innerHTML = '<div class="alert alert-info"><span class="spinner-border spinner-border-sm me-2"></span>Pokušaj u toku...</div>';

        // Construct URL from template
        const url = config.retryPdfUrl.replace('/0/', '/' + fakturaId + '/');

        // Make AJAX request
        fetch(url, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-CSRFToken': config.csrfToken
            }
        })
        .then(response => response.json())
        .then(data => {
            if (data.success) {
                statusDiv.innerHTML = '<div class="alert alert-success">' + data.message + '</div>';
                // Reload page after 2 seconds to show generating status
                setTimeout(() => {
                    window.location.reload();
                }, 2000);
            } else {
                statusDiv.innerHTML = '<div class="alert alert-danger">Greška: ' + data.message + '</div>';
            }
        })
        .catch(error => {
            statusDiv.innerHTML = '<div class="alert alert-danger">Greška pri komunikaciji sa serverom.</div>';
            console.error('Error:', error);
        });
    }

    /**
     * Retry email sending for failed faktura
     * @param {number} fakturaId - ID of the faktura
     */
    function retryEmail(fakturaId) {
        const statusDiv = document.getElementById('retry-email-status-' + fakturaId);
        if (!statusDiv) {
            console.error('Email status div not found for faktura:', fakturaId);
            return;
        }

        // Show loading state
        statusDiv.innerHTML = '<div class="alert alert-info"><span class="spinner-border spinner-border-sm me-2"></span>Pokušaj u toku...</div>';

        // Construct URL from template
        const url = config.retryEmailUrl.replace('/0/', '/' + fakturaId + '/');

        // Make AJAX request
        fetch(url, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-CSRFToken': config.csrfToken
            }
        })
        .then(response => response.json())
        .then(data => {
            if (data.success) {
                statusDiv.innerHTML = '<div class="alert alert-success">' + data.message + '</div>';
                // Reload page after 2 seconds to show sending status
                setTimeout(() => {
                    window.location.reload();
                }, 2000);
            } else {
                statusDiv.innerHTML = '<div class="alert alert-danger">Greška: ' + data.message + '</div>';
            }
        })
        .catch(error => {
            statusDiv.innerHTML = '<div class="alert alert-danger">Greška pri komunikaciji sa serverom.</div>';
            console.error('Error:', error);
        });
    }

    /**
     * Setup email sending modal
     */
    function setupEmailSending() {
        const sendEmailBtn = document.getElementById('sendEmailBtn');
        if (!sendEmailBtn) return;

        sendEmailBtn.addEventListener('click', function() {
            const form = document.getElementById('emailForm');
            const formData = new FormData(form);
            const data = {
                recipient_email: formData.get('recipient_email'),
                cc_email: formData.get('cc_email') || null
            };

            // Validate form
            if (!form.checkValidity()) {
                form.reportValidity();
                return;
            }

            // Show loading state
            const spinner = document.getElementById('emailSpinner');
            const icon = document.getElementById('emailIcon');
            const btnText = document.getElementById('emailBtnText');
            const alertContainer = document.getElementById('emailAlertContainer');

            spinner.classList.remove('d-none');
            icon.classList.add('d-none');
            btnText.textContent = 'Slanje...';
            sendEmailBtn.disabled = true;
            alertContainer.innerHTML = '';

            // Make AJAX POST request
            fetch(config.sendEmailUrl, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRFToken': config.csrfToken
                },
                body: JSON.stringify(data)
            })
            .then(response => response.json())
            .then(result => {
                spinner.classList.add('d-none');
                icon.classList.remove('d-none');
                btnText.textContent = 'Pošalji Email';
                sendEmailBtn.disabled = false;

                if (result.success) {
                    alertContainer.innerHTML = '<div class="alert alert-success">Email uspešno poslat na ' + data.recipient_email + '</div>';
                    // Close modal and reload page after 2 seconds
                    setTimeout(() => {
                        const emailModal = document.getElementById('emailModal');
                        if (emailModal) {
                            const modal = bootstrap.Modal.getInstance(emailModal);
                            if (modal) modal.hide();
                        }
                        window.location.reload();
                    }, 2000);
                } else {
                    alertContainer.innerHTML = '<div class="alert alert-danger">Greška: ' + result.error + '</div>';
                }
            })
            .catch(error => {
                spinner.classList.add('d-none');
                icon.classList.remove('d-none');
                btnText.textContent = 'Pošalji Email';
                sendEmailBtn.disabled = false;
                alertContainer.innerHTML = '<div class="alert alert-danger">Greška pri komunikaciji sa serverom.</div>';
                console.error('Error:', error);
            });
        });
    }

    /**
     * Initialize faktura detail page
     */
    function init() {
        // Load configuration from data attributes
        const detailContainer = document.getElementById('fakturaDetailContainer');
        if (!detailContainer) {
            console.warn('Faktura detail: Container not found');
            return;
        }

        config.fakturaId = parseInt(detailContainer.dataset.fakturaId) || null;
        config.retryPdfUrl = detailContainer.dataset.retryPdfUrl || '';
        config.retryEmailUrl = detailContainer.dataset.retryEmailUrl || '';
        config.sendEmailUrl = detailContainer.dataset.sendEmailUrl || '';
        config.pdfGenerating = detailContainer.dataset.pdfGenerating === 'true';
        config.csrfToken = getCSRFToken();

        // Start countdown if PDF is generating
        if (config.pdfGenerating) {
            startPdfGenerationCountdown();
        }

        // Setup email sending
        setupEmailSending();

        // Expose functions globally for onclick handlers (legacy support)
        window.retryPdfGeneration = retryPdfGeneration;
        window.retryEmail = retryEmail;
        window.checkPdfStatus = checkPdfStatus;
    }

    // Initialize on DOM ready
    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', init);
    } else {
        init();
    }

})();
