document.addEventListener('DOMContentLoaded', function () {
  // Dark/Light theme toggle
  const themeToggle = document.getElementById('theme-toggle');
  const storedTheme = localStorage.getItem('theme');

  // Apply stored theme on page load
  if (storedTheme === 'dark') {
    document.body.classList.add('dark-theme');
    themeToggle.checked = true;
  }

  // Toggle theme on switch change
  themeToggle.addEventListener('change', function () {
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
  mainTabs.forEach((tab) => {
    tab.addEventListener('click', function () {
      const tabId = this.getAttribute('data-main-tab');

      // Remove active class from all tabs
      mainTabs.forEach((t) => t.classList.remove('active'));

      // Add active class to current tab
      this.classList.add('active');

      // Hide all tab content
      mainTabContents.forEach((content) => (content.style.display = 'none'));

      // Show selected tab content
      document.getElementById(`${tabId}-content`).style.display = 'block';

      // Store the active tab in session storage
      localStorage.setItem('activeMainTab', tabId);
    });
  });

  // GIF subtabs functionality
  const gifTabs = document.querySelectorAll('.gif-tab');
  const gifTabContents = document.querySelectorAll('.tab-content');

  gifTabs.forEach((tab) => {
    tab.addEventListener('click', function () {
      const tabId = this.getAttribute('data-tab');

      // Remove active class from all tabs
      gifTabs.forEach((t) => t.classList.remove('active'));

      // Add active class to current tab
      this.classList.add('active');

      // Hide all tab content
      gifTabContents.forEach((content) => content.classList.remove('active'));

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
  flashMessages.forEach((message) => {
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
    toggleApiKey.addEventListener('click', function () {
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
    brightnessSlider.addEventListener('input', function () {
      brightnessValue.textContent = this.value + '%';
    });
  }

  // Add this to your existing JavaScript, or replace the cycling toggle handling section:

  // Plugin cycling toggle - with debug
  console.log('Loading plugin cycling toggle handlers');
  const cycleEnabledToggle = document.getElementById('cycle_enabled');
  const cyclePluginsGrid = document.querySelector('.cycle-plugins-grid');
  const displayDurationInput = document.getElementById('display_duration');

  if (cycleEnabledToggle) {
    console.log('Found cycle_enabled toggle element');

    // Function to toggle the disabled state of cycling options
    function updateCyclingOptionsState() {
      console.log('Toggle changed: ' + cycleEnabledToggle.checked);
      const isEnabled = cycleEnabledToggle.checked;

      // Enable/disable plugin checkboxes
      if (cyclePluginsGrid) {
        console.log('Updating plugin checkboxes state');
        const pluginCheckboxes = cyclePluginsGrid.querySelectorAll(
          'input[type="checkbox"]'
        );
        pluginCheckboxes.forEach((checkbox) => {
          checkbox.disabled = !isEnabled;
        });

        // Add/remove disabled styling
        if (isEnabled) {
          cyclePluginsGrid.classList.remove('disabled');
        } else {
          cyclePluginsGrid.classList.add('disabled');
        }
      } else {
        console.log('Could not find cycle plugins grid');
      }

      // Enable/disable duration input
      if (displayDurationInput) {
        console.log('Updating duration input state');
        displayDurationInput.disabled = !isEnabled;
      } else {
        console.log('Could not find display duration input');
      }
    }

    // Set initial state
    console.log(
      'Setting initial state, isChecked: ' + cycleEnabledToggle.checked
    );
    updateCyclingOptionsState();

    // Update state when toggle changes
    cycleEnabledToggle.addEventListener('change', function (e) {
      console.log('Toggle checkbox change event fired');
      updateCyclingOptionsState();
    });

    // Add click handler directly to the toggle-slider element
    const toggleSlider = document.querySelector('.toggle-slider');
    if (toggleSlider) {
      console.log('Found toggle slider, adding click handler');
      toggleSlider.addEventListener('click', function (e) {
        console.log('Toggle slider clicked');
        // Toggle the checkbox
        cycleEnabledToggle.checked = !cycleEnabledToggle.checked;
        // Trigger the change event manually
        const event = new Event('change');
        cycleEnabledToggle.dispatchEvent(event);
      });
    } else {
      console.log('Could not find toggle slider');
    }
  } else {
    console.log('Could not find cycle_enabled toggle element');
  }

  // Form validation for cycling settings
  const cyclingForm = document.querySelector(
    'form[action*="update_plugin_cycle"]'
  );
  if (cyclingForm) {
    cyclingForm.addEventListener('submit', function (e) {
      const isEnabled = document.getElementById('cycle_enabled').checked;

      if (isEnabled) {
        // Check if at least one plugin is selected
        const selectedPlugins = document.querySelectorAll(
          'input[name="cycle_plugins"]:checked'
        );
        if (selectedPlugins.length === 0) {
          e.preventDefault();
          alert('Please select at least one plugin for cycling.');
        }
      }
    });
  }
});

// Add this to your JavaScript file
document.addEventListener('DOMContentLoaded', function() {
    const cycleEnabled = document.getElementById('cycle_enabled');
    const pluginCheckboxes = document.querySelectorAll('.cycle-plugins-grid input[type="checkbox"]');
    const durationInput = document.getElementById('display_duration');
    const pluginsGrid = document.querySelector('.cycle-plugins-grid');

    if (cycleEnabled) {
        // Handle change event
        cycleEnabled.addEventListener('change', function() {
            // Update plugin checkboxes state
            pluginCheckboxes.forEach(checkbox => {
                checkbox.disabled = !this.checked;
            });

            // Update duration input state
            if (durationInput) {
                durationInput.disabled = !this.checked;
            }

            // Update grid styling
            if (pluginsGrid) {
                if (this.checked) {
                    pluginsGrid.classList.remove('disabled');
                } else {
                    pluginsGrid.classList.add('disabled');
                }
            }

            console.log('Plugin cycling toggle changed:', this.checked);
        });

        // Set initial state
        cycleEnabled.dispatchEvent(new Event('change'));
    }
});
