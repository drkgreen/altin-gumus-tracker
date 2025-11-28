// Viwa Background Service Worker

console.log('Viwa: Background service worker started');

// Initialize extension on install
chrome.runtime.onInstalled.addListener((details) => {
  console.log('Viwa: Extension installed', details);

  if (details.reason === 'install') {
    // Set default settings
    chrome.storage.sync.set({
      statsEnabled: true,
      imagePreviewEnabled: true,
      autoSaveEnabled: false
    });

    // Set default stats
    chrome.storage.local.set({
      totalMessages: 0,
      totalImages: 0
    });

    console.log('Viwa: Default settings initialized');
  }
});

// Handle messages from content script and popup
chrome.runtime.onMessage.addListener((message, sender, sendResponse) => {
  console.log('Viwa: Message received', message);

  switch (message.action) {
    case 'updateStats':
      // Forward stats update to popup if open
      chrome.runtime.sendMessage(message);
      break;

    case 'downloadImage':
      // Handle image download
      if (message.imageUrl) {
        chrome.downloads.download({
          url: message.imageUrl,
          filename: `viwa_${Date.now()}.jpg`,
          saveAs: true
        });
      }
      break;

    default:
      console.log('Viwa: Unknown action', message.action);
  }

  sendResponse({ success: true });
  return true; // Keep message channel open for async response
});

// Monitor tab updates to inject content script
chrome.tabs.onUpdated.addListener((tabId, changeInfo, tab) => {
  if (changeInfo.status === 'complete' && tab.url && tab.url.includes('web.whatsapp.com')) {
    console.log('Viwa: WhatsApp Web tab detected', tabId);
  }
});

// Keep service worker alive
const keepAlive = () => {
  setInterval(() => {
    chrome.storage.local.get('keepAlive');
  }, 20000);
};

keepAlive();
