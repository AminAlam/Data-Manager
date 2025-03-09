// Background script for Data Manager Google Drive Integration

// Listen for when the extension is installed
chrome.runtime.onInstalled.addListener(() => {
  console.log('Data Manager - Google Drive Integration installed!');
  
  // Add context menu items if the API is available
  try {
    if (chrome.contextMenus) {
      chrome.contextMenus.create({
        id: 'addToDataManager',
        title: 'Add to Data Manager',
        contexts: ['page'],
        documentUrlPatterns: [
          '*://docs.google.com/*',
          '*://sheets.google.com/*',
          '*://slides.google.com/*',
          '*://drive.google.com/file/*'
        ]
      });
    }
  } catch (error) {
    console.error('Error creating context menu:', error);
  }
});

// Handle context menu clicks - only if the API is available
if (chrome.contextMenus) {
  try {
    chrome.contextMenus.onClicked.addListener((info, tab) => {
      if (info.menuItemId === 'addToDataManager') {
        // Open the popup to add the current document
        chrome.action.openPopup();
      }
    });
  } catch (error) {
    console.error('Error setting up context menu click handler:', error);
  }
}

// Listen for messages from content script or popup
chrome.runtime.onMessage.addListener((request, sender, sendResponse) => {
  // You can add additional background functionality here if needed
  if (request.action === 'showNotification') {
    try {
      if (chrome.notifications) {
        chrome.notifications.create({
          type: 'basic',
          iconUrl: 'icons/icon128.png',
          title: 'Data Manager',
          message: request.message
        });
      }
    } catch (error) {
      console.error('Error showing notification:', error);
    }
  }
  
  return true;
}); 