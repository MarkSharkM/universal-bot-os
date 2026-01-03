/**
 * State Management Module
 * Manages global application state
 */

// Global state (use different name to avoid conflict)
const AppStateInternal = {
    tg: null,
    botId: null,
    userId: null,
    appData: null,
    currentPage: 'partners',
    navigationHistory: [],
    isInitialLoad: true,
    isLoadingData: false,
    loadDataTimeout: null,
    filteredPartners: [],
    currentSort: 'name',
    currentFilter: 'all'
};

// Getters
function getTg() { return AppStateInternal.tg; }
function getBotId() { return AppStateInternal.botId; }
function getUserId() { return AppStateInternal.userId; }
function getAppData() { return AppStateInternal.appData; }
function getCurrentPage() { return AppStateInternal.currentPage; }
function getNavigationHistory() { return AppStateInternal.navigationHistory; }
function getIsInitialLoad() { return AppStateInternal.isInitialLoad; }
function getIsLoadingData() { return AppStateInternal.isLoadingData; }
function getLoadDataTimeout() { return AppStateInternal.loadDataTimeout; }
function getFilteredPartners() { return AppStateInternal.filteredPartners; }
function getCurrentSort() { return AppStateInternal.currentSort; }
function getCurrentFilter() { return AppStateInternal.currentFilter; }

// Setters
function setTg(value) { AppStateInternal.tg = value; }
function setBotId(value) { AppStateInternal.botId = value; }
function setUserId(value) { AppStateInternal.userId = value; }
function setAppData(value) { AppStateInternal.appData = value; }
function setCurrentPage(value) { AppStateInternal.currentPage = value; }
function setIsInitialLoad(value) { AppStateInternal.isInitialLoad = value; }
function setIsLoadingData(value) { AppStateInternal.isLoadingData = value; }
function setLoadDataTimeout(value) { AppStateInternal.loadDataTimeout = value; }
function setFilteredPartners(value) { AppStateInternal.filteredPartners = value; }
function setCurrentSort(value) { AppStateInternal.currentSort = value; }
function setCurrentFilter(value) { AppStateInternal.currentFilter = value; }

// Navigation history helpers
function pushNavigationHistory(page) {
    AppStateInternal.navigationHistory.push(page);
}

function popNavigationHistory() {
    return AppStateInternal.navigationHistory.pop();
}

function clearNavigationHistory() {
    AppStateInternal.navigationHistory = [];
}

// Export (namespace pattern for compatibility)
// Immediately export to ensure it's available as soon as script loads
(function() {
    try {
        window.AppState = {
            // State object (for direct access if needed)
            state: AppStateInternal,
            
            // Getters
            getTg,
            getBotId,
            getUserId,
            getAppData,
            getCurrentPage,
            getNavigationHistory,
            getIsInitialLoad,
            getIsLoadingData,
            getLoadDataTimeout,
            getFilteredPartners,
            getCurrentSort,
            getCurrentFilter,
            
            // Setters
            setTg,
            setBotId,
            setUserId,
            setAppData,
            setCurrentPage,
            setIsInitialLoad,
            setIsLoadingData,
            setLoadDataTimeout,
            setFilteredPartners,
            setCurrentSort,
            setCurrentFilter,
            
            // Navigation helpers
            pushNavigationHistory,
            popNavigationHistory,
            clearNavigationHistory
        };
        
        // Log success (only in development)
        if (window.location.hostname === 'localhost' || window.location.hostname.includes('127.0.0.1')) {
            console.log('✅ AppState module loaded successfully');
        }
    } catch (error) {
        console.error('❌ Error loading AppState module:', error);
        // Still try to export something to prevent complete failure
        window.AppState = {
            getTg: () => null,
            setTg: () => {},
            getBotId: () => null,
            setBotId: () => {},
            getUserId: () => null,
            setUserId: () => {},
            getAppData: () => null,
            setAppData: () => {},
            getCurrentPage: () => 'partners',
            setCurrentPage: () => {},
            getNavigationHistory: () => [],
            pushNavigationHistory: () => {},
            popNavigationHistory: () => null,
            clearNavigationHistory: () => {},
            getIsInitialLoad: () => true,
            setIsInitialLoad: () => {},
            getIsLoadingData: () => false,
            setIsLoadingData: () => {},
            getLoadDataTimeout: () => null,
            setLoadDataTimeout: () => {},
            getFilteredPartners: () => [],
            setFilteredPartners: () => {},
            getCurrentSort: () => 'name',
            setCurrentSort: () => {},
            getCurrentFilter: () => 'all',
            setCurrentFilter: () => {}
        };
    }
})();
