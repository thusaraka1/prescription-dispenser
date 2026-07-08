// ==========================================
// Firebase Configuration & State
// ==========================================
const FIREBASE_URL = 'https://doctor-438b7-default-rtdb.asia-southeast1.firebasedatabase.app';

let medicinesDB = [];
let prescriptionsDB = [];
let currentPrescription = {
    medicines: []
};

// ==========================================
// DOM Elements
// ==========================================
document.addEventListener('DOMContentLoaded', () => {
    
    // Navigation
    const navLinks = document.querySelectorAll('.nav-links li');
    const sections = document.querySelectorAll('.content-section');
    const pageTitle = document.getElementById('current-page-title');

    // Medicine DB Elements
    const addMedicineForm = document.getElementById('add-medicine-form');
    const medicineTableBody = document.getElementById('medicine-table-body');
    const totalMedsBadge = document.getElementById('total-meds');

    // New Prescription Elements
    const patientForm = document.getElementById('patient-form');
    const medicineSearchInput = document.getElementById('medicine-search');
    const searchResults = document.getElementById('search-results');
    const selectedMedicinesList = document.getElementById('selected-medicines-list');
    const issuePrescriptionBtn = document.getElementById('issue-prescription-btn');

    // Modal Elements
    const prescriptionModal = document.getElementById('prescription-modal');
    const closeModalBtn = document.getElementById('close-modal');
    const printBtn = document.getElementById('print-btn');
    const newPrescBtn = document.getElementById('new-presc-btn');

    // History Elements
    const historyTableBody = document.getElementById('history-table-body');
    const historySearchInput = document.getElementById('history-search-input');
    const viewPrescriptionModal = document.getElementById('view-prescription-modal');
    const closeViewModalBtn = document.getElementById('close-view-modal');
    
    // View Modal Elements
    const viewStatusBadge = document.getElementById('view-status-badge');
    const viewPatientName = document.getElementById('view-patient-name');
    const viewPatientPhone = document.getElementById('view-patient-phone');
    const viewDate = document.getElementById('view-date');
    const viewSessionId = document.getElementById('view-session-id');
    const viewMedicinesList = document.getElementById('view-medicines-list');
    const viewMarkDispersedBtn = document.getElementById('view-mark-dispersed-btn');

    // ==========================================
    // Initialization
    // ==========================================
    fetchMedicines(); // Fetch from Firebase on load
    fetchPrescriptions(); // Fetch history
    setupNavigation();

    // ==========================================
    // Navigation Logic
    // ==========================================
    function setupNavigation() {
        navLinks.forEach(link => {
            link.addEventListener('click', (e) => {
                e.preventDefault();
                navLinks.forEach(l => l.classList.remove('active'));
                sections.forEach(s => s.classList.remove('active'));
                link.classList.add('active');
                
                const targetId = link.getAttribute('data-tab');
                document.getElementById(targetId).classList.add('active');
                pageTitle.textContent = link.querySelector('.link-name').textContent;
                
                if (targetId === 'dispense-prescription') {
                    fetchPrescriptions();
                }
            });
        });
    }

    // ==========================================
    // Medicine DB Logic (Firebase)
    // ==========================================
    async function fetchMedicines() {
        medicineTableBody.innerHTML = `<tr><td colspan="4" style="text-align:center;">Loading from Firebase...</td></tr>`;
        try {
            const response = await fetch(`${FIREBASE_URL}/medicines.json`);
            const data = await response.json();
            
            medicinesDB = [];
            if (data) {
                // Convert Firebase object to array and inject the key as id
                for (let key in data) {
                    medicinesDB.push({
                        id: key,
                        ...data[key]
                    });
                }
            }
            renderMedicineTable();
        } catch (error) {
            console.error('Error fetching medicines:', error);
            medicineTableBody.innerHTML = `<tr><td colspan="4" style="text-align:center; color: var(--danger-color);">Failed to load database.</td></tr>`;
        }
    }

    function renderMedicineTable() {
        medicineTableBody.innerHTML = '';
        
        if(medicinesDB.length === 0) {
            medicineTableBody.innerHTML = `<tr><td colspan="4" style="text-align:center; color: var(--text-muted);">No medicines found in Firebase. Add one above.</td></tr>`;
        }

        medicinesDB.forEach(med => {
            const tr = document.createElement('tr');
            tr.innerHTML = `
                <td><strong>${med.name}</strong></td>
                <td>${med.dosage || '-'}</td>
                <td><span class="type-badge">${med.type}</span></td>
                <td>
                    <button class="icon-btn delete" onclick="deleteMedicine('${med.id}')" title="Delete from Firebase">
                        <i class='bx bx-trash'></i>
                    </button>
                </td>
            `;
            medicineTableBody.appendChild(tr);
        });

        totalMedsBadge.textContent = `${medicinesDB.length} Items`;
    }

    // Delete from Firebase
    window.deleteMedicine = async function(id) {
        if(confirm('Are you sure you want to delete this medicine from the live database?')) {
            try {
                await fetch(`${FIREBASE_URL}/medicines/${id}.json`, {
                    method: 'DELETE'
                });
                await fetchMedicines(); // Refresh list
            } catch (error) {
                console.error("Error deleting:", error);
            }
        }
    };

    // Add to Firebase
    addMedicineForm.addEventListener('submit', async (e) => {
        e.preventDefault();
        const submitBtn = addMedicineForm.querySelector('button[type="submit"]');
        submitBtn.innerHTML = "<i class='bx bx-loader-alt bx-spin'></i> Adding...";
        submitBtn.disabled = true;

        const newMed = {
            name: document.getElementById('med-name').value,
            dosage: document.getElementById('med-dosage').value,
            type: document.getElementById('med-type').value
        };

        try {
            await fetch(`${FIREBASE_URL}/medicines.json`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(newMed)
            });
            
            addMedicineForm.reset();
            await fetchMedicines();
        } catch (error) {
            console.error("Error adding medicine:", error);
            alert("Failed to add medicine to Firebase.");
        } finally {
            submitBtn.innerHTML = "<i class='bx bx-plus'></i> Add to Database";
            submitBtn.disabled = false;
        }
    });

    // ==========================================
    // Prescription Logic - Searching & Adding
    // ==========================================
    medicineSearchInput.addEventListener('input', (e) => {
        const query = e.target.value.toLowerCase().trim();
        searchResults.innerHTML = '';

        if (query.length < 2) {
            searchResults.classList.add('hidden');
            return;
        }

        const filtered = medicinesDB.filter(m => m.name.toLowerCase().includes(query));

        if (filtered.length > 0) {
            searchResults.classList.remove('hidden');
            filtered.forEach(med => {
                const div = document.createElement('div');
                div.className = 'search-item';
                div.innerHTML = `
                    <div class="med-info">
                        <strong>${med.name}</strong>
                        <small>${med.dosage} • ${med.type}</small>
                    </div>
                    <button class="add-btn">Add</button>
                `;
                
                div.addEventListener('click', () => {
                    addMedicineToPrescription(med);
                    searchResults.classList.add('hidden');
                    medicineSearchInput.value = '';
                });

                searchResults.appendChild(div);
            });
        } else {
            searchResults.classList.remove('hidden');
            searchResults.innerHTML = `<div class="search-item" style="color:var(--text-muted); justify-content:center;">No matches found</div>`;
        }
    });

    document.addEventListener('click', (e) => {
        if (!e.target.closest('.search-container')) {
            searchResults.classList.add('hidden');
        }
    });

    function addMedicineToPrescription(med) {
        if (currentPrescription.medicines.find(m => m.id === med.id)) {
            alert('Medicine already added!');
            return;
        }
        // Clone the medicine object and set defaults for calculation
        const medCopy = { ...med, dose: 1, frequency: 3, duration: 5, totalQuantity: 15 };
        currentPrescription.medicines.push(medCopy);
        renderSelectedMedicines();
    }

    window.removePrescMed = function(id) {
        currentPrescription.medicines = currentPrescription.medicines.filter(m => m.id !== id);
        renderSelectedMedicines();
    };

    function renderSelectedMedicines() {
        selectedMedicinesList.innerHTML = '';
        
        if (currentPrescription.medicines.length === 0) {
            selectedMedicinesList.innerHTML = `
                <li class="empty-state">
                    <i class='bx bx-basket'></i>
                    <p>No medicines selected yet. Search above to add.</p>
                </li>
            `;
            return;
        }

        currentPrescription.medicines.forEach(med => {
            const li = document.createElement('li');
            li.className = 'medicine-item';
            li.style.flexDirection = 'column';
            li.style.alignItems = 'stretch';
            li.innerHTML = `
                <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 8px;">
                    <div class="item-details">
                        <strong>${med.name}</strong>
                        <small>${med.dosage} • ${med.type}</small>
                    </div>
                    <button class="icon-btn delete" onclick="removePrescMed('${med.id}')" type="button">
                        <i class='bx bx-x'></i>
                    </button>
                </div>
                <div class="dosage-calculator">
                    <div class="calc-inputs">
                        <div class="input-group calc-group">
                            <label>Units/Time</label>
                            <input type="number" min="1" class="calc-dose" data-id="${med.id}" value="${med.dose}" onchange="updateMedCalc('${med.id}')">
                        </div>
                        <div class="input-group calc-group">
                            <label>Times/Day</label>
                            <input type="number" min="1" class="calc-freq" data-id="${med.id}" value="${med.frequency}" onchange="updateMedCalc('${med.id}')">
                        </div>
                        <div class="input-group calc-group">
                            <label>Days</label>
                            <input type="number" min="1" class="calc-days" data-id="${med.id}" value="${med.duration}" onchange="updateMedCalc('${med.id}')">
                        </div>
                    </div>
                    <div class="calc-total">
                        <div class="total-label">Total Dispense</div>
                        <div class="total-value"><span id="total-${med.id}">${med.totalQuantity}</span></div>
                    </div>
                </div>
            `;
            selectedMedicinesList.appendChild(li);
        });
    }

    window.updateMedCalc = function(id) {
        const med = currentPrescription.medicines.find(m => m.id === id);
        if (!med) return;
        
        const listItem = document.querySelector(`.calc-dose[data-id="${id}"]`).closest('.medicine-item');
        const dose = parseInt(listItem.querySelector('.calc-dose').value) || 1;
        const freq = parseInt(listItem.querySelector('.calc-freq').value) || 1;
        const days = parseInt(listItem.querySelector('.calc-days').value) || 1;
        
        const total = dose * freq * days;
        listItem.querySelector(`#total-${id}`).textContent = total;
        
        med.dose = dose;
        med.frequency = freq;
        med.duration = days;
        med.totalQuantity = total;
    };

    // ==========================================
    // Issuing Prescription to Firebase
    // ==========================================
    issuePrescriptionBtn.addEventListener('click', async () => {
        const nameInput = document.getElementById('patient-name');
        const phoneInput = document.getElementById('patient-phone');
        const hometownInput = document.getElementById('patient-hometown');

        if (!nameInput.checkValidity() || !phoneInput.checkValidity()) {
            patientForm.reportValidity();
            return;
        }

        if (currentPrescription.medicines.length === 0) {
            alert('Please add at least one medicine to the prescription.');
            return;
        }

        // Capture calculation inputs
        const doseInputs = document.querySelectorAll('.calc-dose');
        doseInputs.forEach(input => {
            const id = input.getAttribute('data-id');
            const med = currentPrescription.medicines.find(m => m.id === id);
            if (med) {
                const listItem = input.closest('.medicine-item');
                med.dose = parseInt(listItem.querySelector('.calc-dose').value) || 1;
                med.frequency = parseInt(listItem.querySelector('.calc-freq').value) || 1;
                med.duration = parseInt(listItem.querySelector('.calc-days').value) || 1;
                med.totalQuantity = med.dose * med.frequency * med.duration;
            }
        });

        issuePrescriptionBtn.disabled = true;
        issuePrescriptionBtn.innerHTML = "<i class='bx bx-loader-alt bx-spin'></i> Issuing...";

        const sessionId = 'RX-' + Math.floor(100000 + Math.random() * 900000);
        const dateStr = new Date().toLocaleDateString('en-US', { year: 'numeric', month: 'short', day: 'numeric', hour: '2-digit', minute: '2-digit' });

        const newPrescription = {
            id: sessionId,
            patientName: nameInput.value,
            phone: phoneInput.value,
            hometown: hometownInput.value || '-',
            date: dateStr,
            medicines: [...currentPrescription.medicines],
            status: 'Pending'
        };

        try {
            // Save to Firebase using PUT to use the sessionId as the exact key in the DB
            await fetch(`${FIREBASE_URL}/prescriptions/${sessionId}.json`, {
                method: 'PUT',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(newPrescription)
            });

            // Generate a unique token for the barcode link
            const barcodeToken = Array.from(crypto.getRandomValues(new Uint8Array(16)))
                .map(b => b.toString(16).padStart(2, '0')).join('');

            // Save the token to Firebase
            await fetch(`${FIREBASE_URL}/barcode-tokens/${barcodeToken}.json`, {
                method: 'PUT',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    prescriptionId: sessionId,
                    createdAt: new Date().toISOString()
                })
            });

            // Build the barcode link
            const barcodeLink = `${window.location.origin}/barcode.html?token=${barcodeToken}`;
            console.log('🔗 [Barcode Link] Generated:', barcodeLink);

            // Send SMS via local proxy (to bypass CORS)
            if (phoneInput.value) {
                console.log('📱 [SMS] Step 1: Phone number detected:', phoneInput.value);
                try {
                    // Format phone number to Sri Lankan international format
                    let formattedPhone = phoneInput.value.replace(/[^0-9]/g, '');
                    if (formattedPhone.startsWith('0')) {
                        formattedPhone = '94' + formattedPhone.substring(1);
                    }
                    console.log('📱 [SMS] Step 2: Formatted phone:', formattedPhone);

                    // Build SMS message with barcode link
                    const smsMessage = `Hi ${nameInput.value}, your prescription (${sessionId}) is ready. Open this link to get your barcode: ${barcodeLink}`;
                    console.log('📱 [SMS] Step 3: Message built:', smsMessage);

                    const smsPayload = {
                        recipient: formattedPhone,
                        sender_id: "TextLKDemo",
                        type: "plain",
                        message: smsMessage
                    };
                    console.log('📱 [SMS] Step 4: Sending payload to /api/send-sms proxy...', smsPayload);
                    
                    const smsRes = await fetch('/api/send-sms', {
                        method: 'POST',
                        headers: { 'Content-Type': 'application/json' },
                        body: JSON.stringify(smsPayload)
                    });

                    console.log('📱 [SMS] Step 5: Got response, status code:', smsRes.status);
                    const smsData = await smsRes.json();
                    console.log('📱 [SMS] Step 6: Response body:', JSON.stringify(smsData, null, 2));

                    if (smsData.status === 'success') {
                        console.log('📱 [SMS] ✅ SMS SENT SUCCESSFULLY!');
                    } else {
                        console.error('📱 [SMS] ❌ API Error:', smsData);
                        alert('SMS Error: ' + (smsData.message || JSON.stringify(smsData)));
                    }
                } catch (smsError) {
                    console.error('📱 [SMS] ❌ FETCH FAILED:', smsError.name, smsError.message);
                    alert('SMS could not be sent. Make sure you are running the app via: node server.js → http://localhost:3000');
                }
            } else {
                console.log('📱 [SMS] Skipped — no phone number entered.');
            }

            // Populate Modal
            document.getElementById('res-patient-name').textContent = nameInput.value;
            document.getElementById('res-patient-phone').textContent = phoneInput.value;
            document.getElementById('res-patient-hometown').textContent = hometownInput.value || '-';
            document.getElementById('res-date').textContent = dateStr;

            const resList = document.getElementById('res-medicines-list');
            resList.innerHTML = '';
            currentPrescription.medicines.forEach(med => {
                const li = document.createElement('li');
                li.style.marginBottom = "12px";
                li.innerHTML = `
                    <strong>${med.name}</strong> - ${med.dosage} (${med.type})<br>
                    <small style="color: var(--text-muted);">Take ${med.dose} units, ${med.frequency} times a day, for ${med.duration} days.</small><br>
                    <span class="badge" style="margin-top: 6px; display: inline-block;">Total to Dispense: ${med.totalQuantity}</span>
                `;
                resList.appendChild(li);
            });

            prescriptionModal.classList.remove('hidden');

            try {
                JsBarcode("#barcode", sessionId, {
                    format: "CODE128",
                    lineColor: "#000",
                    width: 2,
                    height: 50,
                    displayValue: true,
                    fontSize: 14,
                    margin: 0
                });
            } catch (e) {
                console.error("Barcode error:", e);
            }
        } catch (error) {
            console.error("Error saving prescription:", error);
            alert("Failed to issue prescription to Firebase.");
        } finally {
            issuePrescriptionBtn.disabled = false;
            issuePrescriptionBtn.innerHTML = "<i class='bx bx-check-circle'></i> Issue Prescription";
        }
    });

    // ==========================================
    // Modal Actions
    // ==========================================
    function resetPrescriptionForm() {
        patientForm.reset();
        currentPrescription.medicines = [];
        renderSelectedMedicines();
        prescriptionModal.classList.add('hidden');
    }

    closeModalBtn.addEventListener('click', () => {
        prescriptionModal.classList.add('hidden');
    });
    newPrescBtn.addEventListener('click', resetPrescriptionForm);
    printBtn.addEventListener('click', () => window.print());

    // ==========================================
    // Prescription History & View (Firebase)
    // ==========================================
    async function fetchPrescriptions() {
        if (!historyTableBody) return;
        historyTableBody.innerHTML = `<tr><td colspan="6" style="text-align:center;">Loading from Firebase...</td></tr>`;
        try {
            const response = await fetch(`${FIREBASE_URL}/prescriptions.json`);
            const data = await response.json();
            
            prescriptionsDB = [];
            if (data) {
                for (let key in data) {
                    prescriptionsDB.push({
                        id: key,
                        ...data[key]
                    });
                }
            }
            // Reverse so newest are first
            prescriptionsDB.reverse();
            renderPrescriptionHistory();
        } catch (error) {
            console.error('Error fetching prescriptions:', error);
            historyTableBody.innerHTML = `<tr><td colspan="6" style="text-align:center; color: var(--danger-color);">Failed to load history.</td></tr>`;
        }
    }

    function renderPrescriptionHistory(query = '') {
        historyTableBody.innerHTML = '';
        
        let filtered = prescriptionsDB;
        if (query) {
            query = query.toLowerCase();
            filtered = prescriptionsDB.filter(p => 
                (p.id && p.id.toLowerCase().includes(query)) ||
                (p.patientName && p.patientName.toLowerCase().includes(query)) ||
                (p.phone && p.phone.toLowerCase().includes(query))
            );
        }

        if(filtered.length === 0) {
            historyTableBody.innerHTML = `<tr><td colspan="6" style="text-align:center; color: var(--text-muted);">No prescriptions found.</td></tr>`;
            return;
        }

        filtered.forEach(p => {
            const tr = document.createElement('tr');
            tr.innerHTML = `
                <td data-label="Barcode ID"><strong>${p.id}</strong></td>
                <td data-label="Patient">${p.patientName}</td>
                <td data-label="Phone">${p.phone || '-'}</td>
                <td data-label="Date">${p.date}</td>
                <td data-label="Status"><span class="badge ${p.status ? p.status.toLowerCase() : 'pending'}">${p.status || 'Pending'}</span></td>
                <td data-label="Action">
                    <button class="secondary-btn" onclick="openViewModal('${p.id}')" style="padding: 4px 12px; font-size: 12px;">View</button>
                    <button class="icon-btn delete" onclick="deletePrescription('${p.id}')" title="Delete Prescription" style="margin-left: 8px;">
                        <i class='bx bx-trash'></i>
                    </button>
                </td>
            `;
            historyTableBody.appendChild(tr);
        });
    }

    historySearchInput.addEventListener('input', (e) => {
        renderPrescriptionHistory(e.target.value);
    });

    window.deletePrescription = async function(id) {
        if(confirm('Are you sure you want to delete this prescription from the live database? This action cannot be undone.')) {
            try {
                await fetch(`${FIREBASE_URL}/prescriptions/${id}.json`, {
                    method: 'DELETE'
                });
                await fetchPrescriptions(); // Refresh list
            } catch (error) {
                console.error("Error deleting prescription:", error);
                alert("Failed to delete prescription from Firebase.");
            }
        }
    };

    let currentlyViewingPrescriptionId = null;

    window.openViewModal = function(id) {
        const found = prescriptionsDB.find(p => p.id === id);
        if (!found) return;

        currentlyViewingPrescriptionId = found.id;
        
        viewPatientName.textContent = found.patientName;
        viewPatientPhone.textContent = found.phone || '-';
        viewDate.textContent = found.date;
        viewSessionId.textContent = found.id;
        
        const status = found.status || 'Pending';
        viewStatusBadge.className = 'badge ' + status.toLowerCase();
        viewStatusBadge.textContent = status;

        if (status === 'Dispersed') {
            viewMarkDispersedBtn.disabled = true;
            viewMarkDispersedBtn.style.opacity = '0.5';
            viewMarkDispersedBtn.style.cursor = 'not-allowed';
            viewMarkDispersedBtn.innerHTML = "<i class='bx bx-check-double'></i> Already Dispersed";
        } else {
            viewMarkDispersedBtn.disabled = false;
            viewMarkDispersedBtn.style.opacity = '1';
            viewMarkDispersedBtn.style.cursor = 'pointer';
            viewMarkDispersedBtn.innerHTML = "<i class='bx bx-check-circle'></i> Mark as Dispersed";
        }

        viewMedicinesList.innerHTML = '';
        if (found.medicines) {
            found.medicines.forEach(med => {
                const li = document.createElement('li');
                li.style.marginBottom = "16px";
                li.style.paddingBottom = "12px";
                li.style.borderBottom = "1px solid rgba(255,255,255,0.05)";
                li.innerHTML = `
                    <div style="display: flex; justify-content: space-between; align-items: flex-start;">
                        <div>
                            <strong>${med.name}</strong> - ${med.dosage} (${med.type})<br>
                            <small style="color: #cbd5e1; display: block; margin-top: 4px;">
                                Take ${med.dose} units, ${med.frequency} times a day, for ${med.duration} days.
                            </small>
                        </div>
                        <div style="text-align: right; background: rgba(14, 165, 233, 0.1); padding: 8px 12px; border-radius: 8px; border: 1px solid rgba(14, 165, 233, 0.2);">
                            <div style="font-size: 11px; color: var(--primary-color); text-transform: uppercase; font-weight: 600;">Dispense Amount</div>
                            <div style="font-size: 24px; font-weight: 700; color: white;">${med.totalQuantity || '0'}</div>
                        </div>
                    </div>
                `;
                viewMedicinesList.appendChild(li);
            });
        }

        viewPrescriptionModal.classList.remove('hidden');
    };

    closeViewModalBtn.addEventListener('click', () => {
        viewPrescriptionModal.classList.add('hidden');
    });

    viewMarkDispersedBtn.addEventListener('click', async () => {
        if (!currentlyViewingPrescriptionId) return;
        
        viewMarkDispersedBtn.disabled = true;
        viewMarkDispersedBtn.innerHTML = "<i class='bx bx-loader-alt bx-spin'></i> Updating...";

        try {
            await fetch(`${FIREBASE_URL}/prescriptions/${currentlyViewingPrescriptionId}.json`, {
                method: 'PATCH',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ status: 'Dispersed' })
            });

            // Update UI modal
            viewStatusBadge.className = 'badge dispersed';
            viewStatusBadge.textContent = 'Dispersed';
            
            viewMarkDispersedBtn.disabled = true;
            viewMarkDispersedBtn.style.opacity = '0.5';
            viewMarkDispersedBtn.style.cursor = 'not-allowed';
            viewMarkDispersedBtn.innerHTML = "<i class='bx bx-check-double'></i> Already Dispersed";
            
            // Refresh table data in background to stay in sync
            await fetchPrescriptions();
            
        } catch (error) {
            console.error("Error updating status:", error);
            alert("Failed to update status in Firebase.");
            viewMarkDispersedBtn.disabled = false;
            viewMarkDispersedBtn.innerHTML = "<i class='bx bx-check-circle'></i> Mark as Dispersed";
        }
    });
});
