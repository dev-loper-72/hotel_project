document.addEventListener('DOMContentLoaded', function() {
    const form = document.querySelector('form');

    // Add input event listeners for real-time validation
    const numberGuests = document.querySelector('[name="number_of_guests"]');
    const amountPaid = document.querySelector('[name="amount_paid"]');

    if (numberGuests) {
        numberGuests.addEventListener('input', function(e) {
            validateField(this, 'number_of_guests');
        });
        // Get max guests from the room type
        const roomTypeSelect = document.querySelector('[name="room_number"]');
        if (roomTypeSelect) {
            const maxGuests = roomTypeSelect.options[roomTypeSelect.selectedIndex].dataset.maxGuests;
            numberGuests.dataset.maxGuests = maxGuests || '4'; // Default to 4 if not set
        }
    }

    if (amountPaid) {
        amountPaid.addEventListener('input', function(e) {
            validateField(this, 'amount_paid');
        });
        // Get price from the form
        const priceInput = document.querySelector('[name="price"]');
        if (priceInput) {
            amountPaid.dataset.maxPrice = priceInput.value || '0';
        }
    }

    function validateField(field, fieldName) {
        const value = parseFloat(field.value) || 0;
        const errorContainer = getOrCreateErrorContainer(field);

        if (fieldName === 'number_of_guests') {
            const maxGuests = parseInt(field.dataset.maxGuests) || 4;
            if (value < 1) {
                showError(errorContainer, 'Number of guests must be at least 1');
            } else if (value > maxGuests) {
                showError(errorContainer, `Maximum number of guests for this room is ${maxGuests}`);
            } else {
                hideError(errorContainer);
            }
        }

        if (fieldName === 'amount_paid') {
            const maxPrice = parseFloat(field.dataset.maxPrice) || 0;
            if (value < 0) {
                showError(errorContainer, 'Payment amount must be 0 or greater');
            } else if (maxPrice > 0 && value > maxPrice) {
                showError(errorContainer, `Payment amount cannot exceed ${maxPrice}`);
            } else {
                hideError(errorContainer);
            }
        }
    }

    function getOrCreateErrorContainer(field) {
        let container = field.parentElement.querySelector('.field-error');
        if (!container) {
            container = document.createElement('div');
            container.className = 'field-error';
            const closeBtn = document.createElement('span');
            closeBtn.className = 'close-error';
            closeBtn.innerHTML = '×';
            closeBtn.onclick = function(e) {
                e.preventDefault();
                hideError(container);
            };
            container.appendChild(closeBtn);
            field.parentElement.appendChild(container);
        }
        return container;
    }

    function showError(container, message) {
        const messageElement = container.querySelector('.error-message') || document.createElement('span');
        messageElement.className = 'error-message';
        messageElement.textContent = message;
        if (!container.contains(messageElement)) {
            container.appendChild(messageElement);
        }
        container.classList.add('show');
    }

    function hideError(container) {
        container.classList.remove('show');
    }
});