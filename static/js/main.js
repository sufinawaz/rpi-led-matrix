/**
 * InfoCube Remote Control JavaScript
 * Handles UI interactivity and tab persistence
 */
document.addEventListener('DOMContentLoaded', function() {
    // Theme toggle functionality
    initThemeToggle();

    // Initialize main tabs with persistence
    initMainTabs();

    // Initialize GIF subtabs with persistence
    initGifTabs();

    // Initialize interactive UI elements
    initBrightnessSlider();
    initPasswordToggle();
    initFlashMessages();
});

/**
 * Initialize light/dark theme toggle
 */
function initThemeToggle() {
    const themeToggle = document.getElementById('theme-toggle');
    if (!themeToggle) return;

    // Check for saved theme preference or use device preference
    const savedTheme = localStorage.getItem('theme');
    const prefersDarkMode = window.matchMedia && window.matchMedia('(prefers-color-scheme: dark)').matches;

    // Apply theme based on preference
    if (savedTheme === 'dark' || (!savedTheme && prefersDarkMode)) {
        document.documentElement.setAttribute('data-theme', 'dark');
        themeToggle.checked = true;
    }

    // Listen for theme toggle changes
    themeToggle.addEventListener('change', function() {
        if (this.checked) {
            document.documentElement.setAttribute('data-theme', 'dark');
            localStorage.setItem('theme', 'dark');
        } else {
            document.documentElement.removeAttribute('data-theme');
            localStorage.setItem('theme', 'light');
        }
    });
}

/**
 * Initialize main tabs (Plugins, GIFs, Settings)
 */
function initMainTabs() {
    const mainTabs = document.querySelectorAll('.main-tab');
    const mainTabContents = document.querySelectorAll('.main-tab-content');

    if (!mainTabs.length) return;

    // Check localStorage for last selected tab
    const lastMainTab = localStorage.getItem('lastMainTab') || 'plugins';

    // Set initial active tab based on localStorage
    activateMainTab(lastMainTab);

    // Add click event listeners to main tabs
    mainTabs.forEach(tab => {
        tab.addEventListener('click', () => {
            const tabId = tab.getAttribute('data-main-tab');
            activateMainTab(tabId);

            // Save to localStorage
            localStorage.setItem('lastMainTab', tabId);
        });
    });

    // Function to activate the selected tab
    function activateMainTab(tabId) {
        // Remove active class from all tabs and contents
        mainTabs.forEach(t => t.classList.remove('active'));
        mainTabContents.forEach(c => c.classList.remove('active'));

        // Add active class to selected tab and content
        const selectedTab = document.querySelector(`[data-main-tab="${tabId}"]`);
        const selectedContent = document.getElementById(`${tabId}-content`);

        if (selectedTab) selectedTab.classList.add('active');
        if (selectedContent) selectedContent.classList.add('active');
    }
}

/**
 * Initialize GIF subtabs (Gallery, Add from URL, Upload)
 */
function initGifTabs() {
    const gifTabs = document.querySelectorAll('.gif-tab');
    const gifTabContents = document.querySelectorAll('.tab-content');

    if (!gifTabs.length) return;

    // Check localStorage for last selected GIF tab
    const lastGifTab = localStorage.getItem('lastGifTab') || 'existing-gifs';

    // Set initial active GIF tab based on localStorage
    activateGifTab(lastGifTab);

    // Add click event listeners to GIF tabs
    gifTabs.forEach(tab => {
        tab.addEventListener('click', () => {
            const tabId = tab.getAttribute('data-tab');
            activateGifTab(tabId);

            // Save to localStorage
            localStorage.setItem('lastGifTab', tabId);
        });
    });

    // Function to activate the selected GIF tab
    function activateGifTab(tabId) {
        // Remove active class from all tabs and contents
        gifTabs.forEach(t => t.classList.remove('active'));
        gifTabContents.forEach(c => c.classList.remove('active'));

        // Add active class to selected tab and content
        const selectedTab = document.querySelector(`[data-tab="${tabId}"]`);
        const selectedContent = document.getElementById(tabId);

        if (selectedTab) selectedTab.classList.add('active');
        if (selectedContent) selectedContent.classList.add('active');
    }
}

/**
 * Initialize brightness slider with live preview
 */
function initBrightnessSlider() {
    const brightnessSlider = document.getElementById('brightness');
    const brightnessValue = document.querySelector('.brightness-value');

    if (!brightnessSlider || !brightnessValue) return;

    brightnessSlider.addEventListener('input', function() {
        brightnessValue.textContent = this.value + '%';
    });
}

/**
 * Initialize password toggle for API key field
 */
function initPasswordToggle() {
    const toggleApiKey = document.getElementById('toggle-api-key');
    const apiKeyInput = document.getElementById('weather_api_key');

    if (!toggleApiKey || !apiKeyInput) return;

    toggleApiKey.addEventListener('click', function() {
        const toggleIcon = this.querySelector('i');

        if (apiKeyInput.type === 'password') {
            apiKeyInput.type = 'text';
            toggleIcon.classList.remove('fa-eye');
            toggleIcon.classList.add('fa-eye-slash');
        } else {
            apiKeyInput.type = 'password';
            toggleIcon.classList.remove('fa-eye-slash');
            toggleIcon.classList.add('fa-eye');
        }
    });
}

/**
 * Initialize auto-hide for flash messages
 */
function initFlashMessages() {
    const flashMessages = document.querySelectorAll('.flash');

    if (!flashMessages.length) return;

    setTimeout(() => {
        flashMessages.forEach(message => {
            message.style.opacity = '0';
            message.style.transform = 'translateY(-10px)';
            setTimeout(() => {
                message.style.display = 'none';
            }, 300);
        });
    }, 6000);
}