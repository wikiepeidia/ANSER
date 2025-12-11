const scenarioState = {
    items: [],
    filteredItems: [],
    activeFolder: 'all',
    activeStatus: 'all',
    searchTerm: ''
};

const fallbackScenarios = [
    {
        id: 'SCN-INV-001',
        name: 'Inventory Sync Automation',
        description: 'Keeps Shopify and internal ERP inventory in sync every hour.',
        status: 'active',
        runs: 42,
        folder: 'all',
        updated_at: new Date().toISOString()
    },
    {
        id: 'SCN-CS-002',
        name: 'Customer Service Digest',
        description: 'Summarizes daily support tickets and posts to Slack.',
        status: 'inactive',
        runs: 0,
        folder: 'uncategorized',
        updated_at: new Date(Date.now() - 86400000).toISOString()
    },
    {
        id: 'SCN-FR-003',
        name: 'Fraud Review Concept',
        description: 'Prototype flow for flagging risky orders.',
        status: 'concept',
        runs: 0,
        folder: 'concepts',
        updated_at: new Date(Date.now() - 43200000).toISOString()
    }
];

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

    const searchInput = document.querySelector('[data-scenarios-search]');
    if (searchInput) {
        searchInput.addEventListener('input', (event) => {
            scenarioState.searchTerm = event.target.value.trim().toLowerCase();
            applyScenarioFilters();
        });
    }

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

    loadScenarios();
}

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
                <button class="scenario-card__action" type="button" onclick="openBuilder('${scenario.id || ''}')">
                    Open Builder
                </button>
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
    if (typeof showNotification === 'function') {
        showNotification('Scenario creation wizard is under development.', 'info');
    } else {
        alert('Scenario creation wizard is under development.');
    }
}

function openBuilder(scenarioId = '') {
    if (scenarioId) {
        window.location.href = `/workspace_builder?scenario=${encodeURIComponent(scenarioId)}`;
        return;
    }
    window.location.href = '/workspace_builder';
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
window.openBuilder = openBuilder;
window.browseTemplates = browseTemplates;