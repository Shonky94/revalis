// Chat history management
let responseCache = new Map();
let currentRequest = null;
let chatHistory = [];
let messageIdCounter = 0;
let isHyperSearchMode = false; // Default to deactive mode
let popoutWindow = null;
let isPopout = window.opener && window.name === 'contextsnap-popout';
let originalSidebarParent = null;
let originalSidebarNextSibling = null;
let isOverlayMode = false;
const minOverlayWidth = 320;
const minOverlayHeight = 400;

// Auth variables
let currentProvider = 'openai';
let isAuthenticated = false;

// Initialize sidebar
window.addEventListener('DOMContentLoaded', function() {
  const clearBtn = document.getElementById('clear-history-btn');
  if (clearBtn) {
    clearBtn.addEventListener('click', clearChatHistory);
  }
  
  const toggleSwitch = document.getElementById('hyper-search-toggle');
  if (toggleSwitch) {
    toggleSwitch.addEventListener('change', handleModeToggle);
  }
  
  // Initialize auth system
  initializeAuth();
  
  // Load any existing history and mode from storage
  loadChatHistory();
  loadModeSettings();
  
  // Send current mode to content script
  setTimeout(() => {
    window.parent.postMessage({
      type: 'current-mode',
      hyperSearch: isHyperSearchMode
    }, '*');
  }, 200);

  const popoutBtn = document.getElementById('popout-btn');
  const sidebar = document.getElementById('sidebar');
  const resizeHandle = document.querySelector('.resize-handle');
  const header = document.querySelector('.header');
  const dragPopoutBtn = document.getElementById('drag-popout-btn');
  console.log('isPopout:', isPopout, 'dragPopoutBtn:', !!dragPopoutBtn);
  if (popoutBtn && sidebar) {
    popoutBtn.addEventListener('click', function() {
      // Send a message to the parent page to toggle overlay mode for the iframe
      window.parent.postMessage({ type: 'toggle-overlay' }, '*');
    });
  }

  if (isPopout && dragPopoutBtn) {
    dragPopoutBtn.style.display = 'flex';
    let isDraggingPopout = false;
    let dragStartX = 0;
    let windowStartX = 0;
    dragPopoutBtn.addEventListener('mousedown', function(e) {
      isDraggingPopout = true;
      dragStartX = e.screenX;
      windowStartX = window.screenX;
      dragPopoutBtn.style.cursor = 'grabbing';
      document.body.style.userSelect = 'none';
    });
    window.addEventListener('mousemove', function(e) {
      if (isDraggingPopout) {
        const deltaX = e.screenX - dragStartX;
        window.moveTo(windowStartX + deltaX, window.screenY);
      }
    });
    window.addEventListener('mouseup', function() {
      if (isDraggingPopout) {
        isDraggingPopout = false;
        dragPopoutBtn.style.cursor = 'grab';
        document.body.style.userSelect = '';
      }
    });
  }

  // Drag logic
  if (header && sidebar) {
    let isDragging = false, dragOffsetX = 0, dragOffsetY = 0;
    header.addEventListener('mousedown', function(e) {
      if (!isOverlayMode) return;
      isDragging = true;
      dragOffsetX = e.clientX - sidebar.offsetLeft;
      dragOffsetY = e.clientY - sidebar.offsetTop;
      document.body.style.userSelect = 'none';
    });
    document.addEventListener('mousemove', function(e) {
      if (isDragging && isOverlayMode) {
        let newLeft = e.clientX - dragOffsetX;
        let newTop = e.clientY - dragOffsetY;
        // Clamp to viewport
        newLeft = Math.max(0, Math.min(window.innerWidth - sidebar.offsetWidth, newLeft));
        newTop = Math.max(0, Math.min(window.innerHeight - sidebar.offsetHeight, newTop));
        sidebar.style.left = newLeft + 'px';
        sidebar.style.top = newTop + 'px';
      }
    });
    document.addEventListener('mouseup', function() {
      isDragging = false;
      document.body.style.userSelect = '';
    });
  }

  // Resize logic (native CSS resize covers most, but enforce min size)
  if (resizeHandle && sidebar) {
    let isResizing = false, startX, startY, startWidth, startHeight;
    resizeHandle.addEventListener('mousedown', function(e) {
      if (!isOverlayMode) return;
      isResizing = true;
      startX = e.clientX;
      startY = e.clientY;
      startWidth = sidebar.offsetWidth;
      startHeight = sidebar.offsetHeight;
      e.preventDefault();
      e.stopPropagation();
    });
    document.addEventListener('mousemove', function(e) {
      if (isResizing && isOverlayMode) {
        let newWidth = Math.max(minOverlayWidth, startWidth + (e.clientX - startX));
        let newHeight = Math.max(minOverlayHeight, startHeight + (e.clientY - startY));
        // Clamp to viewport
        newWidth = Math.min(window.innerWidth, newWidth);
        newHeight = Math.min(window.innerHeight, newHeight);
        sidebar.style.width = newWidth + 'px';
        sidebar.style.height = newHeight + 'px';
      }
    });
    document.addEventListener('mouseup', function() {
      isResizing = false;
    });
  }

  // Listen for restore message in main window
  window.addEventListener('message', function(event) {
    if (event.data && event.data.type === 'restore-sidebar') {
      const sidebar = document.getElementById('sidebar');
      if (sidebar) sidebar.style.display = '';
    }
  });

  // Enforce minimum size in popout
  if (isPopout) {
    function enforceMinSize() {
      const minWidth = 350, minHeight = 500;
      if (window.outerWidth < minWidth) window.resizeTo(minWidth, window.outerHeight);
      if (window.outerHeight < minHeight) window.resizeTo(window.outerWidth, minHeight);
    }
    window.addEventListener('resize', enforceMinSize);
    enforceMinSize();
    // Optionally, add a class to body for popout-specific styling
    document.body.classList.add('popout-mode');
  }

  // Collapsible API settings logic
  const apiToggleBtn = document.getElementById('api-settings-toggle');
  const apiSettingsSection = document.getElementById('api-settings-section');
  if (apiSettingsSection) {
    apiSettingsSection.classList.remove('active'); // Hide by default
  }
  if (apiToggleBtn && apiSettingsSection) {
    apiToggleBtn.addEventListener('click', function() {
      apiSettingsSection.classList.toggle('active');
    });
  }
});

// Initialize authentication system
function initializeAuth() {
  const providerSelect = document.getElementById('provider-select');
  const apiKeyInput = document.getElementById('api-key-input');
  const saveKeyBtn = document.getElementById('save-key-btn');
  const testKeyBtn = document.getElementById('test-key-btn');
  
  if (providerSelect) {
    providerSelect.addEventListener('change', (e) => {
      currentProvider = e.target.value;
      loadStoredApiKey();
    });
  }
  
  if (saveKeyBtn) {
    saveKeyBtn.addEventListener('click', () => {
      const apiKey = apiKeyInput.value.trim();
      if (apiKey) {
        keyManager.storeApiKey(currentProvider, apiKey);
        updateKeyStatus('API key saved securely', 'success');
        apiKeyInput.value = '';
        isAuthenticated = true;
      } else {
        updateKeyStatus('Please enter an API key', 'error');
      }
    });
  }
  
  if (testKeyBtn) {
    testKeyBtn.addEventListener('click', async () => {
      const apiKey = keyManager.getApiKey(currentProvider);
      if (!apiKey) {
        updateKeyStatus('No API key found', 'error');
        return;
      }
      
      updateKeyStatus('Testing API key...', 'testing');
      const isValid = await keyManager.validateApiKey(currentProvider, apiKey);
      
      if (isValid) {
        updateKeyStatus('API key is valid!', 'success');
        isAuthenticated = true;
      } else {
        updateKeyStatus('Invalid API key', 'error');
        isAuthenticated = false;
      }
    });
  }
  
  // Load initial provider and key
  loadStoredApiKey();
}

function loadStoredApiKey() {
  const apiKey = keyManager.getApiKey(currentProvider);
  if (apiKey) {
    updateKeyStatus('API key found', 'success');
    isAuthenticated = true;
  } else {
    updateKeyStatus('No API key configured', 'error');
    isAuthenticated = false;
  }
}

function updateKeyStatus(message, type = 'info') {
  const statusElement = document.getElementById('key-status');
  if (statusElement) {
    statusElement.textContent = message;
    statusElement.className = `key-status-${type}`;
  }
}

// Listen for messages from content script
window.addEventListener('message', function(event) {
  if (event.data.type === 'get-mode') {
    window.parent.postMessage({
      type: 'current-mode',
      hyperSearch: isHyperSearchMode
    }, '*');
  } else if (event.data.text) {
    const selectedText = event.data.text.trim();
    const normalizedText = selectedText.toLowerCase();
    const existingMessage = chatHistory.find(msg =>
      msg.selectedText.trim().toLowerCase() === normalizedText
    );
    if (existingMessage) {
      updateChatDisplay();
      setTimeout(() => {
        const chatContainer = document.getElementById('chat-container');
        const msgDiv = chatContainer.querySelector(`[data-message-id="${existingMessage.id}"]`);
        if (msgDiv) {
          msgDiv.scrollIntoView({ behavior: 'smooth', block: 'center' });
          msgDiv.classList.add('highlight');
          setTimeout(() => msgDiv.classList.remove('highlight'), 1200);
        }
      }, 100);
      return;
    }
    
    // Show loading animation/message
    showLoadingMessage(selectedText);

    // Use local definition API (no authentication required)
    makeSecureRequest(selectedText);
  }
});

// Local definition request function
async function makeSecureRequest(text) {
  // Extract individual words for definition lookup
  const words = text.trim().split(/\s+/).filter(word => word.length > 0);
  const searchWord = words[0]; // Start with first word
  
  console.log('ContextSnap: Searching for definition of:', searchWord);
  
  try {
    // Try local definition API first
    const response = await fetch('http://localhost:5000/api/definition', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ word: searchWord })
    });
    
    console.log('ContextSnap: API response status:', response.status);
    
    if (response.ok) {
      const data = await response.json();
      console.log('ContextSnap: API response data:', data);
      
      // Remove loading message before adding real response
      const chatContainer = document.getElementById('chat-container');
      if (chatContainer) {
        const loadingMsg = chatContainer.querySelector('.chat-message.loading');
        if (loadingMsg) loadingMsg.remove();
      }
      
      if (data.error) {
        // No definition found, show a helpful message
        addMessageToHistory(text, `📚 **No Definition Found**\n\nSorry, I couldn't find a definition for "${searchWord}" in the local database.\n\n💡 **Tip:** Try selecting a single word or a more specific term.\n\n🔍 **Available:** The database contains ${data.cache_stats ? data.cache_stats.total_definitions : '580+'} academic and technical definitions.`);
      } else {
        // Format the local definition response
        let definitionText = '';
        
        if (data.match_type === 'fuzzy') {
          definitionText = `📚 **${data.original_word}** (${Math.round(data.similarity * 100)}% match for "${searchWord}")\n\n${data.definition}`;
          
          if (data.alternative_matches && data.alternative_matches.length > 0) {
            const alternatives = data.alternative_matches.map(alt => `${alt.word} (${Math.round(alt.similarity * 100)}%)`).join(', ');
            definitionText += `\n\n**Similar terms:** ${alternatives}`;
          }
        } else {
          definitionText = `📚 **${data.original_word || searchWord}**\n\n${data.definition}`;
        }
        
        if (data.response_time_ms) {
          definitionText += `\n\n⚡ *Response time: ${data.response_time_ms}ms*`;
        }
        
        addMessageToHistory(text, definitionText);
      }
    } else {
      throw new Error(`API returned ${response.status}: ${response.statusText}`);
    }
  } catch (err) {
    console.log('ContextSnap: Local API error:', err);
    
    // Remove loading message
    const chatContainer = document.getElementById('chat-container');
    if (chatContainer) {
      const loadingMsg = chatContainer.querySelector('.chat-message.loading');
      if (loadingMsg) loadingMsg.remove();
    }
    
    // Show local API error instead of falling back to external APIs
    addMessageToHistory(text, `❌ **Local API Unavailable**\n\nThe ContextSnap definition server is not running or responding.\n\n🔧 **To fix this:**\n1. Open PowerShell in the contextsnap/scripts folder\n2. Run: \`python start_system.py\`\n3. Keep the terminal window open\n\n**Error:** ${err.message}`);
  }
}

// Fallback to external API
async function makeExternalRequest(text) {
  const apiKey = keyManager.getApiKey(currentProvider);
  if (!apiKey) {
    addMessageToHistory(text, 'Error: Please configure your API key first, or start the local definition server.');
    return;
  }

  try {
    const response = await fetch('http://localhost:3000/explain', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ 
        text: text,
        apiKey: apiKey,
        provider: currentProvider
      })
    });
    
    const data = await response.json();
    
    // Remove loading message before adding real response
    const chatContainer = document.getElementById('chat-container');
    if (chatContainer) {
      const loadingMsg = chatContainer.querySelector('.chat-message.loading');
      if (loadingMsg) loadingMsg.remove();
    }
    
    if (data.error) {
      addMessageToHistory(text, `Error: ${data.error}`);
    } else {
      const response_text = data.explanation || data.response || data.result || JSON.stringify(data);
      addMessageToHistory(text, `🤖 **External AI Response**\n\n${response_text}`);
    }
  } catch (err) {
    const chatContainer = document.getElementById('chat-container');
    if (chatContainer) {
      const loadingMsg = chatContainer.querySelector('.chat-message.loading');
      if (loadingMsg) loadingMsg.remove();
    }
    addMessageToHistory(text, 'Error: Both local and external APIs unavailable. ' + err.message);
  }
}

function handleModeToggle(event) {
  isHyperSearchMode = event.target.checked;
  saveModeSettings();
  updateToggleLabel();
  
  if (isHyperSearchMode) {
    showHyperSearchAnimation();
  }
  
  // Send mode change to content script
  window.parent.postMessage({
    type: 'mode-change',
    hyperSearch: isHyperSearchMode
  }, '*');
}

function updateToggleLabel() {
  const label = document.getElementById('toggle-label');
  if (label) {
    label.textContent = isHyperSearchMode ? 'Hyper Search' : 'Manual Mode';
  }
}

function showHyperSearchAnimation() {
  const container = document.getElementById('container');
  if (!container) return;
  
  // Create animation overlay
  const overlay = document.createElement('div');
  overlay.className = 'hyper-search-animation';
  overlay.innerHTML = `
    <div class="animation-content">
      <div class="pulse-circle" style="display: flex; align-items: center; justify-content: center;">
        <svg width="48" height="48" viewBox="0 0 48 48">
          <circle cx="24" cy="24" r="22" fill="#27ae60"/>
          <polygon points="22,10 28,10 24,22 30,22 18,38 22,24 16,24" fill="#fff"/>
        </svg>
      </div>
      <div class="mode-text">Hyper Search Activated!</div>
    </div>
  `;
  
  container.appendChild(overlay);
  
  // Remove animation after 2 seconds
  setTimeout(() => {
    if (overlay.parentNode) {
      overlay.parentNode.removeChild(overlay);
    }
  }, 2000);
}

function loadModeSettings() {
  try {
    const saved = localStorage.getItem('contextsnap-mode');
    if (saved) {
      isHyperSearchMode = JSON.parse(saved);
    } else {
      // Default to false (deactive mode)
      isHyperSearchMode = false;
    }
    
    const toggleSwitch = document.getElementById('hyper-search-toggle');
    if (toggleSwitch) {
      toggleSwitch.checked = isHyperSearchMode;
    }
    updateToggleLabel();
  } catch (e) {
    console.error('Failed to load mode settings:', e);
  }
}

function saveModeSettings() {
  try {
    localStorage.setItem('contextsnap-mode', JSON.stringify(isHyperSearchMode));
  } catch (e) {
    console.error('Failed to save mode settings:', e);
  }
}

function clearChatHistory() {
  chatHistory = [];
  responseCache.clear();
  currentRequest = null;
  updateChatDisplay();
  saveChatHistory();
}

function loadChatHistory() {
  try {
    const saved = localStorage.getItem('contextsnap-chat-history');
    if (saved) {
      chatHistory = JSON.parse(saved);
      messageIdCounter = Math.max(...chatHistory.map(msg => msg.id), 0) + 1;
      updateChatDisplay();
    }
  } catch (e) {
    console.error('Failed to load chat history:', e);
  }
}

function saveChatHistory() {
  try {
    localStorage.setItem('contextsnap-chat-history', JSON.stringify(chatHistory));
  } catch (e) {
    console.error('Failed to save chat history:', e);
  }
}

function addMessageToHistory(selectedText, aiResponse) {
  // Check if this exact message already exists in history
  const normalizedText = selectedText.trim().toLowerCase();
  const existingMessage = chatHistory.find(msg => 
    msg.selectedText.trim().toLowerCase() === normalizedText
  );
  
  if (existingMessage) {
    // Message already exists, just scroll to it
    updateChatDisplay();
    const chatContainer = document.getElementById('chat-container');
    if (chatContainer) {
      chatContainer.scrollTop = chatContainer.scrollHeight;
    }
    return;
  }
  
  const message = {
    id: messageIdCounter++,
    selectedText: selectedText,
    aiResponse: aiResponse,
    timestamp: Date.now()
  };
  
  chatHistory.push(message);
  
  // Limit history to last 20 messages to prevent memory issues
  if (chatHistory.length > 20) {
    chatHistory = chatHistory.slice(-20);
  }
  
  updateChatDisplay();
  saveChatHistory();
}

function updateChatDisplay() {
  const chatContainer = document.getElementById('chat-container');
  if (!chatContainer) return;

  // Clear existing messages
  chatContainer.innerHTML = '';

  if (chatHistory.length === 0) {
    chatContainer.innerHTML = `
      <div class="placeholder-message">
        <div class="placeholder-icon">💭</div>
        <p>Select text on the page to get an AI explanation</p>
      </div>
    `;
    return;
  }

  // Add each message
  chatHistory.forEach(message => {
    const messageDiv = document.createElement('div');
    messageDiv.className = 'chat-message';
    messageDiv.setAttribute('data-message-id', message.id);
    
    messageDiv.innerHTML = `
      <div class="highlighted-section">
        <div class="section-label">Explanation</div>
        <div class="text-content">
          <p>${escapeHtml(message.selectedText)}</p>
        </div>
      </div>
      <div class="response-section">
        <div class="section-label">AI Explanation</div>
        <div class="response-content">
          <p>${escapeHtml(message.aiResponse)}</p>
        </div>
      </div>
    `;
    
    chatContainer.appendChild(messageDiv);
  });

  // Scroll to bottom
  chatContainer.scrollTop = chatContainer.scrollHeight;
}

function copyText(text) {
  if (navigator.clipboard && navigator.clipboard.writeText) {
    navigator.clipboard.writeText(text).then(() => {
      showCopySuccess();
    }).catch(err => {
      fallbackCopyTextToClipboard(text);
    });
  } else {
    fallbackCopyTextToClipboard(text);
  }
}

function fallbackCopyTextToClipboard(text) {
  const textArea = document.createElement('textarea');
  textArea.value = text;
  textArea.style.position = 'fixed';
  textArea.style.left = '-999999px';
  textArea.style.top = '-999999px';
  document.body.appendChild(textArea);
  textArea.focus();
  textArea.select();
  
  try {
    document.execCommand('copy');
    showCopySuccess();
  } catch (err) {
    console.error('Fallback: Oops, unable to copy', err);
  }
  
  document.body.removeChild(textArea);
}

function showCopySuccess() {
  // Find all copy buttons and show success state
  const copyButtons = document.querySelectorAll('.copy-btn');
  copyButtons.forEach(btn => {
    if (btn.classList.contains('copied')) return;
    
    btn.classList.add('copied');
    btn.innerHTML = `
      <svg width="14" height="14" viewBox="0 0 20 20" fill="none">
        <path d="M16.707 5.293a1 1 0 010 1.414l-8 8a1 1 0 01-1.414 0l-4-4a1 1 0 011.414-1.414L8 12.586l7.293-7.293a1 1 0 011.414 0z" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"/>
      </svg>
    `;
    
    setTimeout(() => {
      btn.classList.remove('copied');
      btn.innerHTML = `
        <svg width="14" height="14" viewBox="0 0 20 20" fill="none">
          <path d="M8 3H5a2 2 0 00-2 2v10a2 2 0 002 2h10a2 2 0 002-2v-3M8 3h8a2 2 0 012 2v3M8 3v10a2 2 0 002 2h8a2 2 0 002-2V5a2 2 0 00-2-2h-8a2 2 0 00-2-2z" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"/>
        </svg>
      `;
    }, 2000);
  });
}

function escapeHtml(unsafe) {
  return unsafe
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;")
    .replace(/'/g, "&#039;");
}

function showLoadingMessage(selectedText) {
  const chatContainer = document.getElementById('chat-container');
  if (!chatContainer) return;

  const loadingDiv = document.createElement('div');
  loadingDiv.className = 'chat-message loading';
  loadingDiv.innerHTML = `
    <div class="highlighted-section">
      <div class="section-label">Selected Text</div>
      <div class="text-content">
        <p>${escapeHtml(selectedText)}</p>
      </div>
    </div>
    <div class="response-section">
      <div class="section-label">AI Explanation</div>
      <div class="response-content">
        <div class="loading-animation">
          <div class="loading-dots">
            <span></span>
            <span></span>
            <span></span>
          </div>
          <p>Analyzing...</p>
        </div>
      </div>
    </div>
  `;
  
  chatContainer.appendChild(loadingDiv);
  chatContainer.scrollTop = chatContainer.scrollHeight;
}

function clampSidebarToViewport() {
  const sidebar = document.getElementById('sidebar');
  if (!sidebar || !isOverlayMode) return;
  
  const rect = sidebar.getBoundingClientRect();
  const viewport = {
    width: window.innerWidth,
    height: window.innerHeight
  };
  
  let newLeft = rect.left;
  let newTop = rect.top;
  
  // Clamp to viewport
  if (rect.right > viewport.width) {
    newLeft = viewport.width - rect.width;
  }
  if (rect.left < 0) {
    newLeft = 0;
  }
  if (rect.bottom > viewport.height) {
    newTop = viewport.height - rect.height;
  }
  if (rect.top < 0) {
    newTop = 0;
  }
  
  if (newLeft !== rect.left || newTop !== rect.top) {
    sidebar.style.left = newLeft + 'px';
    sidebar.style.top = newTop + 'px';
  }
}