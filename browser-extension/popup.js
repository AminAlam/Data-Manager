// DOM elements
const configForm = document.getElementById('configForm');
const addEntryForm = document.getElementById('addEntryForm');
const apiConfigForm = document.getElementById('apiConfigForm');
const entryForm = document.getElementById('entryForm');
const toggleAddEntry = document.getElementById('toggleAddEntry');
const toggleConfig = document.getElementById('toggleConfig');
const messageBox = document.getElementById('messageBox');
const submitButton = document.getElementById('submitButton');

// Document info elements
const docTitle = document.getElementById('docTitle');
const docType = document.getElementById('docType');
const docUrl = document.getElementById('docUrl');
const entryName = document.getElementById('entryName');

// Configuration form fields
const serverUrl = document.getElementById('serverUrl');
const username = document.getElementById('username');
const apiKey = document.getElementById('apiKey');

// Current tab information
let currentTab = null;

// Initialize popup
document.addEventListener('DOMContentLoaded', async () => {
  // Get current tab
  const tabs = await chrome.tabs.query({ active: true, currentWindow: true });
  currentTab = tabs[0];
  
  // Check if we're on a Google Drive document
  const isGoogleDoc = isGoogleDriveDocument(currentTab.url);
  
  // Load saved configuration
  loadConfiguration();
  
  // Setup event listeners
  setupEventListeners();
  
  // Initialize UI based on configuration and current page
  initializeUI(isGoogleDoc);
  
  // If on a Google Drive document, fetch document info
  if (isGoogleDoc) {
    fetchDocumentInfo();
  }
});

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
  
  // Toggle between forms
  toggleAddEntry.addEventListener('click', () => {
    configForm.classList.add('hidden');
    addEntryForm.classList.remove('hidden');
  });
  
  toggleConfig.addEventListener('click', () => {
    addEntryForm.classList.add('hidden');
    configForm.classList.remove('hidden');
  });
}

// Initialize UI based on saved configuration and current page
function initializeUI(isGoogleDoc) {
  const config = getStoredConfiguration();
  
  // If configuration is complete and we're on a Google document
  if (config.isComplete && isGoogleDoc) {
    configForm.classList.add('hidden');
    addEntryForm.classList.remove('hidden');
    toggleAddEntry.classList.add('hidden');
  } 
  // If configuration is complete but not on Google document
  else if (config.isComplete && !isGoogleDoc) {
    showMessage('Not a Google Drive document. Navigate to a Google Doc, Sheet, or Slide to add it to Data Manager.', 'error');
    toggleAddEntry.classList.add('hidden');
  }
  // If configuration is incomplete
  else {
    configForm.classList.remove('hidden');
    addEntryForm.classList.add('hidden');
    toggleAddEntry.classList.add('hidden');
  }
}

// Check if URL is a Google Drive document
function isGoogleDriveDocument(url) {
  return (
    url.includes('docs.google.com') || 
    url.includes('sheets.google.com') || 
    url.includes('slides.google.com') ||
    (url.includes('drive.google.com') && url.includes('/file/d/'))
  );
}

// Determine document type from URL
function getDocumentType(url) {
  if (url.includes('docs.google.com')) return 'Google Doc';
  if (url.includes('sheets.google.com')) return 'Google Sheet';
  if (url.includes('slides.google.com')) return 'Google Slides';
  if (url.includes('drive.google.com')) return 'Google Drive File';
  return 'Unknown';
}

// Fetch document information from current tab
function fetchDocumentInfo() {
  chrome.tabs.sendMessage(currentTab.id, { action: 'getDocumentInfo' }, (response) => {
    if (response && response.title) {
      docTitle.textContent = response.title;
      entryName.value = response.title;
    } else {
      // Fallback to tab title if content script doesn't respond
      docTitle.textContent = currentTab.title;
      entryName.value = currentTab.title;
    }
    
    docType.textContent = getDocumentType(currentTab.url);
    docUrl.textContent = currentTab.url;
  });
}

// Load saved configuration into form
function loadConfiguration() {
  chrome.storage.sync.get(['serverUrl', 'username', 'apiKey'], (data) => {
    if (data.serverUrl) serverUrl.value = data.serverUrl;
    if (data.username) username.value = data.username;
    if (data.apiKey) apiKey.value = data.apiKey;
    
    // Check if we have complete configuration
    if (data.serverUrl && data.username && data.apiKey) {
      toggleAddEntry.classList.remove('hidden');
    }
  });
}

// Get stored configuration
function getStoredConfiguration() {
  const config = {
    serverUrl: serverUrl.value,
    username: username.value,
    apiKey: apiKey.value,
    isComplete: false
  };
  
  config.isComplete = !!(config.serverUrl && config.username && config.apiKey);
  return config;
}

// Save configuration
function saveConfiguration() {
  // Ensure the server URL has the correct format
  let serverUrlValue = serverUrl.value.trim();
  
  // Determine if it's a localhost URL
  const isLocalhost = serverUrlValue.includes('localhost') || 
                      serverUrlValue.includes('127.0.0.1');
  
  // Add http:// if missing, using http for localhost and https for others
  if (!serverUrlValue.startsWith('http://') && !serverUrlValue.startsWith('https://')) {
    serverUrlValue = isLocalhost ? 'http://' + serverUrlValue : 'https://' + serverUrlValue;
    serverUrl.value = serverUrlValue;
  }
  
  // Remove trailing slash if present
  if (serverUrlValue.endsWith('/')) {
    serverUrlValue = serverUrlValue.slice(0, -1);
    serverUrl.value = serverUrlValue;
  }
  
  const config = {
    serverUrl: serverUrlValue,
    username: username.value,
    apiKey: apiKey.value
  };
  
  chrome.storage.sync.set(config, () => {
    showMessage('Configuration saved successfully!', 'success', configForm);
    
    // After saving configuration, show the toggle button
    toggleAddEntry.classList.remove('hidden');
    
    // If on a Google Drive document, switch to add entry form
    if (isGoogleDriveDocument(currentTab.url)) {
      setTimeout(() => {
        configForm.classList.add('hidden');
        addEntryForm.classList.remove('hidden');
        fetchDocumentInfo();
      }, 1000);
    }
  });
}

// Submit entry to Data Manager
async function submitEntry() {
  // Get form data
  const config = getStoredConfiguration();
  
  if (!config.isComplete) {
    showMessage('Please complete configuration first', 'error', addEntryForm);
    return;
  }
  
  try {
    // Disable submit button
    submitButton.disabled = true;
    submitButton.textContent = 'Submitting...';
    
    // Show debug info
    console.log('Server URL:', config.serverUrl);
    console.log('Username:', config.username);
    console.log('API Key present:', !!config.apiKey);
    
    // Get current date and time
    const now = new Date();
    const dateStr = now.toISOString().split('T')[0] + ' ' + 
                   now.toTimeString().split(' ')[0];
    
    // Prepare data
    const data = {
      username: config.username,
      api_key: config.apiKey,
      entry_name: entryName.value,
      url: currentTab.url,
      notes: document.getElementById('notes').value,
      tags: document.getElementById('tags').value,
      document_type: getDocumentType(currentTab.url),
      date: dateStr // Add the current date
    };
    
    // Prepare API URL - ensure it's properly formed
    let apiUrl = config.serverUrl;
    const isLocalhost = apiUrl.includes('localhost') || apiUrl.includes('127.0.0.1');
    
    // Ensure proper protocol - USE HTTP FOR LOCALHOST
    if (!apiUrl.startsWith('http')) {
      apiUrl = isLocalhost ? 'http://' + apiUrl : 'https://' + apiUrl;
    } else {
      // Force HTTP for localhost even if saved as HTTPS
      if (isLocalhost && apiUrl.startsWith('https://')) {
        apiUrl = 'http://' + apiUrl.substring(8);
      }
    }
    
    apiUrl = apiUrl.replace(/\/$/, '') + '/api/browser_addon/insert_entry';
    
    console.log('Full API URL:', apiUrl);
    console.log('Data being sent:', JSON.stringify(data));
    
    showMessage(`Connecting to ${apiUrl}...`, 'info', addEntryForm);
    
    // Use XMLHttpRequest as a fallback to fetch (can handle CORS differently)
    await new Promise((resolve, reject) => {
      const xhr = new XMLHttpRequest();
      
      // Set up timeout
      xhr.timeout = 20000; // 20 seconds
      
      xhr.onload = function() {
        if (xhr.status >= 200 && xhr.status < 300) {
          try {
            const result = JSON.parse(xhr.responseText);
            console.log('Server response:', result);
            
            if (result && result.success) {
              // Show success message with suggestion to manually add hash_id
              showMessage(`Entry added successfully! ID: ${result.hash_id || 'unknown'}. You may want to manually add this ID to your document title.`, 'success', addEntryForm);
              
              // Reset form
              document.getElementById('notes').value = '';
              document.getElementById('tags').value = '';
              resolve();
            } else {
              showMessage(`Error: ${result?.message || 'Unknown error from server'}`, 'error', addEntryForm);
              reject(new Error(result?.message || 'Unknown error from server'));
            }
          } catch (parseError) {
            console.error('Error parsing server response:', parseError);
            console.log('Raw response:', xhr.responseText);
            showMessage('Error: Invalid response from server', 'error', addEntryForm);
            reject(parseError);
          }
        } else {
          console.error('Server returned error status:', xhr.status);
          console.log('Response text:', xhr.responseText);
          showMessage(`Server error (${xhr.status}): ${xhr.statusText || 'Unknown error'}`, 'error', addEntryForm);
          reject(new Error(`HTTP error: ${xhr.status}`));
        }
      };
      
      xhr.onerror = function() {
        console.error('Network error occurred');
        console.log('XHR details:', xhr);
        showMessage('Network error: Cannot connect to server. Please check your server URL and that CORS is enabled.', 'error', addEntryForm);
        reject(new Error('Network error'));
      };
      
      xhr.ontimeout = function() {
        console.error('Request timed out');
        showMessage('Error: Request timed out. The server took too long to respond.', 'error', addEntryForm);
        reject(new Error('Request timed out'));
      };
      
      xhr.open('POST', apiUrl);
      xhr.setRequestHeader('Content-Type', 'application/json');
      
      // Send the request
      xhr.send(JSON.stringify(data));
    }).catch(err => {
      console.error('XHR request failed:', err);
      // Error is already handled in the XMLHttpRequest callbacks
    });
    
  } catch (error) {
    console.error('General error:', error);
    showMessage(`Error: ${error.message || 'An unexpected error occurred'}`, 'error', addEntryForm);
  } finally {
    // Always re-enable submit button
    submitButton.disabled = false;
    submitButton.textContent = 'Add to Data Manager';
  }
}

// Display a message in the UI
function showMessage(message, type = 'info', parent = null) {
  // Default to messageBox if no parent specified
  const msgContainer = parent ? parent.querySelector('#messageBox') || messageBox : messageBox;
  
  msgContainer.textContent = message;
  msgContainer.classList.remove('hidden', 'success-message', 'error-message');
  
  if (type === 'success') {
    msgContainer.classList.add('success-message');
  } else if (type === 'error') {
    msgContainer.classList.add('error-message');
  }
  
  // Auto-hide after 5 seconds for success messages
  if (type === 'success') {
    setTimeout(() => {
      msgContainer.classList.add('hidden');
    }, 5000);
  }
} 