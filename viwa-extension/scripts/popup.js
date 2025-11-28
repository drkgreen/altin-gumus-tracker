// Viwa Popup Script

// Load saved settings
document.addEventListener('DOMContentLoaded', async () => {
  loadSettings();
  loadStats();

  // Add event listeners
  document.getElementById('save-btn').addEventListener('click', saveSettings);
  document.getElementById('reset-btn').addEventListener('click', resetStats);

  // Add toggle listeners
  const toggles = document.querySelectorAll('input[type="checkbox"]');
  toggles.forEach(toggle => {
    toggle.addEventListener('change', () => {
      // Auto-save on toggle change
      saveSettings();
    });
  });
});

// Load settings from storage
async function loadSettings() {
  try {
    const settings = await chrome.storage.sync.get({
      statsEnabled: true,
      imagePreviewEnabled: true,
      autoSaveEnabled: false
    });

    document.getElementById('stats-toggle').checked = settings.statsEnabled;
    document.getElementById('image-preview-toggle').checked = settings.imagePreviewEnabled;
    document.getElementById('auto-save-toggle').checked = settings.autoSaveEnabled;
  } catch (error) {
    console.error('Error loading settings:', error);
  }
}

// Save settings to storage
async function saveSettings() {
  try {
    const settings = {
      statsEnabled: document.getElementById('stats-toggle').checked,
      imagePreviewEnabled: document.getElementById('image-preview-toggle').checked,
      autoSaveEnabled: document.getElementById('auto-save-toggle').checked
    };

    await chrome.storage.sync.set(settings);

    // Notify content script of settings change
    const [tab] = await chrome.tabs.query({ active: true, currentWindow: true });
    if (tab && tab.url && tab.url.includes('web.whatsapp.com')) {
      chrome.tabs.sendMessage(tab.id, { action: 'settingsUpdated', settings });
    }

    // Show success feedback
    showNotification('Ayarlar kaydedildi!');
  } catch (error) {
    console.error('Error saving settings:', error);
    showNotification('Hata: Ayarlar kaydedilemedi', 'error');
  }
}

// Load statistics
async function loadStats() {
  try {
    const stats = await chrome.storage.local.get({
      totalMessages: 0,
      totalImages: 0
    });

    document.getElementById('total-messages').textContent = stats.totalMessages;
    document.getElementById('total-images').textContent = stats.totalImages;
  } catch (error) {
    console.error('Error loading stats:', error);
  }
}

// Reset statistics
async function resetStats() {
  if (confirm('Tüm istatistikler sıfırlanacak. Emin misiniz?')) {
    try {
      await chrome.storage.local.set({
        totalMessages: 0,
        totalImages: 0
      });

      loadStats();
      showNotification('İstatistikler sıfırlandı!');
    } catch (error) {
      console.error('Error resetting stats:', error);
      showNotification('Hata: İstatistikler sıfırlanamadı', 'error');
    }
  }
}

// Show notification
function showNotification(message, type = 'success') {
  const saveBtn = document.getElementById('save-btn');
  const originalText = saveBtn.textContent;

  saveBtn.textContent = message;
  saveBtn.style.background = type === 'success' ? '#25d366' : '#e74c3c';

  setTimeout(() => {
    saveBtn.textContent = originalText;
    saveBtn.style.background = '';
  }, 2000);
}

// Listen for stats updates from content script
chrome.runtime.onMessage.addListener((message, sender, sendResponse) => {
  if (message.action === 'updateStats') {
    loadStats();
  }
});
