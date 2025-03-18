// DOM elements
let configForm = document.getElementById('configForm');
let addEntryForm = document.getElementById('addEntryForm');
let apiConfigForm = document.getElementById('apiConfigForm');
let entryForm = document.getElementById('entryForm');
let configButton = document.getElementById('configButton');
let addNewButton = document.getElementById('addNewButton');
let messageBoxConfig = document.getElementById('configMessageBox');
let messageBoxEntry = document.getElementById('entryMessageBox');
let submitButton = document.getElementById('submitButton');
let closeEntriesBtn = document.getElementById('closeEntriesBtn');

// Document info elements
let docTitle = document.getElementById('docTitle');
let docType = document.getElementById('docType');
let docUrl = document.getElementById('docUrl');
let entryName = document.getElementById('entryName');

// Configuration form fields
let serverUrl = document.getElementById('serverUrl');
let username = document.getElementById('username');
let apiKey = document.getElementById('apiKey');

// Current tab information
let currentTab = null;
// Track if we're updating an existing entry
let isUpdateMode = false;
let currentEntryId = null;
// Store all entries for the current URL
let allEntriesForUrl = [];
// Security token for sensitive operations
let csrfToken = null;

// Add CSS for loading animations
const styleElement = document.createElement('style');
styleElement.textContent = `
  @keyframes fadeIn {
    from { opacity: 0; }
    to { opacity: 1; }
  }
  
  @keyframes slideInFromRight {
    from { transform: translateX(20px); opacity: 0; }
    to { transform: translateX(0); opacity: 1; }
  }
  
  @keyframes highlightBackground {
    0% { background-color: transparent; }
    30% { background-color: rgba(52, 168, 83, 0.1); }
    100% { background-color: transparent; }
  }
  
  .fade-in {
    animation: fadeIn 0.3s ease-in-out forwards;
  }
  
  .slide-in {
    animation: slideInFromRight 0.4s ease-out forwards;
  }
  
  .highlight-field {
    animation: highlightBackground 1.5s ease-out forwards;
  }
  
  .spinner-border {
    display: inline-block;
    width: 1rem;
    height: 1rem;
    vertical-align: text-bottom;
    border: 0.2em solid currentColor;
    border-right-color: transparent;
    border-radius: 50%;
    animation: spinner-border .75s linear infinite;
  }
  
  @keyframes spinner-border {
    to { transform: rotate(360deg); }
  }
`;
document.head.appendChild(styleElement);

// Initialize popup
document.addEventListener('DOMContentLoaded', async () => {
  try {
    // Initialize DOM elements if not initialized
    initializeDOMReferences();
    
    // Get current tab
    const tabs = await chrome.tabs.query({ active: true, currentWindow: true });
    if (!tabs || tabs.length === 0) {
      console.error('No active tab found');
      showMessage('Error: Could not access the current tab', 'error');
      return;
    }
    
    currentTab = tabs[0];
    
    // Check if we're on a Google Drive document
    const isGoogleDoc = isGoogleDriveDocument(currentTab.url);
    
    // Load saved configuration
    loadConfiguration();
    
    // Setup event listeners
    setupEventListeners();
    
    // Generate CSRF token for this session
    csrfToken = generateRandomToken();
    
    // Check if the URL has changed since last time
    chrome.runtime.sendMessage({ action: 'getTabChanged' }, async (response) => {
      if (chrome.runtime.lastError) {
        console.warn('Error checking tab change:', chrome.runtime.lastError);
      } else if (response && response.urlChanged) {
        console.log('URL has changed - fetching info for new tab');
        // Update our tab info if needed
        if (response.currentTabUrl && response.currentTabUrl !== currentTab.url) {
          currentTab.url = response.currentTabUrl;
        }
        if (response.currentTabTitle && response.currentTabTitle !== currentTab.title) {
          currentTab.title = response.currentTabTitle;
        }
      }
      
      // Check if we should open the configuration page directly
      chrome.runtime.sendMessage({ action: 'getOpenConfig' }, async (configResponse) => {
        if (chrome.runtime.lastError) {
          console.warn('Error checking config flag:', chrome.runtime.lastError);
          initializeUI(isGoogleDoc);
        } else if (configResponse && configResponse.openConfig === true) {
          // Show configuration page
          if (configForm) configForm.classList.remove('hidden');
          if (addEntryForm) addEntryForm.classList.add('hidden');
        } else {
          // Initialize UI based on configuration and current page
          initializeUI(isGoogleDoc);
          
          // If we have a complete configuration, check for existing entries
          const config = getStoredConfiguration();
          if (config.isComplete) {
            // If on a supported document, fetch document info
            fetchDocumentInfo();
            
            // Show a loading indicator while we check for existing entries
            showLoadingIndicator(true);
            
            // Check if there are existing entries for this URL
            try {
              await checkExistingEntries(currentTab.url);
            } finally {
              // Hide loading indicator
              showLoadingIndicator(false);
            }
          }
        }
      });
    });
    
  } catch (error) {
    console.error('Error initializing extension:', error);
    showMessage('An error occurred while initializing the extension. Please try again.', 'error');
    
    // Log more detailed information about the error
    console.error('Error details:', error.message);
    console.error('Error stack:', error.stack);
    
    // Ensure at least the basic UI is visible even if there's an error
    safelyShowUI();
  }
});

// Safely show the basic UI in case of errors
function safelyShowUI() {
  try {
    // Show the configuration form if possible
    if (document.getElementById('configForm')) {
      document.getElementById('configForm').classList.remove('hidden');
    }
    
    // Hide any loading indicators
    if (document.getElementById('loadingIndicator')) {
      document.getElementById('loadingIndicator').classList.add('hidden');
    }
  } catch (err) {
    console.error('Error showing fallback UI:', err);
  }
}

// Ensure all DOM references are initialized
function initializeDOMReferences() {
  try {
    // Check if essential DOM elements are available
    configForm = document.getElementById('configForm') || configForm;
    addEntryForm = document.getElementById('addEntryForm') || addEntryForm;
    apiConfigForm = document.getElementById('apiConfigForm') || apiConfigForm;
    entryForm = document.getElementById('entryForm') || entryForm;
    configButton = document.getElementById('configButton') || configButton;
    addNewButton = document.getElementById('addNewButton') || addNewButton;
    messageBoxConfig = document.getElementById('configMessageBox') || messageBoxConfig;
    messageBoxEntry = document.getElementById('entryMessageBox') || messageBoxEntry;
    submitButton = document.getElementById('submitButton') || submitButton;
    closeEntriesBtn = document.getElementById('closeEntriesBtn') || closeEntriesBtn;
    
    // Document info elements
    docTitle = document.getElementById('docTitle') || docTitle;
    docType = document.getElementById('docType') || docType;
    docUrl = document.getElementById('docUrl') || docUrl;
    entryName = document.getElementById('entryName') || entryName;
    
    // Configuration form fields
    serverUrl = document.getElementById('serverUrl') || serverUrl;
    username = document.getElementById('username') || username;
    apiKey = document.getElementById('apiKey') || apiKey;
    
    // Check if we have the critical elements
    let missingElements = [];
    if (!addEntryForm) missingElements.push('addEntryForm');
    if (!configForm) missingElements.push('configForm');
    
    if (missingElements.length > 0) {
      console.error('Missing critical DOM elements:', missingElements.join(', '));
      
      // Try to create fallback elements if they don't exist
      if (!configForm && document.body) {
        configForm = document.createElement('div');
        configForm.id = 'configForm';
        document.body.appendChild(configForm);
        console.log('Created fallback configForm element');
      }
      
      if (!addEntryForm && document.body) {
        addEntryForm = document.createElement('div');
        addEntryForm.id = 'addEntryForm';
        document.body.appendChild(addEntryForm);
        console.log('Created fallback addEntryForm element');
      }
      
      // If we still have missing critical elements, throw an error
      if (!addEntryForm || !configForm) {
        throw new Error('Missing essential UI elements: form containers not found');
      }
    }
    
    // Log which UI elements were found
    console.log('UI elements initialized:', {
      configForm: !!configForm,
      addEntryForm: !!addEntryForm,
      apiConfigForm: !!apiConfigForm,
      entryForm: !!entryForm,
      configButton: !!configButton,
      addNewButton: !!addNewButton,
      closeEntriesBtn: !!closeEntriesBtn
    });
  } catch (error) {
    console.error('Error initializing DOM references:', error);
    throw new Error('Failed to initialize DOM references: ' + error.message);
  }
}

// Generate a random token for CSRF protection
function generateRandomToken() {
  const array = new Uint32Array(4);
  window.crypto.getRandomValues(array);
  return Array.from(array, x => x.toString(16).padStart(8, '0')).join('');
}

// Setup all event listeners
function setupEventListeners() {
  // Configuration form submission
  apiConfigForm.addEventListener('submit', (e) => {
    e.preventDefault();
    saveConfiguration();
  });
  
  // Entry form submission
  entryForm.addEventListener('submit', (e) => {
    e.preventDefault();
    submitEntry();
  });
  
  // Config button click
  configButton.addEventListener('click', toggleConfigForm);
  
  // Add new button click
  addNewButton.addEventListener('click', switchToNewEntryMode);
  
  // Add event listener for the "View All Entries" button
  const viewAllEntriesBtn = document.getElementById('viewAllEntriesBtn');
  if (viewAllEntriesBtn) {
    viewAllEntriesBtn.addEventListener('click', displayAllEntries);
  }
  
  // Add event listener to close entries list
  if (closeEntriesBtn) {
    closeEntriesBtn.addEventListener('click', () => {
      const entriesListContainer = document.getElementById('entriesListContainer');
      if (entriesListContainer) {
        entriesListContainer.classList.add('hidden');
      }
    });
  }
  
  // Add event listener for entries list (for selecting an entry to edit)
  const entriesList = document.getElementById('entriesList');
  if (entriesList) {
    entriesList.addEventListener('click', (e) => {
      const entryId = e.target.closest('li')?.dataset?.entryId;
      if (entryId) {
        const entry = allEntriesForUrl.find(entry => (entry.id || entry.hash_id) === entryId);
        if (entry) {
          populateFormWithExistingEntry(entry);
          
          // Hide the entries list
          const entriesListContainer = document.getElementById('entriesListContainer');
          if (entriesListContainer) {
            entriesListContainer.classList.add('hidden');
          }
        }
      }
    });
  }
}

// Toggle configuration form visibility
function toggleConfigForm() {
  if (configForm.classList.contains('hidden')) {
    // Show config form
    configForm.classList.remove('hidden');
    addEntryForm.classList.add('hidden');
  } else {
    // Hide config form
    configForm.classList.add('hidden');
    addEntryForm.classList.remove('hidden');
  }
}

// Initialize UI based on saved configuration and current page
function initializeUI(isGoogleDoc) {
  try {
    const config = getStoredConfiguration();
    
    // If configuration is complete, always show the entry form first
    if (config.isComplete) {
      if (configForm) configForm.classList.add('hidden');
      if (addEntryForm) addEntryForm.classList.remove('hidden');
      
      // If not on a Google document, show a warning
      if (!isGoogleDoc) {
        showMessage('Not a Google Drive document. Navigate to a Google Doc, Sheet, or Slide to add it to Data Manager.', 'error');
      }
    }
    // If configuration is incomplete
    else {
      if (configForm) configForm.classList.remove('hidden');
      if (addEntryForm) addEntryForm.classList.add('hidden');
    }
    
    console.log('UI initialized, config complete:', config.isComplete, 'is Google doc:', isGoogleDoc);
  } catch (error) {
    console.error('Error initializing UI:', error);
    // Fallback to basic state
    safelyShowUI();
  }
}

// Switch to new entry mode
function switchToNewEntryMode() {
  isUpdateMode = false;
  currentEntryId = null;
  
  // Clear form fields
  entryName.value = '';
  document.getElementById('notes').value = '';
  document.getElementById('tags').value = '';
  
  // Update button text
  submitButton.textContent = 'Add to Data Manager';
  
  // Hide the last updated timestamp
  const lastUpdatedContainer = document.getElementById('lastUpdatedContainer');
  if (lastUpdatedContainer) {
    lastUpdatedContainer.classList.add('hidden');
  }
  
  // Hide entries list if visible
  const entriesListContainer = document.getElementById('entriesListContainer');
  if (entriesListContainer) {
    entriesListContainer.classList.add('hidden');
  }

  
  // Show message
  showMessage('Ready to create a new entry.', 'info');
  
  // Make sure the entry form is visible
  configForm.classList.add('hidden');
  addEntryForm.classList.remove('hidden');
  
  // Get document info again
  fetchDocumentInfo();
}

// Display all entries for the current URL
function displayAllEntries() {
  // Get entries list container
  const entriesListContainer = document.getElementById('entriesListContainer');
  const entriesList = document.getElementById('entriesList');
  
  if (!entriesListContainer || !entriesList) {
    console.error('Entries list container not found');
    return false;
  }
  
  // Clear current list
  entriesList.innerHTML = '';
  
  if (!Array.isArray(allEntriesForUrl) || allEntriesForUrl.length === 0) {
    // No entries found
    const noEntries = document.createElement('li');
    noEntries.textContent = 'No entries found for this URL.';
    entriesList.appendChild(noEntries);
  } else {
    try {
      // Sort entries by date (newest first), handling invalid dates gracefully
      const sortedEntries = [...allEntriesForUrl].sort((a, b) => {
        try {
          const dateA = a.date ? new Date(a.date) : new Date(0);
          const dateB = b.date ? new Date(b.date) : new Date(0);
          
          // Check if dates are valid
          if (isNaN(dateA.getTime())) return 1;
          if (isNaN(dateB.getTime())) return -1;
          
          return dateB - dateA;
        } catch (error) {
          console.error('Error comparing dates:', error);
          return 0;
        }
      });
      
      // Add each entry to the list
      sortedEntries.forEach(entry => {
        if (!entry) return; // Skip if entry is null or undefined
        
        const entryId = entry.id || entry.hash_id;
        if (!entryId) return; // Skip if no ID is available
        
        const entryItem = document.createElement('li');
        entryItem.dataset.entryId = entryId;
        
        // Sanitize entry data for display
        const safeName = sanitizeHTML(entry.entry_name || 'Unnamed Entry');
        const safeDate = sanitizeHTML(formatDate(entry.date) || 'Unknown date');
        
        entryItem.innerHTML = `
          <strong>${safeName}</strong>
          <span class="entry-date">${safeDate}</span>
        `;
        entriesList.appendChild(entryItem);
      });
    } catch (error) {
      console.error('Error displaying entries:', error);
      const errorEntry = document.createElement('li');
      errorEntry.textContent = 'Error displaying entries. Please try again.';
      entriesList.appendChild(errorEntry);
    }
  }
  
  // Show the entries list
  entriesListContainer.classList.remove('hidden');
  return true;
}

// Format date for display
function formatDate(dateStr) {
  if (!dateStr) return '';
  
  try {
    const date = new Date(dateStr);
    
    // Check if date is valid
    if (isNaN(date.getTime())) {
      return dateStr;
    }
    
    return date.toLocaleString();
  } catch (error) {
    console.error('Error formatting date:', error);
    return dateStr;
  }
}

// Sanitize HTML to prevent XSS
function sanitizeHTML(text) {
  if (!text) return '';
  
  return String(text)
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;')
    .replace(/'/g, '&#039;');
}

// Check if URL is a Google Drive document
function isGoogleDriveDocument(url) {
  if (!url) return false;
  
  return url.includes('docs.google.com') || 
         url.includes('sheets.google.com') || 
         url.includes('slides.google.com') || 
         url.includes('drive.google.com');
}

// Get document type from URL
function getDocumentType(url) {
  if (!url) return 'Unknown';
  
  if (url.includes('docs.google.com')) return 'Google Doc';
  if (url.includes('sheets.google.com')) return 'Google Sheet';
  if (url.includes('slides.google.com')) return 'Google Slide';
  if (url.includes('drive.google.com')) return 'Google Drive';
  
  return 'Web Page';
}

// Fetch document information from the current tab
function fetchDocumentInfo() {
  try {
    const isGoogleDoc = isGoogleDriveDocument(currentTab.url);
    
    // Set initial values with tab title as fallback
    if (isGoogleDoc) {
      updateDocumentInfo(currentTab.title || 'Loading...', getDocumentType(currentTab.url), currentTab.url);
      
      // Request document title from content script (only works on Google Docs)
      chrome.tabs.sendMessage(currentTab.id, { action: 'getDocumentInfo' }, (response) => {
        if (chrome.runtime.lastError) {
          console.warn('Error sending message:', chrome.runtime.lastError);
          // Still use tab title as fallback
          updateDocumentInfo(currentTab.title || 'Untitled Document', getDocumentType(currentTab.url), currentTab.url);
          return;
        }
        
        if (response && response.title) {
          // Use response from content script
          updateDocumentInfo(response.title, getDocumentType(currentTab.url), currentTab.url);
        } else {
          // Fallback to tab title
          updateDocumentInfo(currentTab.title || 'Untitled Document', getDocumentType(currentTab.url), currentTab.url);
        }
      });
    } else {
      // For non-Google docs, just use the tab title and info
      updateDocumentInfo(currentTab.title || 'Current Page', 'Web Page', currentTab.url);
    }
  } catch (error) {
    console.error('Error fetching document info:', error);
    updateDocumentInfo(currentTab.title || 'Untitled Document', getDocumentType(currentTab.url), currentTab.url);
  }
}

// Update document info in the UI
function updateDocumentInfo(title, type, url) {
  if (docTitle) docTitle.textContent = title;
  if (docType) docType.textContent = type;
  if (docUrl) docUrl.textContent = url;
  // Only update the entry name if it's empty or we're not in update mode
  if (entryName && (!entryName.value.trim() || !isUpdateMode)) {
    entryName.value = title;
  }
}

// Load configuration from storage
function loadConfiguration() {
  try {
    chrome.storage.sync.get(['serverUrl', 'username', 'apiKey'], (result) => {
      if (result.serverUrl) serverUrl.value = result.serverUrl;
      if (result.username) username.value = result.username;
      if (result.apiKey) apiKey.value = result.apiKey;
    });
  } catch (error) {
    console.error('Error loading configuration:', error);
  }
}

// Get stored configuration
function getStoredConfiguration() {
  return {
    serverUrl: serverUrl.value.trim(),
    username: username.value.trim(),
    apiKey: apiKey.value.trim(),
    isComplete: !!(serverUrl.value.trim() && username.value.trim() && apiKey.value.trim())
  };
}

// Save configuration to storage
function saveConfiguration() {
  const config = {
    serverUrl: serverUrl.value.trim(),
    username: username.value.trim(),
    apiKey: apiKey.value.trim()
  };
  
  if (!config.serverUrl || !config.username || !config.apiKey) {
    showMessage('All fields are required', 'error', 'config');
    return;
  }
  
  try {
    chrome.storage.sync.set(config, () => {
      if (chrome.runtime.lastError) {
        console.error('Error saving configuration:', chrome.runtime.lastError);
        showMessage('Error saving configuration: ' + chrome.runtime.lastError.message, 'error', 'config');
        return;
      }
      
      showMessage('Configuration saved successfully', 'success', 'config');
      
      // After a short delay, switch to the add entry form
      setTimeout(() => {
        configForm.classList.add('hidden');
        addEntryForm.classList.remove('hidden');
        
        // If we're on a Google Doc, fetch document info and check for existing entries
        if (isGoogleDriveDocument(currentTab.url)) {
          fetchDocumentInfo();
          checkExistingEntries(currentTab.url);
        }
      }, 1000);
    });
  } catch (error) {
    console.error('Error saving configuration:', error);
    showMessage('Error saving configuration: ' + error.message, 'error', 'config');
  }
}

// Check for existing entries with the same URL
async function checkExistingEntries(url) {

  if (!url) {
    console.error('No URL provided to checkExistingEntries');
    return false;
  }
  
  const config = getStoredConfiguration();
  
  if (!config.isComplete) {
    console.log('Configuration not complete, skipping entry check');
    return false; // Can't check entries without proper configuration
  }
  
  try {
    showMessage('Checking for existing entries...', 'info');
    
    // Prepare API URL
    let apiUrl = config.serverUrl;
    const isLocalhost = apiUrl.includes('localhost') || apiUrl.includes('127.0.0.1');
    
    // Ensure proper protocol
    if (!apiUrl.startsWith('http')) {
      apiUrl = isLocalhost ? 'http://' + apiUrl : 'https://' + apiUrl;
    } else if (isLocalhost && apiUrl.startsWith('https://')) {
      apiUrl = 'http://' + apiUrl.substring(8);
    }
    
    apiUrl = apiUrl.replace(/\/$/, '') + '/api/browser_addon/get_entries_by_url';
    
    // Prepare data
    const data = {
      username: config.username,
      api_key: config.apiKey,
      url: url,
      csrf_token: csrfToken
    };
    
    console.log('Checking for existing entries at:', apiUrl);
    
    // Use XMLHttpRequest with a timeout
    const result = await new Promise((resolve, reject) => {
      const xhr = new XMLHttpRequest();
      xhr.timeout = 10000; // 10 seconds
      
      // Set up a safety timeout in case the XHR gets stuck
      const safetyTimeout = setTimeout(() => {
        console.warn('Safety timeout triggered for XHR request');
        resolve({ success: false, entries: [], error: 'Request timed out' });
      }, 12000);
      
      xhr.onload = function() {
        clearTimeout(safetyTimeout);
        
        if (xhr.status >= 200 && xhr.status < 300) {
          try {
            const result = JSON.parse(xhr.responseText);
            console.log('Server response for existing entries:', result);
            resolve(result);
          } catch (parseError) {
            console.error('Error parsing server response:', parseError);
            resolve({ success: false, entries: [], error: 'Invalid JSON response' });
          }
        } else {
          console.error('Server returned error status:', xhr.status);
          resolve({ success: false, entries: [], error: `Server error: ${xhr.status}` });
        }
      };
      
      xhr.onerror = function() {
        clearTimeout(safetyTimeout);
        console.error('Network error occurred when checking existing entries');
        resolve({ success: false, entries: [], error: 'Network error' });
      };
      
      xhr.ontimeout = function() {
        clearTimeout(safetyTimeout);
        console.error('Request timed out when checking existing entries');
        resolve({ success: false, entries: [], error: 'Request timed out' });
      };
      
      try {
        xhr.open('POST', apiUrl);
        xhr.setRequestHeader('Content-Type', 'application/json');
        xhr.send(JSON.stringify(data));
      } catch (error) {
        clearTimeout(safetyTimeout);
        console.error('Error sending request:', error);
        resolve({ success: false, entries: [], error: 'Error sending request' });
      }
    });
    
    // Process the result
    if (result && result.success && Array.isArray(result.entries) && result.entries.length > 0) {
      // Store all entries
      allEntriesForUrl = result.entries.filter(entry => entry); // Filter out null/undefined entries
      
      if (allEntriesForUrl.length === 0) {
        console.log('All entries were filtered out as invalid');
        showMessage('No existing entries found for this URL. Create a new entry.', 'info');
        return false;
      }
      
      try {
        // Sort entries by date to get the most recent one
        const sortedEntries = [...allEntriesForUrl].sort((a, b) => {
          const dateA = new Date(a.date || 0);
          const dateB = new Date(b.date || 0);
          
          if (isNaN(dateA.getTime())) return 1;
          if (isNaN(dateB.getTime())) return -1;
          
          return dateB - dateA;
        });
        
        const mostRecentEntry = sortedEntries[0];
        
        if (mostRecentEntry) {
          // Populate form with existing data
          populateFormWithExistingEntry(mostRecentEntry);
          
          // Show success message
          showMessage('Found existing entry. You are now editing it.', 'success');
          return true;
        }
      } catch (error) {
        console.error('Error processing entries:', error);
      }
    } else {
      // No entries found, or error
      if (result && !result.success) {
        showMessage(`Error checking entries: ${result.error || 'Unknown error'}`, 'error');
      } else {
        showMessage('No existing entries found for this URL. Create a new entry.', 'info');
      }
    }
    
    return false;
  } catch (error) {
    console.error('Error checking existing entries:', error);
    showMessage('Error checking for existing entries. You can still create a new entry.', 'error');
    return false;
  }
}

// Populate form with existing entry data
function populateFormWithExistingEntry(entry) {
  if (!entry) return;
  
  // Set update mode
  isUpdateMode = true;
  currentEntryId = entry.id || entry.hash_id;
  
  // Apply the changes with a slight animation
  setTimeout(() => {
    try {
      // Set form values with animation
      if (entryName) entryName.value = entry.entry_name || '';
      
      const notesElem = document.getElementById('notes');
      if (notesElem) notesElem.value = entry.notes || '';
      
      const tagsElem = document.getElementById('tags');
      if (tagsElem) tagsElem.value = entry.tags || '';
      
      // Add a temporary highlight class to form fields
      if (entryName) {
        entryName.classList.add('highlight-field');
        setTimeout(() => entryName.classList.remove('highlight-field'), 1000);
      }
      
      // Update button text with animation
      if (submitButton) {
        submitButton.classList.add('fade-in');
        submitButton.textContent = 'Update Entry';
      }
      
      // Update the last updated timestamp
      updateLastUpdatedTimestamp(entry.date);
      
    } catch (err) {
      console.error('Error in populateFormWithExistingEntry animation:', err);
    }
  }, 200);
}

// Update the "last updated" timestamp
function updateLastUpdatedTimestamp(dateStr) {
  const lastUpdatedContainer = document.getElementById('lastUpdatedContainer');
  const lastUpdatedTime = document.getElementById('lastUpdatedTime');
  
  if (lastUpdatedContainer && lastUpdatedTime) {
    lastUpdatedTime.textContent = formatDate(dateStr);
    
    // Show with animation
    lastUpdatedContainer.classList.add('fade-in');
    lastUpdatedContainer.classList.remove('hidden');
  }
}

// Submit entry to Data Manager
async function submitEntry() {
  try {
    // Get form data
    const config = getStoredConfiguration();
    
    if (!config.isComplete) {
      showMessage('Please complete configuration first', 'error');
      return;
    }
    
    // Validate input
    if (!entryName || !entryName.value.trim()) {
      showMessage('Entry name is required', 'error');
      return;
    }
    
    try {
      // Disable submit button and show loading state
      if (submitButton) {
        submitButton.disabled = true;
        submitButton.innerHTML = `<span class="spinner-border spinner-border-sm" role="status" aria-hidden="true"></span> ${isUpdateMode ? 'Updating...' : 'Submitting...'}`;
      }
      
      // Log debug info
      console.log('Server URL:', config.serverUrl);
      console.log('Username:', config.username);
      console.log('API Key present:', !!config.apiKey);
      console.log('Is update mode:', isUpdateMode);
      console.log('Current entry ID:', currentEntryId);
      
      // Get current date and time
      const now = new Date();
      const dateStr = now.toISOString().split('T')[0] + ' ' + 
                     now.toTimeString().split(' ')[0];
      
      // Prepare data
      const data = {
        username: config.username,
        api_key: config.apiKey,
        entry_name: entryName.value.trim(),
        url: currentTab.url,
        notes: document.getElementById('notes').value.trim(),
        tags: document.getElementById('tags').value.trim(),
        document_type: getDocumentType(currentTab.url),
        date: dateStr,
        csrf_token: csrfToken
      };
      
      // If updating, add the entry id - this is critical for updates to work
      if (isUpdateMode && currentEntryId) {
        // Use the correct ID field based on what the API expects
        data.id = currentEntryId;
        data.entry_id = currentEntryId; // Some APIs might use entry_id instead
        data.hash_id = currentEntryId;  // Some might use hash_id
        
        console.log('Updating existing entry with ID:', currentEntryId);
      }
      
      // Prepare API URL
      let apiUrl = config.serverUrl;
      const isLocalhost = apiUrl.includes('localhost') || apiUrl.includes('127.0.0.1');
      
      // Ensure proper protocol
      if (!apiUrl.startsWith('http')) {
        apiUrl = isLocalhost ? 'http://' + apiUrl : 'https://' + apiUrl;
      } else if (isLocalhost && apiUrl.startsWith('https://')) {
        apiUrl = 'http://' + apiUrl.substring(8);
      }
      
      // Choose appropriate endpoint based on mode
      const endpoint = isUpdateMode ? '/api/browser_addon/update_entry' : '/api/browser_addon/insert_entry';
      apiUrl = apiUrl.replace(/\/$/, '') + endpoint;
      
      console.log('Full API URL:', apiUrl);
      console.log('Data being sent:', JSON.stringify(data));
      
      showMessage(`${isUpdateMode ? 'Updating' : 'Submitting'} entry...`, 'info');
      
      // Use XMLHttpRequest
      let result = null;
      
      try {
        result = await new Promise((resolve, reject) => {
          const xhr = new XMLHttpRequest();
          
          // Set up timeout
          xhr.timeout = 20000; // 20 seconds
          
          xhr.onload = function() {
            if (xhr.status >= 200 && xhr.status < 300) {
              try {
                const result = JSON.parse(xhr.responseText);
                console.log('Server response:', result);
                resolve(result);
              } catch (parseError) {
                console.error('Error parsing server response:', parseError);
                console.log('Raw response:', xhr.responseText);
                reject(new Error('Invalid response from server'));
              }
            } else {
              console.error('Server returned error status:', xhr.status);
              console.log('Response text:', xhr.responseText);
              reject(new Error(`HTTP error: ${xhr.status}`));
            }
          };
          
          xhr.onerror = function() {
            console.error('Network error occurred');
            reject(new Error('Network error occurred'));
          };
          
          xhr.ontimeout = function() {
            console.error('Request timed out');
            reject(new Error('Request timed out'));
          };
          
          xhr.open('POST', apiUrl);
          xhr.setRequestHeader('Content-Type', 'application/json');
          xhr.send(JSON.stringify(data));
        });
        
        if (result && result.success) {
          // Set ID and update mode
          if (result.id || result.hash_id || result.entry_id) {
            currentEntryId = result.id || result.hash_id || result.entry_id;
            
            // Switch to update mode if we weren't already
            if (!isUpdateMode) {
              isUpdateMode = true;
              showSuccessWithAnimation();
            } else {
              // Was already in update mode
              showMessage(`Entry updated successfully!`, 'success');
            }
            
            // Update the UI to indicate we're now in edit mode
            if (submitButton) {
              submitButton.textContent = 'Update Entry';
            }
            
            // Update last updated timestamp
            updateLastUpdatedTimestamp(dateStr);
          } else {
            // If we got success but no ID, still show success
            showMessage(`Entry ${isUpdateMode ? 'updated' : 'added'} successfully!`, 'success');
          }
          
          // Refresh the list of entries for this URL
          await checkExistingEntries(currentTab.url);
        } else {
          // Show error message
          const errorMessage = result?.error || 'Unknown error occurred';
          showMessage(`Error: ${errorMessage}`, 'error');
          
        }
      } catch (error) {
        console.error('Error submitting entry:', error);
        showMessage(`Error: ${error.message || 'Unknown error occurred'}`, 'error');
      } finally {
        // Re-enable submit button
        try {
          if (submitButton) {
            submitButton.disabled = false;
            submitButton.textContent = isUpdateMode ? 'Update Entry' : 'Add to Data Manager';
          }
        } catch (err) {
          console.warn('Error restoring submit button:', err);
        }
      }
    } catch (error) {
      console.error('Error in submit process:', error);
      showMessage(`Error: ${error.message || 'Unknown error occurred'}`, 'error');
      
      // Re-enable submit button
      if (submitButton) {
        submitButton.disabled = false;
        submitButton.textContent = isUpdateMode ? 'Update Entry' : 'Add to Data Manager';
      }
    }
  } catch (outerError) {
    console.error('Critical error in submitEntry:', outerError);
    showMessage(`A critical error occurred: ${outerError.message || 'Unknown error'}`, 'error');
    
    // Make sure the submit button is re-enabled
    try {
      if (submitButton) {
        submitButton.disabled = false;
        submitButton.textContent = isUpdateMode ? 'Update Entry' : 'Add to Data Manager';
      }
    } catch (buttonError) {
      console.error('Failed to re-enable submit button:', buttonError);
    }
  }
}

// Show success message with animation when switching from add to edit mode
function showSuccessWithAnimation() {
  // First show the basic success message
  showMessage('Entry added successfully!', 'success');
  
  // Add an additional message that we're now in edit mode
  setTimeout(() => {
    showMessage('You are now editing this entry.', 'info');
  }, 2000);
}

// Show a message to the user
function showMessage(message, type = 'info', target = 'entry') {
  try {
    // Select the appropriate message box based on the target
    let messageBox;
    if (target === 'config') {
      messageBox = messageBoxConfig;
    } else {
      messageBox = messageBoxEntry;
    }
    
    // If messageBox isn't available, try to get it again
    if (!messageBox) {
      if (target === 'config') {
        messageBox = document.getElementById('configMessageBox');
      } else {
        messageBox = document.getElementById('entryMessageBox');
      }
      
      // If still not found, log error and return
      if (!messageBox) {
        console.error('Message box not found for target:', target);
        // As a fallback, try to show an alert for critical errors
        if (type === 'error') {
          try {
            alert('Error: ' + message);
          } catch (alertErr) {
            console.error('Failed to show alert:', alertErr);
          }
        }
        return;
      }
    }
    
    // Set the message and type
    messageBox.textContent = message;
    
    // Remove all existing classes
    messageBox.className = 'message-box';
    
    // Add the appropriate type class
    messageBox.classList.add(type);
    
    // Show the message box
    messageBox.classList.remove('hidden');
    
    // Automatically hide info/success messages after a delay
    if (type === 'info' || type === 'success') {
      setTimeout(() => {
        if (messageBox) {
          messageBox.classList.add('hidden');
        }
      }, 5000);
    }
    
    // Also log the message to console
    const logMethod = type === 'error' ? console.error : 
                     type === 'info' ? console.info : console.log;
    logMethod('Message:', message);
  } catch (error) {
    console.error('Error showing message:', error);
    console.error('Message was:', message, 'Type:', type);
    
    // As a last resort, try to use an alert for errors
    if (type === 'error') {
      try {
        alert('Error: ' + message);
      } catch (alertErr) {
        // Nothing more we can do
      }
    }
  }
}

// Helper function to safely perform DOM operations
function safeDOM(callback) {
  try {
    return callback();
  } catch (error) {
    console.error('DOM operation failed:', error);
    return false;
  }
}

// Helper function to safely query DOM elements
function safeQuerySelector(selector, parent = document) {
  try {
    if (!parent) return null;
    return parent.querySelector(selector);
  } catch (error) {
    console.error(`Error querying selector "${selector}":`, error);
    return null;
  }
}

// Helper function to safely manipulate DOM elements
function safeManipulateElement(element, manipulation) {
  if (!element) return false;
  
  try {
    manipulation(element);
    return true;
  } catch (error) {
    console.error('Error manipulating element:', error);
    return false;
  }
}

// Show or hide a loading indicator
function showLoadingIndicator(show) {
  const loadingIndicator = document.getElementById('loadingIndicator');
  
  if (!loadingIndicator) {
    if (!show) return; // Don't create if we're hiding it
    
    // Create the loading indicator
    const indicator = document.createElement('div');
    indicator.id = 'loadingIndicator';
    indicator.className = 'loading-indicator fade-in';
    indicator.style.position = 'absolute';
    indicator.style.top = '50%';
    indicator.style.left = '50%';
    indicator.style.transform = 'translate(-50%, -50%)';
    indicator.style.textAlign = 'center';
    indicator.style.padding = '20px';
    indicator.style.borderRadius = '8px';
    indicator.style.backgroundColor = 'rgba(255, 255, 255, 0.8)';
    indicator.style.boxShadow = '0 2px 10px rgba(0, 0, 0, 0.1)';
    indicator.style.zIndex = '1000';
    
    indicator.innerHTML = `
      <div style="margin-bottom: 10px">
        <span class="spinner-border" style="width: 2rem; height: 2rem;"></span>
      </div>
      <div style="color: #495057; font-weight: 500;">Checking for existing entries...</div>
    `;
    
    document.body.appendChild(indicator);
  } else {
    // Show or hide existing indicator
    if (show) {
      loadingIndicator.classList.remove('hidden');
      loadingIndicator.style.display = 'block';
    } else {
      loadingIndicator.classList.add('hidden');
      loadingIndicator.style.display = 'none';
    }
  }
}

// Add a global error handler to catch uncaught exceptions
window.onerror = function(message, source, lineno, colno, error) {
  console.error('Uncaught error:', message);
  console.error('Source:', source, 'Line:', lineno, 'Column:', colno);
  if (error) {
    console.error('Error object:', error);
    console.error('Stack trace:', error.stack);
  }
  
  // Try to show the error message to the user
  try {
    const errorMessage = `Uncaught error: ${message}`;
    showMessage(errorMessage, 'error');
  } catch (e) {
    console.error('Failed to show error message:', e);
    try {
      alert(`Extension error: ${message}`);
    } catch (alertErr) {
      // Nothing more we can do
    }
  }
  
  return false; // Let the default error handler run as well
}; 