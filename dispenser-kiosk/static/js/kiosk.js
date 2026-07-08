// ==========================================
// SMD Kiosk — Frontend Logic
// ==========================================
// Manages screen transitions, barcode scanning,
// Firebase data display, and dispensing flow.

// ---- State ----
let currentScreen = 'welcome';
let prescriptionData = null;        // Fetched prescription (barcode flow)
let medicinesList = [];             // All medicines from Firebase
let selectedMedicine = null;        // Selected medicine (manual flow)
let manualQuantity = 2;             // Current manual quantity
let quantityLimits = { min: 2, max: 18 };
let countdownTimer = null;          // Auto-return timer
let dispensePoller = null;          // Polling interval for dispense status
let barcodeBuffer = '';             // Accumulates barcode scanner keystrokes
let barcodeTimeout = null;          // Timeout to detect end of barcode input


// ==========================================
// Screen Navigation
// ==========================================

function navigateTo(screenId) {
    // Clean up previous screen
    cleanupScreen(currentScreen);

    // Hide all screens
    document.querySelectorAll('.screen').forEach(s => s.classList.remove('active'));

    // Show target screen
    const target = document.getElementById('screen-' + screenId);
    if (target) {
        target.classList.add('active');
        currentScreen = screenId;
        initScreen(screenId);
    }
}

function initScreen(screenId) {
    switch (screenId) {
        case 'scan':
            initScanScreen();
            break;
        case 'medicine-list':
            loadMedicines();
            break;
        case 'quantity':
            initQuantityScreen();
            break;
        case 'dispensing':
            startPollingDispenseStatus();
            break;
        case 'complete':
            startCountdown();
            break;
    }
}

function cleanupScreen(screenId) {
    switch (screenId) {
        case 'scan':
            document.removeEventListener('keydown', onBarcodeKeydown);
            clearTimeout(barcodeTimeout);
            barcodeBuffer = '';
            break;
        case 'complete':
            clearInterval(countdownTimer);
            countdownTimer = null;
            break;
        case 'dispensing':
            clearInterval(dispensePoller);
            dispensePoller = null;
            break;
    }
}

function returnHome() {
    clearInterval(countdownTimer);
    prescriptionData = null;
    selectedMedicine = null;
    manualQuantity = 2;
    navigateTo('welcome');
}


// ==========================================
// BARCODE SCAN FLOW
// ==========================================

function initScanScreen() {
    // Focus the hidden input for USB barcode scanner
    const hiddenInput = document.getElementById('barcode-input');
    if (hiddenInput) {
        hiddenInput.value = '';
        hiddenInput.focus();

        // Listen for input events (USB barcode scanners type characters rapidly)
        hiddenInput.addEventListener('input', onBarcodeInput);
    }

    // Also listen for keyboard events (backup for scanners that send key events)
    barcodeBuffer = '';
    document.addEventListener('keydown', onBarcodeKeydown);

    // Clear manual input
    const manualInput = document.getElementById('manual-barcode-input');
    if (manualInput) manualInput.value = '';

    // Update status text
    updateScanStatus('Please scan your prescription barcode', false);
}

function onBarcodeInput(e) {
    const value = e.target.value.trim();
    if (value.length >= 6) {
        // Barcode scanner usually sends complete string followed by Enter
        // Give a short delay to collect all characters
        clearTimeout(barcodeTimeout);
        barcodeTimeout = setTimeout(() => {
            if (e.target.value.trim().length >= 6) {
                processBarcodeInput(e.target.value.trim());
                e.target.value = '';
            }
        }, 200);
    }
}

function onBarcodeKeydown(e) {
    // USB barcode scanners send characters very rapidly, ending with Enter
    if (e.key === 'Enter') {
        if (barcodeBuffer.length >= 3) {
            processBarcodeInput(barcodeBuffer);
        }
        barcodeBuffer = '';
        return;
    }

    // Ignore modifier keys
    if (e.key.length === 1) {
        barcodeBuffer += e.key;
        clearTimeout(barcodeTimeout);
        barcodeTimeout = setTimeout(() => {
            barcodeBuffer = '';
        }, 500);  // Reset buffer if no input for 500ms
    }
}

function submitManualBarcode() {
    const input = document.getElementById('manual-barcode-input');
    const barcode = input ? input.value.trim() : '';
    if (barcode.length >= 3) {
        processBarcodeInput(barcode);
    }
}

async function processBarcodeInput(barcode) {
    updateScanStatus('Searching for prescription...', true);

    try {
        const response = await fetch(`/api/prescription/${encodeURIComponent(barcode)}`);
        const data = await response.json();

        if (data.success && data.prescription) {
            prescriptionData = data.prescription;

            // Check if already dispensed
            if (prescriptionData.status === 'Dispersed') {
                showError('Already Dispensed', 
                    'This prescription has already been dispensed. Please contact the pharmacy if you need assistance.');
                updateScanStatus('Please scan your prescription barcode', false);
                return;
            }

            showVerifiedScreen(prescriptionData);
        } else {
            showError('Prescription Not Found', 
                data.message || `No prescription found for barcode: ${barcode}`);
            updateScanStatus('Please scan your prescription barcode', false);
        }
    } catch (error) {
        console.error('Error fetching prescription:', error);
        showError('Connection Error', 
            'Could not connect to the database. Please try again.');
        updateScanStatus('Please scan your prescription barcode', false);
    }
}

function updateScanStatus(text, loading) {
    const statusEl = document.getElementById('scan-status-text');
    if (statusEl) {
        statusEl.textContent = text;
        if (loading) {
            statusEl.innerHTML = '<i class="bx bx-loader-alt bx-spin" style="margin-right:8px"></i>' + text;
        }
    }
}


// ==========================================
// VERIFIED SCREEN (Barcode Flow)
// ==========================================

function showVerifiedScreen(prescription) {
    // Populate patient details
    document.getElementById('v-patient-name').textContent = prescription.patientName || '—';
    document.getElementById('v-patient-phone').textContent = prescription.phone || '—';
    document.getElementById('v-patient-date').textContent = prescription.date || '—';
    document.getElementById('v-prescription-id').textContent = prescription.id || '—';

    // Populate medicines list
    const medList = document.getElementById('v-medicines-list');
    medList.innerHTML = '';

    if (prescription.medicines && prescription.medicines.length > 0) {
        prescription.medicines.forEach(med => {
            const li = document.createElement('li');
            li.className = 'med-list-item';
            li.innerHTML = `
                <div class="med-item-info">
                    <span class="med-item-name">${med.name || 'Unknown'}</span>
                    <span class="med-item-detail">${med.dosage || ''} • ${med.type || ''} • ${med.dose || 1} units × ${med.frequency || 1}/day × ${med.duration || 1} days</span>
                </div>
                <div class="med-item-qty">
                    <span class="qty-number">${med.totalQuantity || 0}</span>
                    <span class="qty-label">units</span>
                </div>
            `;
            medList.appendChild(li);
        });
    }

    navigateTo('verified');
}


// ==========================================
// MANUAL MEDICINE FLOW
// ==========================================

async function loadMedicines() {
    const container = document.getElementById('medicine-varieties-list');
    container.innerHTML = `
        <div class="loading-state">
            <i class='bx bx-loader-alt bx-spin'></i>
            <p>Loading medicines...</p>
        </div>
    `;

    try {
        const response = await fetch('/api/medicines');
        const data = await response.json();

        if (data.success) {
            medicinesList = data.medicines || [];
            if (data.limits) {
                quantityLimits = data.limits;
            }
            renderMedicineList(medicinesList);
        } else {
            container.innerHTML = `<div class="empty-state-msg">Failed to load medicines.</div>`;
        }
    } catch (error) {
        console.error('Error loading medicines:', error);
        container.innerHTML = `<div class="empty-state-msg">Connection error. Please try again.</div>`;
    }
}

function renderMedicineList(medicines) {
    const container = document.getElementById('medicine-varieties-list');
    container.innerHTML = '';

    if (medicines.length === 0) {
        container.innerHTML = `<div class="empty-state-msg">No medicines available.</div>`;
        return;
    }

    medicines.forEach((med, index) => {
        const item = document.createElement('div');
        item.className = 'med-variety-item';
        item.setAttribute('data-name', med.name.toLowerCase());
        item.onclick = () => selectMedicine(med, index);

        // Choose icon based on type
        let icon = 'bx-capsule';
        if (med.type === 'Tablet') icon = 'bx-plus-medical';
        else if (med.type === 'Syrup') icon = 'bx-test-tube';
        else if (med.type === 'Injection') icon = 'bx-injection';
        else if (med.type === 'Drops') icon = 'bx-droplet';
        else if (med.type === 'Ointment') icon = 'bx-band-aid';

        item.innerHTML = `
            <div class="med-variety-icon">
                <i class='bx ${icon}'></i>
            </div>
            <div class="med-variety-info">
                <div class="med-variety-name">${med.name}</div>
                <div class="med-variety-meta">
                    ${med.dosage || '—'} • <span class="type-badge">${med.type}</span>
                </div>
            </div>
            <i class='bx bx-chevron-right med-variety-arrow'></i>
        `;

        container.appendChild(item);
    });
}

function filterMedicines(query) {
    query = query.toLowerCase().trim();
    if (!query) {
        renderMedicineList(medicinesList);
        return;
    }
    const filtered = medicinesList.filter(m => m.name.toLowerCase().includes(query));
    renderMedicineList(filtered);
}

function selectMedicine(med, slotIndex) {
    selectedMedicine = { ...med, slot: slotIndex };
    navigateTo('quantity');
}


// ==========================================
// QUANTITY SELECTOR
// ==========================================

function initQuantityScreen() {
    if (selectedMedicine) {
        document.getElementById('selected-med-name').textContent = 
            `${selectedMedicine.name} — ${selectedMedicine.dosage || ''} (${selectedMedicine.type || ''})`;
    }

    manualQuantity = quantityLimits.min;
    document.getElementById('qty-value').value = manualQuantity;
    document.getElementById('qty-value').min = quantityLimits.min;
    document.getElementById('qty-value').max = quantityLimits.max;
    document.getElementById('qty-min-val').textContent = quantityLimits.min;
    document.getElementById('qty-max-val').textContent = quantityLimits.max;
}

function adjustQuantity(delta) {
    const input = document.getElementById('qty-value');
    let val = parseInt(input.value) || quantityLimits.min;
    val += delta;
    val = Math.max(quantityLimits.min, Math.min(quantityLimits.max, val));
    input.value = val;
    manualQuantity = val;

    // Visual feedback
    input.style.transform = 'scale(1.1)';
    setTimeout(() => { input.style.transform = 'scale(1)'; }, 150);
}

function clampQuantity() {
    const input = document.getElementById('qty-value');
    let val = parseInt(input.value) || quantityLimits.min;
    val = Math.max(quantityLimits.min, Math.min(quantityLimits.max, val));
    input.value = val;
    manualQuantity = val;
}


// ==========================================
// DISPENSING
// ==========================================

async function startDispensing() {
    if (!prescriptionData || !prescriptionData.medicines) return;

    navigateTo('dispensing');

    try {
        const response = await fetch('/api/dispense', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                barcode_id: prescriptionData.id,
                medicines: prescriptionData.medicines.map((med, idx) => ({
                    name: med.name,
                    slot: idx,
                    totalQuantity: med.totalQuantity || 1
                }))
            })
        });

        const data = await response.json();
        if (!data.success) {
            showError('Dispense Error', data.error || 'Failed to start dispensing.');
        }
    } catch (error) {
        console.error('Dispense error:', error);
        showError('Connection Error', 'Could not communicate with the dispenser.');
    }
}

async function startManualDispense() {
    if (!selectedMedicine) return;

    const qty = parseInt(document.getElementById('qty-value').value) || quantityLimits.min;

    navigateTo('dispensing');

    try {
        const response = await fetch('/api/dispense/manual', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                medicine_name: selectedMedicine.name,
                quantity: qty,
                slot: selectedMedicine.slot || 0
            })
        });

        const data = await response.json();
        if (!data.success) {
            showError('Dispense Error', data.error || 'Failed to start dispensing.');
        }
    } catch (error) {
        console.error('Manual dispense error:', error);
        showError('Connection Error', 'Could not communicate with the dispenser.');
    }
}

function startPollingDispenseStatus() {
    updateDispenseUI({
        current_medicine: 'Preparing...',
        total_progress: 0,
        message: 'Starting dispensing process...'
    });

    dispensePoller = setInterval(async () => {
        try {
            const response = await fetch('/api/dispense/status');
            const status = await response.json();
            updateDispenseUI(status);

            if (!status.active && status.total_progress >= 100) {
                clearInterval(dispensePoller);
                dispensePoller = null;
                // Brief delay before showing complete screen
                setTimeout(() => {
                    navigateTo('complete');
                }, 1500);
            }
        } catch (error) {
            console.error('Status poll error:', error);
        }
    }, 500);
}

function updateDispenseUI(status) {
    const medEl = document.getElementById('dispense-current-med');
    const percentEl = document.getElementById('dispense-percent');
    const progressBar = document.getElementById('dispense-progress-bar');
    const detailEl = document.getElementById('dispense-detail');

    if (medEl) medEl.textContent = status.current_medicine || 'Processing...';
    if (percentEl) percentEl.textContent = (status.total_progress || 0) + '%';
    if (progressBar) progressBar.style.width = (status.total_progress || 0) + '%';
    if (detailEl) detailEl.textContent = status.message || '';
}


// ==========================================
// COMPLETE SCREEN & COUNTDOWN
// ==========================================

function startCountdown() {
    let seconds = 10;
    const numberEl = document.getElementById('countdown-number');
    const textEl = document.getElementById('countdown-text');
    const circleEl = document.getElementById('countdown-circle');
    const circumference = 2 * Math.PI * 18; // r=18

    if (circleEl) {
        circleEl.style.strokeDasharray = circumference;
        circleEl.style.strokeDashoffset = 0;
    }

    const updateCountdown = () => {
        if (numberEl) numberEl.textContent = seconds;
        if (textEl) textEl.textContent = seconds;
        if (circleEl) {
            const offset = circumference * (1 - seconds / 10);
            circleEl.style.strokeDashoffset = offset;
        }
    };

    updateCountdown();

    countdownTimer = setInterval(() => {
        seconds--;
        if (seconds <= 0) {
            clearInterval(countdownTimer);
            returnHome();
        } else {
            updateCountdown();
        }
    }, 1000);
}


// ==========================================
// ERROR HANDLING
// ==========================================

function showError(title, message) {
    document.getElementById('error-title').textContent = title;
    document.getElementById('error-message').textContent = message;
    document.getElementById('error-overlay').classList.remove('hidden');
}

function dismissError() {
    document.getElementById('error-overlay').classList.add('hidden');
}


// ==========================================
// INITIALIZATION
// ==========================================

document.addEventListener('DOMContentLoaded', () => {
    console.log('💊 SMD Kiosk initialized');

    // Prevent context menu on touch devices
    document.addEventListener('contextmenu', e => e.preventDefault());

    // Handle Enter key on manual barcode input
    const manualInput = document.getElementById('manual-barcode-input');
    if (manualInput) {
        manualInput.addEventListener('keydown', (e) => {
            if (e.key === 'Enter') {
                e.preventDefault();
                submitManualBarcode();
            }
        });
    }

    // Keep focus on scan screen
    document.addEventListener('click', () => {
        if (currentScreen === 'scan') {
            const hiddenInput = document.getElementById('barcode-input');
            if (hiddenInput && document.activeElement !== document.getElementById('manual-barcode-input')) {
                hiddenInput.focus();
            }
        }
    });
});
