// Background script for Data Manager

// Listen for when the extension is installed
chrome.runtime.onInstalled.addListener(() => {
  console.log('Data Manager installed!');
  
  // Add context menu items if the API is available
  try {
    if (chrome.contextMenus) {
      chrome.contextMenus.create({
        id: 'addToDataManager',
        title: 'Add to Data Manager',
        contexts: ['page']
      });
      
      // Add a separator
      chrome.contextMenus.create({
        id: 'separator1',
        type: 'separator',
        contexts: ['page']
      });
      
      // Add a context menu item for configuration
      chrome.contextMenus.create({
        id: 'configureDataManager',
        title: 'Configure Data Manager',
        contexts: ['page']
      });
    }
  } catch (error) {
    console.error('Error creating context menu:', error);
  }
});

// Handle context menu clicks - only if the API is available
try {
  if (chrome.contextMenus) {
    chrome.contextMenus.onClicked.addListener((info, tab) => {
      try {
        if (info.menuItemId === 'addToDataManager') {
          // Open the popup to add the current document
          if (chrome.action && chrome.action.openPopup) {
            chrome.action.openPopup();
          } else if (chrome.browserAction && chrome.browserAction.openPopup) {
            // Fallback for older Chrome versions
            chrome.browserAction.openPopup();
          }
        } else if (info.menuItemId === 'configureDataManager') {
          // Send a message to the popup to switch to configuration mode
          chrome.storage.local.set({ 'openConfigOnNextOpen': true }, () => {
            if (chrome.runtime.lastError) {
              console.error('Error setting storage:', chrome.runtime.lastError);
            }
            
            if (chrome.action && chrome.action.openPopup) {
              chrome.action.openPopup();
            } else if (chrome.browserAction && chrome.browserAction.openPopup) {
              // Fallback for older Chrome versions
              chrome.browserAction.openPopup();
            }
          });
        }
      } catch (e) {
        console.error('Error in context menu handler:', e);
      }
    });
  }
} catch (error) {
  console.error('Error setting up context menu click handler:', error);
}

// Listen for tab changes to update the popup when it opens
try {
  if (chrome.tabs) {
    chrome.tabs.onActivated.addListener(activeInfo => {
      try {
        // Store the current active tab ID
        chrome.storage.local.set({ 'currentActiveTabId': activeInfo.tabId }, () => {
          if (chrome.runtime.lastError) {
            console.error('Error setting storage:', chrome.runtime.lastError);
          }
        });
      } catch (e) {
        console.error('Error in tab activated handler:', e);
      }
    });

    // Listen for tab updates (URL changes, etc.)
    chrome.tabs.onUpdated.addListener((tabId, changeInfo, tab) => {
      try {
        if (changeInfo.status === 'complete') {
          // Store the current tab information
          chrome.storage.local.set({ 
            'currentTabUrl': tab.url,
            'currentTabTitle': tab.title,
            'urlChanged': true
          }, () => {
            if (chrome.runtime.lastError) {
              console.error('Error setting storage:', chrome.runtime.lastError);
            }
          });
        }
      } catch (e) {
        console.error('Error in tab updated handler:', e);
      }
    });
  }
} catch (error) {
  console.error('Error setting up tab listeners:', error);
}

// Listen for messages from content script or popup
chrome.runtime.onMessage.addListener((request, sender, sendResponse) => {
  try {
    // Handle different message types
    if (request.action === 'showNotification') {
      try {
        if (chrome.notifications) {
          chrome.notifications.create({
            type: 'basic',
            iconUrl: 'icons/icon128.png',
            title: 'Data Manager',
            message: request.message
          }, () => {
            if (chrome.runtime.lastError) {
              console.error('Error showing notification:', chrome.runtime.lastError);
            }
          });
        }
      } catch (error) {
        console.error('Error showing notification:', error);
        sendResponse({ success: false, error: error.message });
      }
    } else if (request.action === 'checkExistingEntries') {
      // We could add functionality here to check for existing entries
      // and return the result, but currently this is handled in the popup
      sendResponse({ success: true, message: 'Request received' });
    } else if (request.action === 'getOpenConfig') {
      // Return whether the configuration should be shown on open
      try {
        chrome.storage.local.get(['openConfigOnNextOpen'], (result) => {
          if (chrome.runtime.lastError) {
            console.error('Error getting storage:', chrome.runtime.lastError);
            sendResponse({ openConfig: false, error: chrome.runtime.lastError.message });
            return;
          }
          
          const openConfig = result.openConfigOnNextOpen || false;
          
          // Clear the flag after reading it
          if (openConfig) {
            chrome.storage.local.remove('openConfigOnNextOpen', () => {
              if (chrome.runtime.lastError) {
                console.error('Error removing storage key:', chrome.runtime.lastError);
              }
            });
          }
          
          sendResponse({ openConfig });
        });
        
        // Indicate that sendResponse will be called asynchronously
        return true;
      } catch (error) {
        console.error('Error handling getOpenConfig:', error);
        sendResponse({ openConfig: false, error: error.message });
      }
    } else if (request.action === 'getTabChanged') {
      // Check if the URL has changed since last popup open
      try {
        chrome.storage.local.get(['urlChanged', 'currentTabUrl', 'currentTabTitle'], (result) => {
          if (chrome.runtime.lastError) {
            console.error('Error getting storage:', chrome.runtime.lastError);
            sendResponse({ 
              urlChanged: false, 
              currentTabUrl: '', 
              currentTabTitle: '',
              error: chrome.runtime.lastError.message
            });
            return;
          }
          
          sendResponse({
            urlChanged: result.urlChanged || false,
            currentTabUrl: result.currentTabUrl || '',
            currentTabTitle: result.currentTabTitle || ''
          });
          
          // Reset the flag after reading it
          if (result.urlChanged) {
            chrome.storage.local.set({ 'urlChanged': false }, () => {
              if (chrome.runtime.lastError) {
                console.error('Error setting storage:', chrome.runtime.lastError);
              }
            });
          }
        });
        
        // Indicate that sendResponse will be called asynchronously
        return true;
      } catch (error) {
        console.error('Error handling getTabChanged:', error);
        sendResponse({ 
          urlChanged: false, 
          currentTabUrl: '', 
          currentTabTitle: '',
          error: error.message
        });
      }
    } else {
      sendResponse({ success: false, error: 'Unknown action' });
    }
  } catch (error) {
    console.error('Error handling message:', error);
    try {
      sendResponse({ success: false, error: 'Error processing request: ' + error.message });
    } catch (e) {
      console.error('Error sending response:', e);
    }
  }
  
  return true;
}); 