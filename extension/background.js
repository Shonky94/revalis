// Background script for ContextSnap
// Handles context menu creation and messaging

// Create context menu item when extension installs
chrome.runtime.onInstalled.addListener(() => {
  chrome.contextMenus.create({
    id: "contextsnap-analyze",
    title: "🔍 Analyze with ContextSnap",
    contexts: ["selection"],
    documentUrlPatterns: ["<all_urls>"]
  });
  
  console.log("ContextSnap context menu created");
});

// Handle context menu clicks
chrome.contextMenus.onClicked.addListener((info, tab) => {
  console.log("Context menu clicked", { menuItemId: info.menuItemId, hasSelection: !!info.selectionText, tabId: tab?.id });
  
  if (info.menuItemId === "contextsnap-analyze" && info.selectionText) {
    // Handle case where tabId is -1 (PDF viewer, extension pages, etc.)
    if (!tab || !tab.id || tab.id < 0) {
      console.log("Invalid tab ID, getting active tab...");
      chrome.tabs.query({ active: true, currentWindow: true }, (tabs) => {
        if (tabs && tabs[0] && tabs[0].id >= 0) {
          const activeTab = tabs[0];
          console.log("Using active tab", activeTab.id);
          analyzeText(activeTab.id, info.selectionText);
        } else {
          console.error("No valid active tab found");
        }
      });
    } else {
      console.log("Using provided tab", tab.id);
      analyzeText(tab.id, info.selectionText);
    }
  } else {
    console.log("Context menu click ignored:", {
      wrongMenuId: info.menuItemId !== "contextsnap-analyze",
      noSelection: !info.selectionText
    });
  }
});

// Function to analyze text with given tab ID
function analyzeText(tabId, selectionText) {
  console.log("Sending message to tab", tabId, "with text:", selectionText.substring(0, 50) + "...");
  
  // Send message to content script to analyze the selected text
  chrome.tabs.sendMessage(tabId, {
    action: "analyze-text",
    text: selectionText
  }).catch((error) => {
    console.log("Content script not ready, injecting...", error);
    // If content script not ready, inject it first
    chrome.scripting.executeScript({
      target: { tabId: tabId },
      files: ["content.js"]
    }).then(() => {
      console.log("Content script injected, retrying message...");
      // Try sending message again after injection
      setTimeout(() => {
        chrome.tabs.sendMessage(tabId, {
          action: "analyze-text",
          text: selectionText
        }).catch(console.error);
      }, 100);
    }).catch(console.error);
  });
}

// Handle messages from content scripts
chrome.runtime.onMessage.addListener((request, sender, sendResponse) => {
  if (request.action === "get-selected-text") {
    // This could be used for additional functionality if needed
    sendResponse({ success: true });
  }
});
