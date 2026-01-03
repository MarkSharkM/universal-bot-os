/**
 * State Management Module
 * Manages global application state
 */

// Global state
const AppState = {
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
function getTg() { return AppState.tg; }
function getBotId() { return AppState.botId; }
function getUserId() { return AppState.userId; }
function getAppData() { return AppState.appData; }
function getCurrentPage() { return AppState.currentPage; }
function getNavigationHistory() { return AppState.navigationHistory; }
function getIsInitialLoad() { return AppState.isInitialLoad; }
function getIsLoadingData() { return AppState.isLoadingData; }
function getLoadDataTimeout() { return AppState.loadDataTimeout; }
function getFilteredPartners() { return AppState.filteredPartners; }
function getCurrentSort() { return AppState.currentSort; }
function getCurrentFilter() { return AppState.currentFilter; }

// Setters
function setTg(value) { AppState.tg = value; }
function setBotId(value) { AppState.botId = value; }
function setUserId(value) { AppState.userId = value; }
function setAppData(value) { AppState.appData = value; }
function setCurrentPage(value) { AppState.currentPage = value; }
function setIsInitialLoad(value) { AppState.isInitialLoad = value; }
function setIsLoadingData(value) { AppState.isLoadingData = value; }
function setLoadDataTimeout(value) { AppState.loadDataTimeout = value; }
function setFilteredPartners(value) { AppState.filteredPartners = value; }
function setCurrentSort(value) { AppState.currentSort = value; }
function setCurrentFilter(value) { AppState.currentFilter = value; }

// Navigation history helpers
function pushNavigationHistory(page) {
    AppState.navigationHistory.push(page);
}

function popNavigationHistory() {
    return AppState.navigationHistory.pop();
}

function clearNavigationHistory() {
    AppState.navigationHistory = [];
}

// Export (namespace pattern for compatibility)
// Immediately export to ensure it's available as soon as script loads
(function() {
    try {
        window.AppState = {
            // State object (for direct access if needed)
            state: AppState,
            
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
