/**
 * Navigation Module
 * Tab switching, partner detail, search and filters
 */

function switchTab(tabName) {
    // Haptic feedback
    if (typeof Haptic !== 'undefined') {
        Haptic.light();
    }
    
    // If user manually switches tabs, mark that initial load is done
    // This prevents loadAppData from auto-switching to earnings
    if (AppState.getIsInitialLoad()) {
        AppState.setIsInitialLoad(false);
    }
    
    // Update tab buttons
    document.querySelectorAll('.tab').forEach(tab => {
        const isActive = tab.getAttribute('data-tab') === tabName;
        tab.classList.toggle('active', isActive);
        // Update aria-current for accessibility
        if (isActive) {
            tab.setAttribute('aria-current', 'page');
        } else {
            tab.removeAttribute('aria-current');
        }
    });
    
    // Show target page
    const targetPage = document.getElementById(`${tabName}-page`);
    if (!targetPage) {
        console.error(`Page not found: ${tabName}-page`);
        return;
    }
    
    // Hide all pages first
    document.querySelectorAll('.page').forEach(page => {
        page.classList.remove('active');
        // Force hide to ensure no display issues
        if (page !== targetPage) {
            page.style.display = 'none';
        }
    });
    
    // Show target page (CSS will handle display via .page.active)
    targetPage.classList.add('active');
    targetPage.style.display = 'block';
    AppState.setCurrentPage(tabName);
    
    // Scroll to top when switching tabs (works for all tabs: Home, Partners, TOP)
    // Find the scrollable container (usually .content or the page itself)
    const contentContainer = document.querySelector('.content') || targetPage;
    if (contentContainer) {
        // Use requestAnimationFrame to ensure DOM is updated before scrolling
        requestAnimationFrame(() => {
            contentContainer.scrollTo({
                top: 0,
                left: 0,
                behavior: 'instant' // Instant scroll, no animation
            });
            // Fallback for older browsers
            if (contentContainer.scrollTo === undefined) {
                contentContainer.scrollTop = 0;
            }
        });
    }
    
    console.log(`[Navigation] Switched to tab: ${tabName}, page ID: ${targetPage.id}`);
    console.log(`[Navigation] Active pages:`, Array.from(document.querySelectorAll('.page.active')).map(p => p.id));
    
    // Show skeleton while loading (if data not available)
    if (!AppState.getAppData()) {
        showSkeleton(tabName);
    }
    
    // Render content immediately with existing data (if available)
    // This ensures user sees content right away, not a blank screen
    if (tabName === 'home') {
        if (AppState.getAppData()) {
            hideSkeleton('home');
            if (typeof Render !== 'undefined' && Render.renderHome) {
                Render.renderHome();
            } else {
                renderHome();
            }
        }
    } else if (tabName === 'partners') {
        if (AppState.getAppData()) {
            hideSkeleton('partners');
            if (typeof Render !== 'undefined' && Render.renderPartners) {
                Render.renderPartners();
            } else {
                renderPartners();
            }
            setupSearchAndFilters();
        }
    } else if (tabName === 'top') {
        if (AppState.getAppData()) {
            hideSkeleton('top');
            if (typeof Render !== 'undefined' && Render.renderTop) {
                Render.renderTop();
            } else {
                renderTop();
            }
        }
    }
    
    // Reload data when switching to tabs that need fresh data
    // This ensures counters and stats are up-to-date
    // BUT: Don't reload on initial load (AppState.getIsInitialLoad() = true) to prevent infinite loop
    // AND: Only reload if we have existing data (to avoid double load on first visit)
    if ((tabName === 'home' || tabName === 'top') && AppState.getAppData() && !AppState.getIsInitialLoad()) {
        // Reload app data to get fresh counters (only if AppState.getAppData() already exists and not initial load)
        // Use debounced version to prevent multiple rapid calls
        loadAppData(false).catch(err => {
            console.error('Error reloading data:', err);
            // Data already rendered above, so user sees content even if reload fails
        });
    }
}

function showPartnerDetail(partnerId) {
    if (!partnerId) {
        console.error('Partner ID is required');
        return;
    }
    
    AppState.pushNavigationHistory(AppState.getCurrentPage());
    
    // Hide current page
    document.querySelectorAll('.page').forEach(page => {
        page.classList.remove('active');
    });
    
    // Show detail page
    const detailPage = document.getElementById('partner-detail-page');
    if (detailPage) {
        detailPage.classList.add('active');
        AppState.setCurrentPage('partner-detail');
        renderPartnerDetail(String(partnerId));
    }
}

function goBack() {
    const history = AppState.getNavigationHistory();
    if (history.length > 0) {
        const previousPage = AppState.popNavigationHistory();
        if (typeof Navigation !== 'undefined' && Navigation.switchTab) {
            Navigation.switchTab(previousPage);
        } else {
            switchTab(previousPage);
        }
    } else {
        if (typeof Navigation !== 'undefined' && Navigation.switchTab) {
            Navigation.switchTab('home');
        } else {
            switchTab('home');
        }
    }
}

function setupSearchAndFilters() {
    // Search input
    const searchInput = document.getElementById('partner-search');
    if (searchInput) {
        let searchTimeout;
        searchInput.addEventListener('input', (e) => {
            clearTimeout(searchTimeout);
            searchTimeout = setTimeout(() => {
                filterPartners(e.target.value);
            }, 300); // Debounce
        });
    }
    
    // Filter button
    const filterBtn = document.getElementById('filter-btn');
    const filterPanel = document.getElementById('filter-panel');
    if (filterBtn && filterPanel) {
        filterBtn.addEventListener('click', () => {
            filterPanel.style.display = filterPanel.style.display === 'none' ? 'block' : 'none';
        });
    }
    
    // Sort select
    const sortSelect = document.getElementById('sort-select');
    if (sortSelect) {
        sortSelect.addEventListener('change', (e) => {
            AppState.setCurrentSort(e.target.value);
            applyFilters();
        });
    }
    
    // Filter chips
    document.querySelectorAll('.chip').forEach(chip => {
        chip.addEventListener('click', (e) => {
            document.querySelectorAll('.chip').forEach(c => c.classList.remove('active'));
            e.target.classList.add('active');
            AppState.setCurrentFilter(e.target.getAttribute('data-filter'));
            applyFilters();
        });
    });
}

function filterPartners(query) {
    const appData = AppState.getAppData();
    if (!appData) return;
    
    const partners = appData.partners || [];
    const searchQuery = query.toLowerCase().trim();
    
    if (searchQuery === '') {
        AppState.setFilteredPartners([...partners]);
    } else {
        const filtered = partners.filter(partner => {
            const name = (partner.name || '').toLowerCase();
            const description = (partner.description || '').toLowerCase();
            return name.includes(searchQuery) || description.includes(searchQuery);
        });
        AppState.setFilteredPartners(filtered);
    }
    
    if (typeof Navigation !== 'undefined' && Navigation.applyFilters) {
        Navigation.applyFilters();
    } else {
        applyFilters();
    }
}

function applyFilters() {
    const appData = AppState.getAppData();
    if (!appData) return;
    
    const filteredPartners = AppState.getFilteredPartners();
    let partners = filteredPartners.length > 0 ? filteredPartners : (appData.partners || []);
    
    // Apply category filter
    const currentFilter = AppState.getCurrentFilter();
    if (currentFilter !== 'all') {
        // TODO: Add category filtering when backend supports it
        // For now, filter by TOP status
        if (currentFilter === 'top') {
            const topPartnerIds = (appData.top_partners || []).map(p => p.id);
            partners = partners.filter(p => topPartnerIds.includes(p.id));
        }
    }
    
    // Apply sorting
    const currentSort = AppState.getCurrentSort();
    partners.sort((a, b) => {
        switch (currentSort) {
            case 'commission':
                return (b.commission || 0) - (a.commission || 0);
            case 'name':
                return (a.name || '').localeCompare(b.name || '');
            case 'new':
                // TODO: Add date field when backend supports it
                return 0;
            default:
                return 0;
        }
    });
    
    if (typeof Render !== 'undefined' && Render.renderPartnersList) {
        Render.renderPartnersList(partners);
    } else {
        renderPartnersList(partners);
    }
}


window.Navigation = {
    switchTab,
    showPartnerDetail,
    goBack,
    setupSearchAndFilters,
    filterPartners,
    applyFilters
};
