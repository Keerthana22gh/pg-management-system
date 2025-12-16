// Navigation
function showSection(sectionId) {
    document.querySelectorAll('.section').forEach(sec => sec.classList.remove('active'));
    document.getElementById(sectionId).classList.add('active');
}

function toggleModal(modalId) {
    const modal = document.getElementById(modalId);
    modal.style.display = modal.style.display === "block" ? "none" : "block";
}

// Window click to close modal
window.onclick = function (event) {
    if (event.target.classList.contains('modal')) {
        event.target.style.display = "none";
    }
}

// ---------------- ADMIN FUNCTIONS ----------------

async function loadTenants() {
    const tbody = document.getElementById('tenantTableBody');
    if (!tbody) return;

    try {
        const res = await fetch('/api/admin/tenants');
        const tenants = await res.json();
        tbody.innerHTML = tenants.map(t => `
            <tr>
                <td>${t.name}</td>
                <td>${t.rooms ? t.rooms.room_number : 'N/A'}</td>
                <td>${t.phone}</td>
                <td>${t.join_date}</td>
                <td>${t.deposit}</td>
            </tr>
        `).join('');
    } catch (e) { console.error(e); }
}

async function loadRoomsForSelect() {
    const select = document.getElementById('roomSelect');
    if (!select) return;

    try {
        const res = await fetch('/api/admin/rooms');
        const rooms = await res.json();
        const available = rooms.filter(r => !r.occupied);
        select.innerHTML += available.map(r => `<option value="${r.id}">${r.room_number} (Floor ${r.floor})</option>`).join('');
    } catch (e) { console.error(e); }
}

// Add Tenant Form
const addTenantForm = document.getElementById('addTenantForm');
if (addTenantForm) {
    addTenantForm.addEventListener('submit', async (e) => {
        e.preventDefault();
        const formData = new FormData(addTenantForm);
        const data = Object.fromEntries(formData);

        try {
            const res = await fetch('/api/admin/tenants', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(data)
            });
            if (res.ok) {
                alert('Tenant added successfully');
                toggleModal('addTenantModal');
                loadTenants();
                addTenantForm.reset();
            } else {
                alert('Error adding tenant');
            }
        } catch (e) { console.error(e); }
    });
}

// Admin Loaders for other sections (simplified for hackathon)
document.addEventListener('DOMContentLoaded', () => {
    // Admin specific loaders
    if (document.getElementById('paymentTableBody')) loadAdminPayments();
    if (document.getElementById('maintenanceTableBodyAdmin')) loadAdminMaintenance();
    if (document.getElementById('vacateTableBodyAdmin')) loadAdminVacate();
});

async function loadAdminPayments(month = '') {
    try {
        let url = '/api/admin/payments';
        if (month) {
            url += `?month=${month}`;
        }
        const res = await fetch(url);
        const payments = await res.json();
        const tbody = document.getElementById('paymentTableBody');
        if (tbody) {
            if (payments.length === 0) {
                tbody.innerHTML = '<tr><td colspan="6" style="text-align:center;">No payments found for this period</td></tr>';
            } else {
                tbody.innerHTML = payments.map(p => `
                    <tr>
                        <td>${p.month}</td>
                        <td>${p.tenants.name}</td>
                        <td>${p.tenants.rooms ? p.tenants.rooms.room_number : '-'}</td>
                        <td>${p.amount}</td>
                        <td>${p.proof_url ? `<a href="${p.proof_url}" target="_blank" class="btn-primary" style="padding: 4px 10px; font-size: 0.8rem; text-decoration: none;">View</a>` : 'None'}</td>
                        <td>${p.status}</td>
                    </tr>
                `).join('');
            }
        }
    } catch (e) { console.error(e); }
}

async function loadAdminMaintenance() {
    try {
        const res = await fetch('/api/admin/maintenance');
        const requests = await res.json();
        const tbody = document.getElementById('maintenanceTableBodyAdmin');
        tbody.innerHTML = requests.map(r => `
            <tr>
                <td>${new Date(r.created_at).toLocaleDateString()}</td>
                <td>${r.tenants.name}</td>
                <td>${r.tenants.rooms ? r.tenants.rooms.room_number : '-'}</td>
                <td>${r.title}</td>
                <td>${r.status}</td>
                <td>
                    ${r.status === 'pending' ? `<button onclick="updateMaintenance('${r.id}', 'completed')">Mark Complete</button>` : 'Completed'}
                </td>
            </tr>
        `).join('');
    } catch (e) { console.error(e); }
}

async function updateMaintenance(id, status) {
    await fetch('/api/admin/maintenance', {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ id, status })
    });
    loadAdminMaintenance();
}

async function loadAdminVacate() {
    try {
        const res = await fetch('/api/admin/vacate');
        const requests = await res.json();
        const tbody = document.getElementById('vacateTableBodyAdmin');
        tbody.innerHTML = requests.map(r => `
            <tr>
                <td>${r.vacate_date}</td>
                <td>${r.tenants.name}</td>
                <td>${r.reason}</td>
                <td>${r.dues}</td>
                <td>${r.status}</td>
                <td>
                    ${r.status === 'pending' ? `<button onclick="completeVacate('${r.id}')">Process</button>` : 'Processed'}
                </td>
            </tr>
        `).join('');
    } catch (e) { console.error(e); }
}

async function completeVacate(id) {
    if (confirm('Are you sure you want to process this vacate request?')) {
        await fetch('/api/admin/vacate', {
            method: 'PUT',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ id, status: 'completed' })
        });
        loadAdminVacate();
    }
}


// ---------------- TENANT FUNCTIONS ----------------

async function loadTenantProfile() {
    const card = document.getElementById('profileCard');
    if (!card) return;

    try {
        const res = await fetch('/api/tenant/profile');
        const t = await res.json();
        card.innerHTML = `
            <h3>${t.name}</h3>
            <p><strong>Room:</strong> ${t.rooms ? t.rooms.room_number : 'Unassigned'}</p>
            <p><strong>Phone:</strong> ${t.phone}</p>
            <p><strong>Email:</strong> ${t.email}</p>
            <p><strong>Deposit:</strong> ${t.deposit}</p>
            <p><strong>Joined:</strong> ${t.join_date}</p>
        `;
    } catch (e) { console.error(e); }
}

async function loadTenantPayments() {
    const tbody = document.getElementById('tenantPaymentTableBody');
    if (!tbody) return;

    try {
        const res = await fetch('/api/tenant/payments');
        const payments = await res.json();
        tbody.innerHTML = payments.map(p => `
            <tr>
                <td>${p.month}</td>
                <td>${p.amount}</td>
                <td>${p.paid_date}</td>
                <td>${p.status}</td>
            </tr>
        `).join('');
    } catch (e) { console.error(e); }
}

const uploadPaymentForm = document.getElementById('uploadPaymentForm');
if (uploadPaymentForm) {
    uploadPaymentForm.addEventListener('submit', async (e) => {
        e.preventDefault();
        const formData = new FormData(uploadPaymentForm);

        try {
            const res = await fetch('/api/tenant/payments', {
                method: 'POST',
                body: formData // Fetch handles multipart automatic
            });
            const result = await res.json();
            if (result.error) {
                alert('Error: ' + result.error);
            } else {
                alert('Payment proof uploaded!');
                loadTenantPayments();
                uploadPaymentForm.reset();
            }
        } catch (e) { console.error(e); }
    });
}

// Maintenance
async function loadTenantMaintenance() {
    const tbody = document.getElementById('tenantMaintenanceTableBody');
    if (!tbody) return;

    try {
        const res = await fetch('/api/tenant/maintenance');
        const requests = await res.json();
        tbody.innerHTML = requests.map(r => `
            <tr>
                <td>${new Date(r.created_at).toLocaleDateString()}</td>
                <td>${r.title}</td>
                <td>${r.status}</td>
            </tr>
        `).join('');
    } catch (e) { console.error(e); }
}

const maintenanceForm = document.getElementById('maintenanceForm');
if (maintenanceForm) {
    maintenanceForm.addEventListener('submit', async (e) => {
        e.preventDefault();
        const formData = new FormData(maintenanceForm);
        try {
            const res = await fetch('/api/tenant/maintenance', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(Object.fromEntries(formData))
            });
            if (res.ok) {
                alert('Request submitted');
                loadTenantMaintenance();
                maintenanceForm.reset();
            }
        } catch (e) { console.error(e); }
    });
}

// Vacate
async function loadTenantVacateStatus() {
    const formContainer = document.getElementById('vacateFormContainer');
    const statusContainer = document.getElementById('existingVacateRequest');
    if (!formContainer) return;

    try {
        const res = await fetch('/api/tenant/vacate');
        const requests = await res.json();
        const activeRequest = requests.find(r => r.status === 'pending');

        if (activeRequest) {
            formContainer.style.display = 'none';
            statusContainer.style.display = 'block';
            document.getElementById('vacateStatus').innerText = activeRequest.status;
        }
    } catch (e) { console.error(e); }
}

const vacateForm = document.getElementById('vacateForm');
if (vacateForm) {
    vacateForm.addEventListener('submit', async (e) => {
        e.preventDefault();
        if (!confirm("Are you sure you want to vacate? This action is irreversible.")) return;

        const formData = new FormData(vacateForm);
        try {
            const res = await fetch('/api/tenant/vacate', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(Object.fromEntries(formData))
            });
            if (res.ok) {
                alert('Vacate request submitted');
                loadTenantVacateStatus();
            }
        } catch (e) { console.error(e); }
    });
}
