/**
 * Icons.js
 * Central repository for v5.0 UI SVGs.
 * Style: Duotone/Filled, Soft corners, Stroke 1.5-2px.
 */

const Icons = {
    // Header
    Wallet: `<svg width="24" height="24" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg"><rect x="2" y="5" width="20" height="14" rx="3" stroke="currentColor" stroke-width="2"/><path d="M18 12L22 12" stroke="currentColor" stroke-width="2" stroke-linecap="round"/></svg>`, // Simple wallet outline/pill style

    // Hero / Invite
    Rocket: `<svg width="24" height="24" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg"><path d="M4.5 9.5L2 12L4.5 14.5" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/><path d="M19.5 9.5L22 12L19.5 14.5" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/><circle cx="12" cy="12" r="3" stroke="currentColor" stroke-width="2"/></svg>`, // Placeholder, will replace with better Rocket

    // Better Rocket (Filled/Duotone style)
    RocketFilled: `<svg width="24" height="24" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
        <path d="M11.5757 1.42426C11.6569 1.34306 11.7766 1.31758 11.8833 1.35882C13.4357 1.95922 15.9392 3.12518 17.6569 4.84281C19.7891 6.97505 20.3703 9.47195 20.3995 9.58888C20.4287 9.70581 20.4042 9.82915 20.3346 9.92196L14.0772 18.2652C14.0189 18.3429 13.9298 18.3916 13.8335 18.3986C13.7371 18.4056 13.6423 18.3702 13.5757 18.3036L5.04036 9.76822C4.97377 9.70163 4.93838 9.60686 4.94537 9.51051C4.95237 9.41417 5.00105 9.32504 5.07881 9.26674L11.5757 1.42426Z" fill="#ef4444"/>
        <path d="M14.0775 18.2646C14.0191 18.3423 13.93 18.391 13.8337 18.398L13.8242 18.3987L5.04944 19.035C4.91264 19.0449 4.78906 18.9664 4.73977 18.8384C4.69048 18.7104 4.72596 18.5631 4.82859 18.4735L13.5761 18.3031C13.6427 18.2964 13.7317 18.2711 13.7901 18.1934L14.0775 18.2646Z" fill="#b91c1c"/>
        <path d="M12.9142 5.5C12.9142 6.05228 12.4665 6.5 11.9142 6.5C11.3619 6.5 10.9142 6.05228 10.9142 5.5C10.9142 4.94772 11.3619 4.5 11.9142 4.5C12.4665 4.5 12.9142 4.94772 12.9142 5.5Z" fill="white"/>
    </svg>`,

    // Cards
    Users: `<svg width="24" height="24" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg"><path d="M17 21V19C17 16.7909 15.2091 15 13 15H5C2.79086 15 1 16.7909 1 19V21" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/><circle cx="9" cy="7" r="4" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/><path d="M23 21V19C22.9993 18.1137 22.7044 17.2528 22.1614 16.5523C21.6184 15.8519 20.8581 15.3516 20 15.13" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/><path d="M16 3.13C16.8604 3.35031 17.623 3.85071 18.1676 4.55232C18.7122 5.25392 19.005 6.11684 19.005 7.005C19.005 7.89316 18.7122 8.75608 18.1676 9.45768C17.623 10.1593 16.8604 10.6597 16 10.88" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/></svg>`,

    Robot: `<svg width="24" height="24" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg"><rect x="3" y="11" width="18" height="10" rx="2" stroke="currentColor" stroke-width="2"/><circle cx="12" cy="5" r="2" stroke="currentColor" stroke-width="2"/><path d="M12 7V11" stroke="currentColor" stroke-width="2"/><line x1="8" y1="16" x2="8" y2="16" stroke="currentColor" stroke-width="2" stroke-linecap="round"/><line x1="16" y1="16" x2="16" y2="16" stroke="currentColor" stroke-width="2" stroke-linecap="round"/></svg>`,

    // UI Elements
    ChevronRight: `<svg width="20" height="20" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg"><path d="M9 18L15 12L9 6" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/></svg>`,

    // Footer / Misc
    Document: `<svg width="20" height="20" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg"><path d="M14 2H6C5.46957 2 4.96086 2.21071 4.58579 2.58579C4.21071 2.96086 4 3.46957 4 4V20C4 20.5304 4.21071 21.0391 4.58579 21.4142C4.96086 21.7893 5.46957 22 6 22H18C18.5304 22 19.0391 21.7893 19.4142 21.4142C19.7893 21.0391 20 20.5304 20 20V8L14 2Z" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/><path d="M14 2V8H20" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/><path d="M16 13H8" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/><path d="M16 17H8" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/><path d="M10 9H8" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/></svg>`,
    Shield: `<svg width="20" height="20" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg"><path d="M12 22S2 18 2 12V6L12 2L22 6V12C22 18 12 22 12 22Z" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/></svg>`,
    Headphones: `<svg width="20" height="20" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg"><path d="M3 18V12C3 7.02944 7.02944 3 12 3C16.9706 3 21 7.02944 21 12V18" stroke="currentColor" stroke-width="2" stroke-linecap="round"/><rect x="18" y="16" width="4" height="6" rx="1" transform="rotate(180 20 19)" stroke="currentColor" stroke-width="2"/><rect x="2" y="14" width="4" height="6" rx="1" stroke="currentColor" stroke-width="2"/></svg>`,
    Back: `<svg width="24" height="24" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg"><path d="M19 12H5" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/><path d="M12 19L5 12L12 5" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/></svg>`
};
