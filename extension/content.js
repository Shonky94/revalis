// Inject slide CSS for sidebar if not already present
function injectSidebarStyles() {
  if (document.getElementById('contextsnap-sidebar-style')) return;
  const style = document.createElement('style');
  style.id = 'contextsnap-sidebar-style';
  style.textContent = `
    #contextsnap-sidebar {
      position: fixed !important;
      top: 0 !important;
      right: 0 !important;
      width: 400px !important;
      height: 100vh !important;
      border: none !important;
      z-index: 2147483647 !important; /* Maximum z-index for PDFs */
      box-shadow: -2px 0 5px rgba(0,0,0,0.1) !important;
      background: white !important;
      transition: transform 0.3s cubic-bezier(0.4,0,0.2,1) !important;
      transform: translateX(100%) !important;
      display: block !important;
      pointer-events: auto !important; /* Ensure interactions work in PDFs */
    }
    #contextsnap-sidebar.open {
      transform: translateX(0) !important;
    }
    #contextsnap-sidebar-close-btn {
      position: fixed;
      top: 18px;
      right: 410px;
      background: #fff;
      border: 1px solid #ddd;
      border-radius: 50%;
      font-size: 18px;
      width: 32px;
      height: 32px;
      z-index: 2147483647;
      cursor: pointer;
      box-shadow: 0 2px 8px rgba(0,0,0,0.08);
      display: flex;
      align-items: center;
      justify-content: center;
      transition: background 0.2s;
      color: #333 !important;
      pointer-events: auto !important;
    }
    #contextsnap-sidebar-close-btn:hover {
      background: #f8f9fa;
    }
    #contextsnap-sidebar-show-btn {
      position: fixed;
      top: 50%;
      right: 16px;
      transform: translateY(-50%);
      background: #10a37f;
      color: #fff;
      border: none;
      border-radius: 50%;
      width: 44px;
      height: 44px;
      font-size: 24px;
      box-shadow: 0 2px 8px rgba(0,0,0,0.12);
      z-index: 2147483647;
      cursor: pointer;
      display: flex;
      align-items: center;
      justify-content: center;
      transition: background 0.2s, box-shadow 0.2s;
      pointer-events: auto !important;
    }
    #contextsnap-sidebar-show-btn:hover {
      background: #1a7f64;
      box-shadow: 0 4px 16px rgba(16,163,127,0.18);
    }

  `;
  document.head.appendChild(style);
}

let isHyperSearchMode = false; // Default to deactive mode

function showSidebar() {
  console.log('ContextSnap: showSidebar() called');
  const iframe = document.getElementById('contextsnap-sidebar');
  console.log('ContextSnap: iframe found:', !!iframe);
  
  if (!iframe) {
    console.log('ContextSnap: No iframe found, loading sidebar...');
    loadSidebar();
    // Try again after loading
    setTimeout(() => {
      const newIframe = document.getElementById('contextsnap-sidebar');
      if (newIframe) {
        console.log('ContextSnap: Iframe loaded, opening...');
        newIframe.classList.add('open');
        newIframe.classList.remove('collapsed');
      }
    }, 100);
  } else {
    iframe.classList.add('open');
    iframe.classList.remove('collapsed');
    const closeBtn = document.getElementById('contextsnap-sidebar-close-btn');
    if (closeBtn) closeBtn.style.display = 'flex';
    const showBtn = document.getElementById('contextsnap-sidebar-show-btn');
    if (showBtn) showBtn.style.display = 'none'; // Hide show button when sidebar is open
  }
}

function hideSidebar() {
  const iframe = document.getElementById('contextsnap-sidebar');
  if (iframe) {
    iframe.classList.remove('open');
    iframe.classList.add('collapsed');
    const closeBtn = document.getElementById('contextsnap-sidebar-close-btn');
    if (closeBtn) closeBtn.style.display = 'none';
    const showBtn = document.getElementById('contextsnap-sidebar-show-btn');
    if (showBtn) showBtn.style.display = 'flex'; // Show the button when sidebar is closed
  }
}

function injectCloseButton() {
  if (document.getElementById('contextsnap-sidebar-close-btn')) return;
  const btn = document.createElement('button');
  btn.id = 'contextsnap-sidebar-close-btn';
  btn.innerText = '✖';
  btn.onclick = hideSidebar;
  document.body.appendChild(btn);
  btn.style.display = 'none';
}

function injectShowButton() {
  if (document.getElementById('contextsnap-sidebar-show-btn')) return;
  const btn = document.createElement('button');
  btn.id = 'contextsnap-sidebar-show-btn';
  btn.innerText = '⮞';
  btn.onclick = showSidebar;
  btn.style.display = 'flex';
  document.body.appendChild(btn);
}

// Handle messages from background script
chrome.runtime.onMessage.addListener((request, sender, sendResponse) => {
  console.log('ContextSnap: Message received:', request);
  
  if (request.action === "analyze-text" && request.text) {
    console.log('ContextSnap: Received text from context menu:', request.text.substring(0, 50) + '...');
    
    // Show sidebar and analyze text
    showSidebar();
    const iframe = document.getElementById('contextsnap-sidebar');
    if (iframe) {
      // Wait a moment for sidebar to load if needed
      setTimeout(() => {
        console.log('ContextSnap: Sending message to sidebar iframe');
        iframe.contentWindow.postMessage({ text: request.text }, '*');
      }, 500); // Increased timeout to ensure sidebar is loaded
    }
    
    sendResponse({ success: true });
  } else {
    console.log('ContextSnap: Message ignored - action:', request.action, 'hasText:', !!request.text);
    sendResponse({ success: false });
  }
});

function loadSidebar() {
  let iframe = document.getElementById('contextsnap-sidebar');
  if (!iframe) {
    iframe = document.createElement('iframe');
    iframe.src = chrome.runtime.getURL('sidebar.html');
    iframe.id = 'contextsnap-sidebar';
    iframe.className = 'collapsed';
    document.body.appendChild(iframe);
    
    // Listen for mode changes from sidebar
    iframe.addEventListener('load', function() {
      // Request current mode from sidebar
      setTimeout(() => {
        iframe.contentWindow.postMessage({ type: 'get-mode' }, '*');
      }, 100);
      
      // Listen for messages from sidebar
      window.addEventListener('message', function(event) {
        if (event.data.type === 'mode-change') {
          isHyperSearchMode = event.data.hyperSearch;
          console.log('Mode changed to:', isHyperSearchMode ? 'Hyper Search' : 'Manual Mode');
        } else if (event.data.type === 'current-mode') {
          isHyperSearchMode = event.data.hyperSearch;
          console.log('Current mode loaded:', isHyperSearchMode ? 'Hyper Search' : 'Manual Mode');
        }
      });
    });
  }
}

// Initialize extension
function initializeContextSnap() {
  injectSidebarStyles();
  injectCloseButton();
  injectShowButton();
  loadSidebar();
  
  // Log PDF detection for debugging
  if (isPDFViewer()) {
    console.log('ContextSnap: Initialized for PDF viewer');
  } else {
    console.log('ContextSnap: Initialized for regular webpage');
  }
}

// Initialize extension when page loads
document.addEventListener('DOMContentLoaded', initializeContextSnap);

// Also initialize if DOMContentLoaded already fired
if (document.readyState === 'loading') {
  document.addEventListener('DOMContentLoaded', initializeContextSnap);
} else {
  initializeContextSnap();
}

// Special handling for PDF viewers that load dynamically
if (window.location.href.includes('.pdf')) {
  // For PDF files, also try to initialize after a delay
  setTimeout(() => {
    if (!document.getElementById('contextsnap-sidebar')) {
      console.log('ContextSnap: Late initialization for PDF');
      initializeContextSnap();
    }
  }, 2000);
}

// Check if we're in a PDF viewer
function isPDFViewer() {
  return window.location.href.includes('.pdf') || 
         document.querySelector('embed[type="application/pdf"]') ||
         document.querySelector('object[type="application/pdf"]') ||
         window.location.href.includes('chrome-extension://mhjfbmdgcfjbbpaeojofohoefgiehjai') || // Chrome PDF viewer
         document.title.includes('.pdf') ||
         document.querySelector('#viewer') && document.querySelector('.page'); // Generic PDF viewer
}

// Get selected text from various sources (regular DOM and PDF)
function getSelectedText() {
  // Try regular window selection first
  let selectedText = window.getSelection().toString().trim();
  
  if (!selectedText && isPDFViewer()) {
    // For PDF viewers, try different methods
    try {
      // Method 1: Check for PDF.js viewer
      if (window.PDFViewerApplication && window.PDFViewerApplication.pdfViewer) {
        const selection = window.PDFViewerApplication.pdfViewer.getTextSelection();
        if (selection && selection.str) {
          selectedText = selection.str.trim();
        }
      }
      
      // Method 2: Try to get selection from PDF viewer iframe or embed
      const pdfEmbed = document.querySelector('embed[type="application/pdf"]');
      if (pdfEmbed) {
        try {
          const pdfSelection = pdfEmbed.contentWindow.getSelection();
          if (pdfSelection) {
            selectedText = pdfSelection.toString().trim();
          }
        } catch (e) {
          // Cross-origin restrictions may prevent access
        }
      }
      
      // Method 3: Check for text layers in PDF.js
      const textLayers = document.querySelectorAll('.textLayer');
      if (textLayers.length > 0) {
        // Get selection from text layers
        const selection = window.getSelection();
        if (selection.rangeCount > 0) {
          const range = selection.getRangeAt(0);
          const container = range.commonAncestorContainer;
          if (container && container.textContent) {
            selectedText = range.toString().trim();
          }
        }
      }
      
    } catch (error) {
      console.log('ContextSnap: PDF text selection error:', error);
    }
  }
  
  return selectedText;
}

// Enhanced text selection handler
function handleTextSelection(event) {
  // Add a small delay to ensure selection is complete
  setTimeout(() => {
    const selectedText = getSelectedText();
    
    if (selectedText && selectedText.length >= 3) {
      console.log('ContextSnap: Selected text:', selectedText);
      
      if (isHyperSearchMode) {
        // Hyper Search mode: immediately show sidebar and analyze
        console.log('Hyper Search mode: analyzing text:', selectedText);
        showSidebar();
        const iframe = document.getElementById('contextsnap-sidebar');
        if (iframe) {
          iframe.contentWindow.postMessage({ text: selectedText }, '*');
        }
      }
      // In manual mode, do nothing - wait for right-click
    }
  }, 100);
}

// Handle text selection for both regular pages and PDFs
document.addEventListener('mouseup', handleTextSelection);

// For PDFs, also listen on document body and common PDF viewer elements
if (isPDFViewer()) {
  console.log('ContextSnap: PDF viewer detected, adding enhanced selection handlers');
  
  // Additional listeners for PDF viewers
  document.body.addEventListener('mouseup', handleTextSelection);
  
  // Listen for PDF.js specific events
  document.addEventListener('textlayerrendered', function() {
    const textLayers = document.querySelectorAll('.textLayer');
    textLayers.forEach(layer => {
      layer.addEventListener('mouseup', handleTextSelection);
    });
  });
  
  // Monitor for dynamically loaded PDF pages
  const observer = new MutationObserver(function(mutations) {
    mutations.forEach(function(mutation) {
      if (mutation.addedNodes) {
        mutation.addedNodes.forEach(function(node) {
          if (node.nodeType === 1) { // Element node
            // Check for new text layers
            const textLayers = node.querySelectorAll ? node.querySelectorAll('.textLayer') : [];
            textLayers.forEach(layer => {
              layer.addEventListener('mouseup', handleTextSelection);
            });
            
            // Check if the added node is itself a text layer
            if (node.classList && node.classList.contains('textLayer')) {
              node.addEventListener('mouseup', handleTextSelection);
            }
          }
        });
      }
    });
  });
  
  observer.observe(document.body, {
    childList: true,
    subtree: true
  });
}

// Note: Context menu is now handled by background.js using Chrome's built-in context menu API
// The "Analyze with ContextSnap" option will appear when text is selected

// --- Overlay logic for the sidebar iframe ---
let isSidebarOverlay = false;
let originalSidebarStyles = {};
let dragOffsetX = 0, dragOffsetY = 0;

window.addEventListener('message', function(event) {
  if (event.data && event.data.type === 'toggle-overlay') {
    toggleSidebarOverlay();
  }
  if (event.data && event.data.type === 'contextsnap-copy') {
    injectCopyScript(event.data.text);
  }
});

function injectCopyScript(text) {
  const script = document.createElement('script');
  script.textContent = `
    (function() {
      try {
        if (navigator.clipboard && navigator.clipboard.writeText) {
          navigator.clipboard.writeText(${JSON.stringify(text)});
        } else {
          var textArea = document.createElement('textarea');
          textArea.value = ${JSON.stringify(text)};
          document.body.appendChild(textArea);
          textArea.focus();
          textArea.select();
          try {
            document.execCommand('copy');
          } catch (err) {}
          document.body.removeChild(textArea);
        }
      } catch (e) {}
    })();
  `;
  document.documentElement.appendChild(script);
  script.remove();
}

function toggleSidebarOverlay() {
  const iframe = document.getElementById('contextsnap-sidebar');
  if (!iframe) return;
  const minWidth = 320, minHeight = 400;
  isSidebarOverlay = !isSidebarOverlay;

  if (isSidebarOverlay) {
    // Save original styles
    originalSidebarStyles = {
      position: iframe.style.position,
      top: iframe.style.top,
      left: iframe.style.left,
      width: iframe.style.width,
      height: iframe.style.height,
      zIndex: iframe.style.zIndex,
      borderRadius: iframe.style.borderRadius,
      boxShadow: iframe.style.boxShadow,
      transition: iframe.style.transition,
      background: iframe.style.background,
      minWidth: iframe.style.minWidth,
      minHeight: iframe.style.minHeight,
      maxWidth: iframe.style.maxWidth,
      maxHeight: iframe.style.maxHeight,
      display: iframe.style.display
    };
    // Set overlay styles
    iframe.style.position = 'fixed';
    iframe.style.top = '80px';
    iframe.style.left = '80px';
    iframe.style.width = '400px';
    iframe.style.height = '600px';
    iframe.style.minWidth = minWidth + 'px';
    iframe.style.minHeight = minHeight + 'px';
    iframe.style.maxWidth = '90vw';
    iframe.style.maxHeight = '90vh';
    iframe.style.zIndex = '2147483646'; // slightly less than handle
    iframe.style.borderRadius = '12px';
    iframe.style.boxShadow = '0 4px 32px rgba(0,0,0,0.25)';
    iframe.style.transition = 'box-shadow 0.2s';
    iframe.style.background = '#fff';
    iframe.style.display = 'block';
    iframe.style.resize = ''; // no resize

    // Hide sidebar open/close buttons
    const closeBtn = document.getElementById('contextsnap-sidebar-close-btn');
    const showBtn = document.getElementById('contextsnap-sidebar-show-btn');
    if (closeBtn) closeBtn.style.display = 'none';
    if (showBtn) showBtn.style.display = 'none';

    // Add drag handle if not present
    let dragHandle = document.getElementById('overlay-drag-handle');
    if (!dragHandle) {
      dragHandle = document.createElement('div');
      dragHandle.className = 'overlay-drag-handle';
      dragHandle.id = 'overlay-drag-handle';
      dragHandle.innerHTML = `<svg width="16" height="16" viewBox="0 0 20 20"><circle cx="10" cy="10" r="6" fill="#fff" stroke="#10a37f" stroke-width="2"/></svg>`;
      document.body.appendChild(dragHandle);
    }
    positionDragHandle();

    // Drag logic
    let isDraggingOverlay = false;
    dragHandle.onmousedown = function(e) {
      isDraggingOverlay = true;
      dragOffsetX = e.clientX - iframe.offsetLeft;
      dragOffsetY = e.clientY - iframe.offsetTop;
      document.body.style.userSelect = 'none';
      dragHandle.style.cursor = 'grabbing';
    };
    window.onmousemove = function(e) {
      if (!isDraggingOverlay) return;
      let newLeft = e.clientX - dragOffsetX;
      let newTop = e.clientY - dragOffsetY;
      newLeft = Math.max(0, Math.min(window.innerWidth - iframe.offsetWidth, newLeft));
      newTop = Math.max(0, Math.min(window.innerHeight - iframe.offsetHeight, newTop));
      iframe.style.left = newLeft + 'px';
      iframe.style.top = newTop + 'px';
      positionDragHandle();
    };
    window.onmouseup = function() {
      if (isDraggingOverlay) {
        isDraggingOverlay = false;
        document.body.style.userSelect = '';
        dragHandle.style.cursor = 'grab';
      }
    };

    // Keep handle in sync with iframe position/size
    window.addEventListener('resize', positionDragHandle);
    function positionDragHandle() {
      const rect = iframe.getBoundingClientRect();
      dragHandle.style.left = (rect.left + rect.width - 20) + 'px';
      dragHandle.style.top = (rect.top + 12) + 'px';
    }
  } else {
    // Remove drag handle
    const dragHandle = document.getElementById('overlay-drag-handle');
    if (dragHandle) dragHandle.remove();
    // Restore original styles
    for (const key in originalSidebarStyles) {
      iframe.style[key] = originalSidebarStyles[key] || '';
    }
    // Show sidebar open/close buttons
    const closeBtn = document.getElementById('contextsnap-sidebar-close-btn');
    const showBtn = document.getElementById('contextsnap-sidebar-show-btn');
    if (closeBtn) closeBtn.style.display = 'flex';
    if (showBtn) showBtn.style.display = 'flex';
    // Remove drag events
    window.onmousemove = null;
    window.onmouseup = null;
  }
}

// Initialize the extension
console.log('ContextSnap: Content script loaded on', window.location.href);
injectSidebarStyles();
console.log('ContextSnap: Styles injected, ready for messages');
