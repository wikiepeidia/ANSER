const scenarioState = {
    items: [],
    filteredItems: [],
    activeFolder: 'all',
    activeStatus: 'all',
    searchTerm: ''
};

const fallbackScenarios = [];

function initScenariosPage() {
    if (!document.body.classList.contains('scenarios-page')) {
        return;
    }

    scenarioState.grid = document.querySelector('[data-scenarios-grid]');
    scenarioState.emptyState = document.querySelector('[data-scenarios-empty]');
    scenarioState.folderItems = document.querySelectorAll('[data-folder-item]');
    scenarioState.folderCounts = document.querySelectorAll('[data-folder-count]');
    scenarioState.tabs = document.querySelectorAll('[data-tab]');
    scenarioState.tabBadges = document.querySelectorAll('[data-tab-count]');

    // Check for first-time user
    checkFirstTimeUser();

    const searchInput = document.querySelector('[data-scenarios-search]');
    if (searchInput) {
        searchInput.addEventListener('input', (event) => {
            scenarioState.searchTerm = event.target.value.trim().toLowerCase();
            applyScenarioFilters();
        });
    }

    // Load scenarios (mock or real)
    loadScenarios();

    scenarioState.folderItems.forEach((item) => {
        item.addEventListener('click', () => {
            const folder = item.dataset.folderItem;
            selectFolder(folder);
        });
    });

    scenarioState.tabs.forEach((tab) => {
        tab.addEventListener('click', () => {
            selectTab(tab.dataset.tab);
        });
    });
}

function checkFirstTimeUser() {
    const hasSeenTutorial = localStorage.getItem('hasSeenWorkflowTutorial');
    if (!hasSeenTutorial) {
        // Small delay to ensure UI is loaded
        setTimeout(() => {
            showTutorialModal();
        }, 1000);
    }
}

window.showTutorialModal = function() {
    const modalEl = document.getElementById('tutorialModal');
    if (modalEl) {
        const modal = new bootstrap.Modal(modalEl);
        modal.show();
        
        // Handle "Don't show again" checkbox
        const checkbox = document.getElementById('dontShowAgain');
        if (checkbox) {
            checkbox.addEventListener('change', (e) => {
                if (e.target.checked) {
                    localStorage.setItem('hasSeenWorkflowTutorial', 'true');
                } else {
                    localStorage.removeItem('hasSeenWorkflowTutorial');
                }
            });
        }
        
        // Also set it if they click "Start Tour" or "Maybe Later" if checkbox is checked
        modalEl.addEventListener('hidden.bs.modal', () => {
            if (document.getElementById('dontShowAgain')?.checked) {
                localStorage.setItem('hasSeenWorkflowTutorial', 'true');
            }
        });
    }
};

window.startInteractiveTutorial = function() {
    // Placeholder for interactive tour
    bootstrap.Modal.getInstance(document.getElementById('tutorialModal')).hide();
    localStorage.setItem('hasSeenWorkflowTutorial', 'true');
    alert('Interactive tour starting... (This is a placeholder)');
};

document.addEventListener('DOMContentLoaded', initScenariosPage);

async function loadScenarios() {
    try {
        const response = await fetch('/api/scenarios');
        if (!response.ok) {
            throw new Error('Failed to fetch scenarios');
        }
        const data = await response.json();
        if (data && data.success && Array.isArray(data.scenarios)) {
            scenarioState.items = data.scenarios;
        } else {
            scenarioState.items = fallbackScenarios;
        }
    } catch (error) {
        console.warn('Using fallback scenarios:', error.message);
        scenarioState.items = fallbackScenarios;
    } finally {
        applyScenarioFilters();
    }
}

function applyScenarioFilters() {
    const normalizedFolder = scenarioState.activeFolder || 'all';
    const normalizedStatus = scenarioState.activeStatus || 'all';

    scenarioState.filteredItems = scenarioState.items.filter((scenario) => {
        const matchesFolder =
            normalizedFolder === 'all' ||
            (normalizedFolder === 'uncategorized' && !scenario.folder) ||
            (scenario.folder && scenario.folder === normalizedFolder);

        const matchesStatus =
            normalizedStatus === 'all' ||
            (scenario.status && scenario.status === normalizedStatus);

        const matchesSearch = !scenarioState.searchTerm ||
            scenario.name?.toLowerCase().includes(scenarioState.searchTerm) ||
            scenario.description?.toLowerCase().includes(scenarioState.searchTerm) ||
            scenario.id?.toLowerCase().includes(scenarioState.searchTerm);

        return matchesFolder && matchesStatus && matchesSearch;
    });

    renderScenarioGrid();
    updateScenarioCounts();
}

function renderScenarioGrid() {
    if (!scenarioState.grid || !scenarioState.emptyState) {
        return;
    }

    const hasItems = scenarioState.filteredItems.length > 0;
    scenarioState.grid.toggleAttribute('hidden', !hasItems);
    scenarioState.emptyState.toggleAttribute('hidden', hasItems);

    if (!hasItems) {
        scenarioState.grid.innerHTML = '';
        return;
    }

    scenarioState.grid.innerHTML = scenarioState.filteredItems
        .map((scenario) => buildScenarioCard(scenario))
        .join('');
}

function buildScenarioCard(scenario) {
    const statusMap = {
        active: { label: 'Active', className: 'badge-success' },
        inactive: { label: 'Inactive', className: 'badge-secondary' },
        concept: { label: 'Concept', className: 'badge-warning' }
    };

    const statusMeta = statusMap[scenario.status] || statusMap.inactive;
    const lastUpdated = formatScenarioDate(scenario.updated_at);

    return `
        <article class="scenario-card">
            <header class="scenario-card__header">
                <div>
                    <p class="scenario-card__id">${scenario.id || 'SCN-NEW'}</p>
                    <h3 class="scenario-card__title">${scenario.name || 'Untitled Scenario'}</h3>
                </div>
                <span class="badge ${statusMeta.className}">${statusMeta.label}</span>
            </header>
            <p class="scenario-card__description">${scenario.description || 'No description provided yet.'}</p>
            <footer class="scenario-card__footer">
                <div class="scenario-card__meta">
                    <span><i class="fas fa-sync"></i> Runs: ${scenario.runs ?? 0}</span>
                    <span><i class="fas fa-clock"></i> Updated: ${lastUpdated}</span>
                </div>
                <div class="d-flex justify-content-between align-items-center mt-3 w-100">
                     <button class="scenario-card__action me-2" type="button" onclick="openBuilder('${scenario.id || ''}')">
                        Open Builder
                    </button>
                    <div>
                        <button class="btn btn-sm btn-link text-secondary p-0 me-2" type="button" onclick="editScenario('${scenario.id}')" title="Edit">
                            <i class="fas fa-edit"></i>
                        </button>
                        <button class="btn btn-sm btn-link text-danger p-0" type="button" onclick="deleteScenario('${scenario.id}')" title="Delete">
                            <i class="fas fa-trash"></i>
                        </button>
                    </div>
                </div>
            </footer>
        </article>
    `;
}

function updateScenarioCounts() {
    const total = scenarioState.items.length;
    const active = scenarioState.items.filter((item) => item.status === 'active').length;
    const inactive = scenarioState.items.filter((item) => item.status === 'inactive').length;
    const concepts = scenarioState.items.filter((item) => item.status === 'concept').length;
    const uncategorized = scenarioState.items.filter((item) => !item.folder).length;

    const folderCountMap = {
        all: total,
        uncategorized
    };

    const statusCountMap = {
        all: total,
        active,
        inactive,
        concept: concepts
    };

    scenarioState.folderCounts.forEach((node) => {
        const folderKey = node.dataset.folderCount;
        if (folderKey && typeof folderCountMap[folderKey] !== 'undefined') {
            const count = folderCountMap[folderKey];
            node.textContent = `${count} ${count === 1 ? 'scenario' : 'scenarios'}`;
        }
    });

    scenarioState.tabBadges.forEach((badge) => {
        const tabKey = badge.dataset.tabCount;
        if (tabKey && typeof statusCountMap[tabKey] !== 'undefined') {
            badge.textContent = statusCountMap[tabKey];
        }
    });
}

function selectFolder(folderKey = 'all') {
    scenarioState.activeFolder = folderKey;
    scenarioState.folderItems.forEach((item) => {
        item.classList.toggle('active', item.dataset.folderItem === folderKey);
    });
    applyScenarioFilters();
}

function selectTab(tabKey = 'all') {
    scenarioState.activeStatus = tabKey;
    scenarioState.tabs.forEach((tab) => {
        tab.classList.toggle('active', tab.dataset.tab === tabKey);
    });
    applyScenarioFilters();
}

function createFolder() {
    if (typeof showNotification === 'function') {
        showNotification('Folder management is coming soon.', 'info');
    } else {
        alert('Folder management is coming soon.');
    }
}

function createScenario() {
    // Direct to builder page as requested
    openBuilder();
}

function editScenario(id) {
    const scenario = scenarioState.items.find(s => s.id === id);
    if (!scenario) return;

    document.getElementById('scenarioId').value = scenario.id;
    document.getElementById('scenarioName').value = scenario.name;
    document.getElementById('scenarioDescription').value = scenario.description || '';
    document.getElementById('scenarioModalLabel').textContent = 'Edit Scenario';
    
    const modalEl = document.getElementById('scenarioModal');
    if (modalEl && typeof bootstrap !== 'undefined') {
        const modal = bootstrap.Modal.getOrCreateInstance(modalEl);
        modal.show();
    }
}

async function saveScenario() {
    const id = document.getElementById('scenarioId').value;
    const name = document.getElementById('scenarioName').value;
    const description = document.getElementById('scenarioDescription').value;

    if (!name) {
        alert('Please enter a scenario name');
        return;
    }

    const payload = { name, description };
    const method = id ? 'PUT' : 'POST';
    const url = id ? `/api/scenarios/${id}` : '/api/scenarios';
    const csrfToken = document.querySelector('meta[name="csrf-token"]')?.content;

    try {
        const response = await fetch(url, {
            method: method,
            headers: { 
                'Content-Type': 'application/json',
                'X-CSRFToken': csrfToken
            },
            body: JSON.stringify(payload)
        });

        if (!response.ok) throw new Error('Failed to save scenario');

        const result = await response.json();
        
        // Hide modal
        const modalEl = document.getElementById('scenarioModal');
        if (modalEl && typeof bootstrap !== 'undefined') {
            const modal = bootstrap.Modal.getOrCreateInstance(modalEl);
            modal.hide();
        }

        // Reload scenarios
        loadScenarios();
        
        if (typeof showNotification === 'function') {
            showNotification('Scenario saved successfully', 'success');
        }
    } catch (error) {
        console.error('Error saving scenario:', error);
        alert('Error saving scenario: ' + error.message);
    }
}

async function deleteScenario(id) {
    if (!confirm('Are you sure you want to delete this scenario?')) return;

    const csrfToken = document.querySelector('meta[name="csrf-token"]')?.content;

    try {
        const response = await fetch(`/api/scenarios/${id}`, {
            method: 'DELETE',
            headers: {
                'X-CSRFToken': csrfToken
            }
        });

        if (!response.ok) throw new Error('Failed to delete scenario');

        loadScenarios();
        
        if (typeof showNotification === 'function') {
            showNotification('Scenario deleted successfully', 'success');
        }
    } catch (error) {
        console.error('Error deleting scenario:', error);
        alert('Error deleting scenario: ' + error.message);
    }
}

function openBuilder(scenarioId = '') {
    if (scenarioId) {
        window.location.href = `/workspace/builder?id=${encodeURIComponent(scenarioId)}`;
        return;
    }
    window.location.href = '/workspace/builder';
}

function browseTemplates() {
    if (typeof showNotification === 'function') {
        showNotification('Template marketplace will be available soon.', 'info');
    } else {
        alert('Template marketplace will be available soon.');
    }
}

function formatScenarioDate(dateValue) {
    if (!dateValue) {
        return 'Not run yet';
    }
    try {
        const date = new Date(dateValue);
        if (Number.isNaN(date.getTime())) {
            return 'Not run yet';
        }
        return date.toLocaleString('en-US', {
            dateStyle: 'medium',
            timeStyle: 'short'
        });
    } catch (error) {
        return 'Not run yet';
    }
}

// Expose functions for inline handlers
window.createFolder = createFolder;
window.selectFolder = selectFolder;
window.createScenario = createScenario;
window.editScenario = editScenario;
window.saveScenario = saveScenario;
window.deleteScenario = deleteScenario;
window.openBuilder = function(id = null) {
    if (id) {
        window.location.href = `/workspace/builder?id=${id}`;
    } else {
        window.location.href = '/workspace/builder';
    }
};
window.browseTemplates = browseTemplates;