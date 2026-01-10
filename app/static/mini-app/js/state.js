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
    currentPage: 'home', // Changed default to 'home'
    navigationHistory: [],
    isInitialLoad: true,
    isLoadingData: false,
    loadDataTimeout: null,
    filteredPartners: [],
    currentSort: 'name',
    currentFilter: 'all',
    // New states for Revenue Launcher
    didStart7Flow: false, // Track if user started 7% flow
    topLocked: true, // Track TOP lock status (default: locked)
    referralCount: 0, // Track referral count for TOP unlock
    hasSeenOnboarding: false, // Track onboarding completion
    partnersExpanded: false, // Track if partners list is expanded (default: show 5)
    lastLoadTime: 0, // Track last data load time for debouncing
    tgrLink: null // Track saved TGR link
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
function getDidStart7Flow() { return AppStateInternal.didStart7Flow; }
function getTopLocked() { return AppStateInternal.topLocked; }
function getReferralCount() { return AppStateInternal.referralCount; }
function getHasSeenOnboarding() { return AppStateInternal.hasSeenOnboarding; }
function getPartnersExpanded() { return AppStateInternal.partnersExpanded; }
function getLastLoadTime() { return AppStateInternal.lastLoadTime; }

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
function setDidStart7Flow(value) { AppStateInternal.didStart7Flow = value; }
function setTopLocked(value) { AppStateInternal.topLocked = value; }
function setReferralCount(value) { AppStateInternal.referralCount = value; }
function setHasSeenOnboarding(value) { AppStateInternal.hasSeenOnboarding = value; }
function setPartnersExpanded(value) { AppStateInternal.partnersExpanded = value; }
function setLastLoadTime(value) { AppStateInternal.lastLoadTime = value; }
function setTgrLink(value) { AppStateInternal.tgrLink = value; }
function getTgrLink() { return AppStateInternal.tgrLink; }

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
(function () {
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
            getDidStart7Flow,
            getTopLocked,
            getReferralCount,
            getHasSeenOnboarding,
            getPartnersExpanded,
            getLastLoadTime,

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
            setDidStart7Flow,
            setTopLocked,
            setReferralCount,
            setHasSeenOnboarding,
            setPartnersExpanded,
            setLastLoadTime,
            setTgrLink,
            getTgrLink,

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
            setTg: () => { },
            getBotId: () => null,
            setBotId: () => { },
            getUserId: () => null,
            setUserId: () => { },
            getAppData: () => null,
            setAppData: () => { },
            getCurrentPage: () => 'home',
            setCurrentPage: () => { },
            getNavigationHistory: () => [],
            pushNavigationHistory: () => { },
            popNavigationHistory: () => null,
            clearNavigationHistory: () => { },
            getIsInitialLoad: () => true,
            setIsInitialLoad: () => { },
            getIsLoadingData: () => false,
            setIsLoadingData: () => { },
            getLoadDataTimeout: () => null,
            setLoadDataTimeout: () => { },
            getFilteredPartners: () => [],
            setFilteredPartners: () => { },
            getCurrentSort: () => 'name',
            setCurrentSort: () => { },
            getCurrentFilter: () => 'all',
            setCurrentFilter: () => { },
            getDidStart7Flow: () => false,
            setDidStart7Flow: () => { },
            getTopLocked: () => true,
            setTopLocked: () => { },
            getReferralCount: () => 0,
            setReferralCount: () => { },
            getHasSeenOnboarding: () => false,
            setHasSeenOnboarding: () => { },
            getPartnersExpanded: () => false,
            setPartnersExpanded: () => { }
        };
    }
})();
