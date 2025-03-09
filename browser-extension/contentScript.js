// Listen for messages from the popup
chrome.runtime.onMessage.addListener((request, sender, sendResponse) => {
  if (request.action === 'getDocumentInfo') {
    const documentInfo = extractDocumentInfo();
    sendResponse(documentInfo);
  }
  return true; // Keep the message channel open for async response
});

// Extract information from the current document
function extractDocumentInfo() {
  const info = {
    title: document.title,
    url: window.location.href
  };
  
  // Try to get a better title based on the type of Google document
  if (window.location.hostname.includes('docs.google.com')) {
    // For Google Docs
    const docTitle = document.querySelector('.docs-title-input');
    if (docTitle) {
      info.title = docTitle.value || document.title;
    }
  } 
  else if (window.location.hostname.includes('sheets.google.com')) {
    // For Google Sheets
    const sheetTitle = document.querySelector('#docs-title-widget input');
    if (sheetTitle) {
      info.title = sheetTitle.value || document.title;
    }
  }
  else if (window.location.hostname.includes('slides.google.com')) {
    // For Google Slides
    const slideTitle = document.querySelector('.docs-title-input');
    if (slideTitle) {
      info.title = slideTitle.value || document.title;
    }
  }
  else if (window.location.hostname.includes('drive.google.com')) {
    // For Google Drive
    const driveTitle = document.querySelector('.Q5txwe');
    if (driveTitle) {
      info.title = driveTitle.innerText || document.title;
    }
  }
  
  // Clean up the title (remove " - Google Docs", etc.)
  info.title = cleanTitle(info.title);
  
  return info;
}

// Clean up document title
function cleanTitle(title) {
  if (!title) return '';
  
  // Remove " - Google Docs", " - Google Sheets", etc.
  return title
    .replace(' - Google Docs', '')
    .replace(' - Google Sheets', '')
    .replace(' - Google Slides', '')
    .replace(' - Google Drive', '')
    .trim();
} 