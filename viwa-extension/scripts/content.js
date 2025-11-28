// Viwa Content Script for WhatsApp Web

console.log('Viwa: Content script loaded');

// Settings
let settings = {
  statsEnabled: true,
  imagePreviewEnabled: true,
  autoSaveEnabled: false
};

// Stats
let stats = {
  totalMessages: 0,
  totalImages: 0
};

// Initialize extension
async function init() {
  console.log('Viwa: Initializing...');

  // Load settings
  await loadSettings();
  await loadStats();

  // Wait for WhatsApp to load
  waitForWhatsApp();
}

// Load settings
async function loadSettings() {
  try {
    settings = await chrome.storage.sync.get({
      statsEnabled: true,
      imagePreviewEnabled: true,
      autoSaveEnabled: false
    });
    console.log('Viwa: Settings loaded', settings);
  } catch (error) {
    console.error('Viwa: Error loading settings', error);
  }
}

// Load stats
async function loadStats() {
  try {
    stats = await chrome.storage.local.get({
      totalMessages: 0,
      totalImages: 0
    });
    console.log('Viwa: Stats loaded', stats);
  } catch (error) {
    console.error('Viwa: Error loading stats', error);
  }
}

// Wait for WhatsApp to fully load
function waitForWhatsApp() {
  const checkInterval = setInterval(() => {
    // Check if main WhatsApp container is loaded
    const mainContainer = document.querySelector('[data-testid="conversation-panel-body"]') ||
                         document.querySelector('#main') ||
                         document.querySelector('div[role="application"]');

    if (mainContainer) {
      clearInterval(checkInterval);
      console.log('Viwa: WhatsApp loaded, starting features...');
      startFeatures();
    }
  }, 1000);

  // Timeout after 30 seconds
  setTimeout(() => {
    clearInterval(checkInterval);
    console.log('Viwa: Timeout waiting for WhatsApp');
  }, 30000);
}

// Start all features
function startFeatures() {
  if (settings.statsEnabled) {
    showStatsBadge();
  }

  if (settings.imagePreviewEnabled) {
    setupImageDetection();
  }

  observeMessages();
}

// Show stats badge
function showStatsBadge() {
  // Remove existing badge if any
  const existingBadge = document.querySelector('.viwa-stats-badge');
  if (existingBadge) {
    existingBadge.remove();
  }

  const badge = document.createElement('div');
  badge.className = 'viwa-stats-badge';
  badge.innerHTML = `📊 ${stats.totalImages} resim`;
  badge.title = 'Viwa İstatistikleri';

  badge.addEventListener('click', () => {
    alert(`Viwa İstatistikleri\n\nToplam Mesaj: ${stats.totalMessages}\nToplam Resim: ${stats.totalImages}`);
  });

  document.body.appendChild(badge);
}

// Setup image detection
function setupImageDetection() {
  console.log('Viwa: Setting up image detection...');

  // Observer for new images
  const observer = new MutationObserver((mutations) => {
    mutations.forEach((mutation) => {
      mutation.addedNodes.forEach((node) => {
        if (node.nodeType === 1) { // Element node
          processImages(node);
        }
      });
    });
  });

  // Start observing
  const targetNode = document.querySelector('#main') || document.body;
  observer.observe(targetNode, {
    childList: true,
    subtree: true
  });

  // Process existing images
  processImages(document.body);
}

// Process images in a node
function processImages(node) {
  // Common image selectors for WhatsApp Web
  // Note: User will provide HTML to extract exact selectors
  const imageSelectors = [
    'img[src*="blob:"]',
    'img[src*="web.whatsapp.com"]',
    'div[data-testid="image-thumb"]',
    'img.media-image',
    'img[class*="message"]'
  ];

  imageSelectors.forEach(selector => {
    const images = node.querySelectorAll ? node.querySelectorAll(selector) : [];
    images.forEach(img => {
      if (!img.dataset.viwaProcessed) {
        img.dataset.viwaProcessed = 'true';
        enhanceImage(img);
        updateImageCount();
      }
    });
  });
}

// Enhance image with Viwa features
function enhanceImage(img) {
  // Add highlight on hover
  img.addEventListener('mouseenter', () => {
    if (settings.imagePreviewEnabled) {
      img.classList.add('viwa-highlight');
    }
  });

  img.addEventListener('mouseleave', () => {
    img.classList.remove('viwa-highlight');
  });

  // Log image for debugging
  console.log('Viwa: Image enhanced', img.src);
}

// Observe messages
function observeMessages() {
  const observer = new MutationObserver(() => {
    updateMessageCount();
  });

  const targetNode = document.querySelector('#main') || document.body;
  observer.observe(targetNode, {
    childList: true,
    subtree: true
  });
}

// Update message count
async function updateMessageCount() {
  const messageElements = document.querySelectorAll('div[data-testid="msg-container"]');
  const newCount = messageElements.length;

  if (newCount !== stats.totalMessages) {
    stats.totalMessages = newCount;
    await chrome.storage.local.set({ totalMessages: newCount });
    console.log('Viwa: Message count updated:', newCount);
  }
}

// Update image count
async function updateImageCount() {
  const imageElements = document.querySelectorAll('img[data-viwa-processed="true"]');
  const newCount = imageElements.length;

  if (newCount !== stats.totalImages) {
    stats.totalImages = newCount;
    await chrome.storage.local.set({ totalImages: newCount });

    // Update badge
    if (settings.statsEnabled) {
      showStatsBadge();
    }

    // Notify popup
    chrome.runtime.sendMessage({ action: 'updateStats' });

    console.log('Viwa: Image count updated:', newCount);
  }
}

// Listen for messages from popup
chrome.runtime.onMessage.addListener((message, sender, sendResponse) => {
  if (message.action === 'settingsUpdated') {
    settings = message.settings;
    console.log('Viwa: Settings updated', settings);

    // Restart features
    startFeatures();

    sendResponse({ success: true });
  }
});

// Start initialization
init();
