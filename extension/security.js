// Secure API key management for ContextSnap
class SecureKeyManager {
  constructor() {
    this.encryptionKey = this.generateEncryptionKey();
  }

  // Generate a unique encryption key for this user
  generateEncryptionKey() {
    const storedKey = localStorage.getItem('contextsnap-encryption-key');
    if (storedKey) return storedKey;
    
    // Generate a random key
    const array = new Uint8Array(32);
    crypto.getRandomValues(array);
    const keyString = Array.from(array, byte => byte.toString(16).padStart(2, '0')).join('');
    localStorage.setItem('contextsnap-encryption-key', keyString);
    return keyString;
  }

  // Simple XOR encryption (for demo purposes)
  encryptApiKey(apiKey) {
    const encoder = new TextEncoder();
    const data = encoder.encode(apiKey);
    
    const keyBytes = new Uint8Array(this.encryptionKey.match(/.{1,2}/g).map(byte => parseInt(byte, 16)));
    const encrypted = new Uint8Array(data.length);
    
    for (let i = 0; i < data.length; i++) {
      encrypted[i] = data[i] ^ keyBytes[i % keyBytes.length];
    }
    
    return btoa(String.fromCharCode(...encrypted));
  }

  decryptApiKey(encryptedKey) {
    try {
      const encryptedBytes = new Uint8Array(atob(encryptedKey).split('').map(char => char.charCodeAt(0)));
      const keyBytes = new Uint8Array(this.encryptionKey.match(/.{1,2}/g).map(byte => parseInt(byte, 16)));
      const decrypted = new Uint8Array(encryptedBytes.length);
      
      for (let i = 0; i < encryptedBytes.length; i++) {
        decrypted[i] = encryptedBytes[i] ^ keyBytes[i % keyBytes.length];
      }
      
      return new TextDecoder().decode(decrypted);
    } catch (error) {
      console.error('Failed to decrypt API key:', error);
      return null;
    }
  }

  storeApiKey(provider, apiKey) {
    const encrypted = this.encryptApiKey(apiKey);
    localStorage.setItem(`contextsnap-api-key-${provider}`, encrypted);
  }

  getApiKey(provider) {
    const encrypted = localStorage.getItem(`contextsnap-api-key-${provider}`);
    if (!encrypted) return null;
    return this.decryptApiKey(encrypted);
  }

  removeApiKey(provider) {
    localStorage.removeItem(`contextsnap-api-key-${provider}`);
  }

  async validateApiKey(provider, apiKey) {
    try {
      const response = await fetch('http://localhost:3000/explain', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          text: 'test',
          apiKey: apiKey,
          provider: provider
        })
      });
      
      return response.ok;
    } catch (error) {
      console.error('API key validation failed:', error);
      return false;
    }
  }

  getAllStoredProviders() {
    const providers = [];
    for (let i = 0; i < localStorage.length; i++) {
      const key = localStorage.key(i);
      if (key && key.startsWith('contextsnap-api-key-')) {
        const provider = key.replace('contextsnap-api-key-', '');
        providers.push(provider);
      }
    }
    return providers;
  }
}

// Initialize secure key manager
const keyManager = new SecureKeyManager(); 