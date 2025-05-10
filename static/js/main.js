document.addEventListener('DOMContentLoaded', function() {
    // Dark/Light theme toggle
    const themeToggle = document.getElementById('theme-toggle');
    const storedTheme = localStorage.getItem('theme');

    // Apply stored theme on page load
    if (storedTheme === 'dark') {
        document.body.classList.add('dark-theme');
        themeToggle.checked = true;
    }

    // Toggle theme on switch change
    themeToggle.addEventListener('change', function() {
        if (this.checked) {
            document.body.classList.add('dark-theme');
            localStorage.setItem('theme', 'dark');
        } else {
            document.body.classList.remove('dark-theme');
            localStorage.setItem('theme', 'light');
        }
    });

    // Main tabs functionality
    const mainTabs = document.querySelectorAll('.main-tab');
    const mainTabContents = document.querySelectorAll('.main-tab-content');

    // Handle main tab clicks
    mainTabs.forEach(tab => {
        tab.addEventListener('click', function() {
            const tabId = this.getAttribute('data-main-tab');

            // Remove active class from all tabs
            mainTabs.forEach(t => t.classList.remove('active'));

            // Add active class to current tab
            this.classList.add('active');

            // Hide all tab content
            mainTabContents.forEach(content => content.style.display = 'none');

            // Show selected tab content
            document.getElementById(`${tabId}-content`).style.display = 'block';

            // Store the active tab in session storage
            localStorage.setItem('activeMainTab', tabId);
        });
    });

    // GIF subtabs functionality
    const gifTabs = document.querySelectorAll('.gif-tab');
    const gifTabContents = document.querySelectorAll('.tab-content');

    gifTabs.forEach(tab => {
        tab.addEventListener('click', function() {
            const tabId = this.getAttribute('data-tab');

            // Remove active class from all tabs
            gifTabs.forEach(t => t.classList.remove('active'));

            // Add active class to current tab
            this.classList.add('active');

            // Hide all tab content
            gifTabContents.forEach(content => content.classList.remove('active'));

            // Show selected tab content
            document.getElementById(tabId).classList.add('active');
        });
    });

    // Restore previously active tab
    const activeMainTab = localStorage.getItem('activeMainTab');
    if (activeMainTab) {
        const tab = document.querySelector(`[data-main-tab="${activeMainTab}"]`);
        if (tab) {
            tab.click();
        }
    }

    // Flash messages auto-dismiss
    const flashMessages = document.querySelectorAll('.flash');
    flashMessages.forEach(message => {
        setTimeout(() => {
            message.style.opacity = '0';
            setTimeout(() => {
                message.style.display = 'none';
            }, 500);
        }, 5000);
    });

    // Toggle password visibility for API key
    const toggleApiKey = document.getElementById('toggle-api-key');
    if (toggleApiKey) {
        toggleApiKey.addEventListener('click', function() {
            const apiKeyInput = document.getElementById('weather_api_key');
            const type = apiKeyInput.getAttribute('type');

            if (type === 'password') {
                apiKeyInput.setAttribute('type', 'text');
                this.innerHTML = '<i class="fas fa-eye-slash"></i>';
            } else {
                apiKeyInput.setAttribute('type', 'password');
                this.innerHTML = '<i class="fas fa-eye"></i>';
            }
        });
    }

    // Brightness slider
    const brightnessSlider = document.getElementById('brightness');
    const brightnessValue = document.querySelector('.brightness-value');

    if (brightnessSlider && brightnessValue) {
        brightnessSlider.addEventListener('input', function() {
            brightnessValue.textContent = this.value + '%';
        });
    }

    // Plugin cycling toggle
    const cycleEnabledToggle = document.getElementById('cycle_enabled');
    const cyclePluginsGrid = document.querySelector('.cycle-plugins-grid');
    const displayDurationInput = document.getElementById('display_duration');

    if (cycleEnabledToggle) {
        // Function to toggle the disabled state of cycling options
        function updateCyclingOptionsState() {
            const isEnabled = cycleEnabledToggle.checked;

            // Enable/disable plugin checkboxes
            if (cyclePluginsGrid) {
                const pluginCheckboxes = cyclePluginsGrid.querySelectorAll('input[type="checkbox"]');
                pluginCheckboxes.forEach(checkbox => {
                    checkbox.disabled = !isEnabled;
                });

                // Add/remove disabled styling
                if (isEnabled) {
                    cyclePluginsGrid.classList.remove('disabled');
                } else {
                    cyclePluginsGrid.classList.add('disabled');
                }
            }

            // Enable/disable duration input
            if (displayDurationInput) {
                displayDurationInput.disabled = !isEnabled;
            }
        }

        // Set initial state
        updateCyclingOptionsState();

        // Update state when toggle changes
        cycleEnabledToggle.addEventListener('change', updateCyclingOptionsState);
    }

    // Form validation for cycling settings
    const cyclingForm = document.querySelector('form[action*="update_plugin_cycle"]');
    if (cyclingForm) {
        cyclingForm.addEventListener('submit', function(e) {
            const isEnabled = document.getElementById('cycle_enabled').checked;

            if (isEnabled) {
                // Check if at least one plugin is selected
                const selectedPlugins = document.querySelectorAll('input[name="cycle_plugins"]:checked');
                if (selectedPlugins.length === 0) {
                    e.preventDefault();
                    alert('Please select at least one plugin for cycling.');
                }
            }
        });
    }
});