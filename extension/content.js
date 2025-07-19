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
      z-index: 999999 !important;
      box-shadow: -2px 0 5px rgba(0,0,0,0.1) !important;
      background: white !important;
      transition: transform 0.3s cubic-bezier(0.4,0,0.2,1) !important;
      transform: translateX(100%) !important;
      display: block !important;
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
      z-index: 1000000;
      cursor: pointer;
      box-shadow: 0 2px 8px rgba(0,0,0,0.08);
      display: flex;
      align-items: center;
      justify-content: center;
      transition: background 0.2s;
      color: #333 !important;
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
      z-index: 1000001;
      cursor: pointer;
      display: flex;
      align-items: center;
      justify-content: center;
      transition: background 0.2s, box-shadow 0.2s;
    }
    #contextsnap-sidebar-show-btn:hover {
      background: #1a7f64;
      box-shadow: 0 4px 16px rgba(16,163,127,0.18);
    }
    #contextsnap-context-menu {
      position: fixed;
      background: #fff;
      border: 1px solid #ddd;
      border-radius: 8px;
      box-shadow: 0 4px 12px rgba(0,0,0,0.15);
      z-index: 1000001;
      padding: 8px 0;
      min-width: 200px;
      display: none;
    }
    #contextsnap-context-menu button {
      display: block;
      width: 100%;
      padding: 8px 16px;
      border: none;
      background: none;
      text-align: left;
      cursor: pointer;
      font-size: 14px;
      color: #333;
      transition: background 0.2s;
    }
    #contextsnap-context-menu button:hover {
      background: #f5f5f5;
    }
    #contextsnap-context-menu button:first-child {
      border-radius: 8px 8px 0 0;
    }
    #contextsnap-context-menu button:last-child {
      border-radius: 0 0 8px 8px;
    }
  `;
  document.head.appendChild(style);
}

let isHyperSearchMode = false; // Default to deactive mode

function showSidebar() {
  const iframe = document.getElementById('contextsnap-sidebar');
  if (iframe) {
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

function injectContextMenu() {
  if (document.getElementById('contextsnap-context-menu')) return;
  const menu = document.createElement('div');
  menu.id = 'contextsnap-context-menu';
  menu.innerHTML = `
    <button id="contextsnap-analyze-btn">🔍 Analyze with ContextSnap</button>
    <button id="contextsnap-cancel-btn">Cancel</button>
  `;
  document.body.appendChild(menu);
  
  // Add event listeners
  document.getElementById('contextsnap-analyze-btn').addEventListener('click', handleContextMenuAnalyze);
  document.getElementById('contextsnap-cancel-btn').addEventListener('click', hideContextMenu);
}

function showContextMenu(x, y, selectedText) {
  const menu = document.getElementById('contextsnap-context-menu');
  if (!menu) return;
  
  menu.style.left = x + 'px';
  menu.style.top = y + 'px';
  menu.style.display = 'block';
  menu.dataset.selectedText = selectedText;
}

function hideContextMenu() {
  const menu = document.getElementById('contextsnap-context-menu');
  if (menu) {
    menu.style.display = 'none';
  }
}

function handleContextMenuAnalyze() {
  const menu = document.getElementById('contextsnap-context-menu');
  const selectedText = menu.dataset.selectedText;
  hideContextMenu();
  
  if (selectedText) {
    showSidebar();
    const iframe = document.getElementById('contextsnap-sidebar');
    if (iframe) {
      iframe.contentWindow.postMessage({ text: selectedText }, '*');
    }
  }
}

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

// Initialize extension when page loads
document.addEventListener('DOMContentLoaded', function() {
  injectSidebarStyles();
  injectCloseButton();
  injectShowButton();
  injectContextMenu();
  loadSidebar();
});

// Also initialize if DOMContentLoaded already fired
if (document.readyState === 'loading') {
  document.addEventListener('DOMContentLoaded', function() {
    injectSidebarStyles();
    injectCloseButton();
    injectShowButton();
    injectContextMenu();
    loadSidebar();
  });
} else {
  injectSidebarStyles();
  injectCloseButton();
  injectShowButton();
  injectContextMenu();
  loadSidebar();
}

// Handle text selection based on mode
document.addEventListener('mouseup', async function () {
  const selectedText = window.getSelection().toString().trim();

  if (selectedText.length >= 3) {
    if (isHyperSearchMode) {
      // Hyper Search mode: immediately show sidebar and analyze
      console.log('Hyper Search mode: analyzing text:', selectedText);
      showSidebar();
      const iframe = document.getElementById('contextsnap-sidebar');
      if (iframe) {
        iframe.contentWindow.postMessage({ text: selectedText }, '*');
      }
    }
    // In deactive mode, do nothing - wait for right-click
  }
});

// Handle right-click context menu
document.addEventListener('contextmenu', function(event) {
  const selectedText = window.getSelection().toString().trim();
  
  if (selectedText.length >= 3 && !isHyperSearchMode) {
    // Show custom context menu
    event.preventDefault();
    showContextMenu(event.clientX, event.clientY, selectedText);
  }
});

// Hide context menu when clicking elsewhere
document.addEventListener('click', function(event) {
  if (!event.target.closest('#contextsnap-context-menu')) {
    hideContextMenu();
  }
});

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
