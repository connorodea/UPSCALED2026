const statusEls = {
  batchNumber: document.getElementById('batchNumber'),
  batchId: document.getElementById('batchId'),
  itemsRemaining: document.getElementById('itemsRemaining'),
  location: document.getElementById('location')
};

const manifestForm = document.getElementById('manifestForm');
const manifestResponse = document.getElementById('manifestResponse');
const productForm = document.getElementById('productForm');
const productResponse = document.getElementById('productResponse');
const inventoryTable = document.getElementById('inventoryTable');
const batchList = document.getElementById('batchList');
const batchNumberInput = document.getElementById('batchNumberInput');
const refreshStatus = document.getElementById('refreshStatus');
const buildHub = document.getElementById('buildHub');
const exportBatch = document.getElementById('exportBatch');
const openUnprocessed = document.getElementById('openUnprocessed');
const openProcessed = document.getElementById('openProcessed');
const hubResponse = document.getElementById('hubResponse');
const loginOverlay = document.getElementById('loginOverlay');
const loginForm = document.getElementById('loginForm');
const loginError = document.getElementById('loginError');
const metricsEls = {
  totalProcessed: document.getElementById('totalProcessed'),
  processedToday: document.getElementById('processedToday'),
  manifestCount: document.getElementById('manifestCount'),
  unprocessedCount: document.getElementById('unprocessedCount')
};
const wizardOverlay = document.getElementById('wizardOverlay');
const wizardTitle = document.getElementById('wizardTitle');
const wizardBody = document.getElementById('wizardBody');
const wizardNext = document.getElementById('wizardNext');
const wizardSkip = document.getElementById('wizardSkip');
const wizardLaunch = document.getElementById('wizardLaunch');
const checklistStatus = document.getElementById('checklistStatus');
const printAgentStatus = document.getElementById('printAgentStatus');

const wizardSteps = [
  {
    title: 'Welcome to Upscaled Ops',
    body: 'This guided setup walks you through the core workflow. You can skip it and come back anytime.'
  },
  {
    title: 'Step 1: Receive the Manifest',
    body: 'Grab the Manifest ID from the auction, enter it here, and set the unit count. This generates PID-UID labels.'
  },
  {
    title: 'Step 2: Apply PID-UID Labels',
    body: 'Place the PID-UID label on each unit as you unload the pallet. This ties every unit to the manifest.'
  },
  {
    title: 'Step 3: Process Items',
    body: 'Enter PID-UID, grade, and optional UPC/manufacturer/model to create SKUs and print the labels.'
  },
  {
    title: 'Step 4: Build the Inventory Hub',
    body: 'Click “Build Inventory Hub” whenever you want refreshed master CSVs for unprocessed and processed inventory.'
  },
  {
    title: 'Step 5: Export Batches',
    body: 'Use Batch Tools to export completed batches for downstream workflows.'
  }
];

let wizardIndex = 0;

function showWizard() {
  wizardIndex = 0;
  wizardOverlay.classList.add('active');
  renderWizard();
}

function renderWizard() {
  const step = wizardSteps[wizardIndex];
  wizardTitle.textContent = step.title;
  wizardBody.textContent = step.body;
  wizardNext.textContent = wizardIndex === wizardSteps.length - 1 ? 'Finish' : 'Next';
}

function advanceWizard() {
  if (wizardIndex < wizardSteps.length - 1) {
    wizardIndex += 1;
    renderWizard();
  } else {
    wizardOverlay.classList.remove('active');
    localStorage.setItem('upscaled_wizard_done', 'true');
  }
}

function skipWizard() {
  wizardOverlay.classList.remove('active');
  localStorage.setItem('upscaled_wizard_done', 'true');
}

function getToken() {
  return localStorage.getItem('upscaled_token');
}

function setToken(token) {
  localStorage.setItem('upscaled_token', token);
}

function clearToken() {
  localStorage.removeItem('upscaled_token');
}

function loadChecklist() {
  const stored = JSON.parse(localStorage.getItem('upscaled_checklist') || '{}');
  document.querySelectorAll('[data-check]').forEach((input) => {
    const key = input.getAttribute('data-check');
    if (stored[key]) {
      input.checked = true;
    }
  });
}

function saveChecklist() {
  const stored = {};
  document.querySelectorAll('[data-check]').forEach((input) => {
    const key = input.getAttribute('data-check');
    stored[key] = input.checked;
  });
  localStorage.setItem('upscaled_checklist', JSON.stringify(stored));
  checklistStatus.textContent = 'Checklist saved.'
  setTimeout(() => {
    checklistStatus.textContent = '';
  }, 1500);
}

async function apiFetch(path, options = {}) {
  const token = getToken();
  const headers = { 'Content-Type': 'application/json', ...(options.headers || {}) };
  if (token) {
    headers.Authorization = `Bearer ${token}`;
  }

  const response = await fetch(path, {
    ...options,
    headers
  });

  if (response.status === 401) {
    clearToken();
    loginOverlay.classList.add('active');
  }

  if (!response.ok) {
    const error = await response.json().catch(() => ({}));
    throw new Error(error.error || 'Request failed');
  }

  return response.json();
}

async function loadStatus() {
  try {
    const status = await apiFetch('/api/status');
    statusEls.batchNumber.textContent = status.batchNumber;
    statusEls.batchId.textContent = status.batchId;
    statusEls.itemsRemaining.textContent = status.itemsRemaining;
    statusEls.location.textContent = status.location;
  } catch {
    statusEls.batchNumber.textContent = '--';
  }
}

async function loadMetrics() {
  try {
    const metrics = await apiFetch('/api/metrics');
    metricsEls.totalProcessed.textContent = metrics.totalProcessed;
    metricsEls.processedToday.textContent = metrics.processedToday;
    metricsEls.manifestCount.textContent = metrics.manifestCount;
    metricsEls.unprocessedCount.textContent = metrics.unprocessedCount;
  } catch {
    // ignore
  }
}

async function loadPrintAgentStatus() {
  if (!printAgentStatus) {
    return;
  }
  try {
    const status = await apiFetch('/api/print-agent/status');
    const label = status.mode === 'proxy' ? 'Proxy' : status.mode === 'local' ? 'Local' : 'Disabled';
    printAgentStatus.textContent = `Print agent: ${label} (${status.status})`;
  } catch {
    printAgentStatus.textContent = 'Print agent: unknown';
  }
}

async function loadInventory() {
  try {
    const data = await apiFetch('/api/inventory');
    const { headers, rows } = data;
    if (!rows.length) {
      inventoryTable.innerHTML = '<p class="response">No inventory rows yet.</p>';
      return;
    }

    const table = document.createElement('table');
    const thead = document.createElement('thead');
    const headRow = document.createElement('tr');
    headers.forEach((header) => {
      const th = document.createElement('th');
      th.textContent = header;
      headRow.appendChild(th);
    });
    thead.appendChild(headRow);

    const tbody = document.createElement('tbody');
    rows.slice(-25).reverse().forEach((row) => {
      const tr = document.createElement('tr');
      headers.forEach((header) => {
        const td = document.createElement('td');
        td.textContent = row[header] || '';
        tr.appendChild(td);
      });
      tbody.appendChild(tr);
    });

    table.appendChild(thead);
    table.appendChild(tbody);
    inventoryTable.innerHTML = '';
    inventoryTable.appendChild(table);
  } catch (error) {
    inventoryTable.innerHTML = `<p class="response">${error.message}</p>`;
  }
}

async function loadBatches() {
  try {
    const data = await apiFetch('/api/batches');
    const list = data.batchFiles.length
      ? data.batchFiles.join(', ')
      : 'No batch exports yet.';
    const locationLabel = data.location ? `${data.location}: ` : '';
    batchList.textContent = `${locationLabel}${list}`;
  } catch (error) {
    batchList.textContent = 'Failed to load batches.';
  }
}

manifestForm.addEventListener('submit', async (event) => {
  event.preventDefault();
  manifestResponse.textContent = '';

  const formData = new FormData(manifestForm);
  const payload = Object.fromEntries(formData.entries());
  payload.printLabels = Boolean(formData.get('printLabels'));

  try {
    const result = await apiFetch('/api/manifest', {
      method: 'POST',
      body: JSON.stringify(payload)
    });
    manifestResponse.textContent = `Manifest ${result.record.manifestId} created with ${result.pidUids.length} PID-UIDs.`;
    await loadStatus();
    await loadMetrics();
  } catch (error) {
    manifestResponse.textContent = error.message;
  }
});

productForm.addEventListener('submit', async (event) => {
  event.preventDefault();
  productResponse.textContent = '';

  const formData = new FormData(productForm);
  const payload = Object.fromEntries(formData.entries());
  payload.printLabel = Boolean(formData.get('printLabel'));

  try {
    const result = await apiFetch('/api/product', {
      method: 'POST',
      body: JSON.stringify(payload)
    });
    productResponse.textContent = `SKU ${result.product.sku} saved. Label: ${result.labelDownload || result.labelPath}`;
    await loadStatus();
    await loadInventory();
    await loadMetrics();
  } catch (error) {
    productResponse.textContent = error.message;
  }
});

refreshStatus.addEventListener('click', async () => {
  await loadStatus();
  await loadInventory();
  await loadBatches();
  await loadMetrics();
  await loadPrintAgentStatus();
});

buildHub.addEventListener('click', async () => {
  hubResponse.textContent = '';
  try {
    await apiFetch('/api/hub/build', { method: 'POST' });
    hubResponse.textContent = 'Inventory hub updated.';
    await loadMetrics();
  } catch (error) {
    hubResponse.textContent = error.message;
  }
});

exportBatch.addEventListener('click', async () => {
  const value = batchNumberInput.value.trim();
  const payload = value ? { batchNumber: value } : {};
  try {
    await apiFetch('/api/batch/export', {
      method: 'POST',
      body: JSON.stringify(payload)
    });
    await loadBatches();
  } catch (error) {
    batchList.textContent = error.message;
  }
});

openUnprocessed.addEventListener('click', () => {
  window.open('/api/download/hub/unprocessed', '_blank');
});

openProcessed.addEventListener('click', () => {
  window.open('/api/download/hub/processed', '_blank');
});

loginForm.addEventListener('submit', async (event) => {
  event.preventDefault();
  loginError.textContent = '';

  const formData = new FormData(loginForm);
  const username = formData.get('username');
  const password = formData.get('password');

  try {
    const result = await apiFetch('/api/login', {
      method: 'POST',
      body: JSON.stringify({ username, password })
    });
    if (result.token) {
      setToken(result.token);
    }
    loginOverlay.classList.remove('active');
    await loadStatus();
    await loadInventory();
    await loadBatches();
    await loadMetrics();
  } catch (error) {
    loginError.textContent = error.message;
  }
});

wizardNext.addEventListener('click', advanceWizard);
wizardSkip.addEventListener('click', skipWizard);
wizardLaunch.addEventListener('click', showWizard);

if (!localStorage.getItem('upscaled_wizard_done')) {
  wizardOverlay.classList.add('active');
  renderWizard();
}

loadChecklist();
document.querySelectorAll('[data-check]').forEach((input) => {
  input.addEventListener('change', saveChecklist);
});

loadStatus();
loadInventory();
loadBatches();
loadMetrics();
loadPrintAgentStatus();
