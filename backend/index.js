import express from "express";
import cors from "cors";
import dotenv from "dotenv";
import fetch from "node-fetch";

dotenv.config();
const app = express();
const PORT = process.env.PORT || 3000;

// Enhanced CORS for extension security
app.use(cors({
  origin: ['chrome-extension://*', 'moz-extension://*', 'http://localhost:*'],
  credentials: true
}));
app.use(express.json());

// Rate limiting
const rateLimit = new Map();
const RATE_LIMIT = 100; // requests per hour
const RATE_WINDOW = 60 * 60 * 1000; // 1 hour

function checkRateLimit(userId) {
  const now = Date.now();
  const userRequests = rateLimit.get(userId) || [];
  const validRequests = userRequests.filter(time => now - time < RATE_WINDOW);
  
  if (validRequests.length >= RATE_LIMIT) {
    return false;
  }
  
  validRequests.push(now);
  rateLimit.set(userId, validRequests);
  return true;
}

// Provider configurations
const PROVIDERS = {
  openai: {
    endpoint: 'https://api.openai.com/v1/chat/completions',
    defaultModel: 'gpt-3.5-turbo',
    headers: (apiKey) => ({
      'Authorization': `Bearer ${apiKey}`,
      'Content-Type': 'application/json'
    })
  },
  openrouter: {
    endpoint: 'https://openrouter.ai/api/v1/chat/completions',
    defaultModel: 'deepseek/deepseek-r1-0528-qwen3-8b:free',
    headers: (apiKey) => ({
      'Authorization': `Bearer ${apiKey}`,
      'Content-Type': 'application/json',
      'HTTP-Referer': 'https://contextsnap.com',
      'X-Title': 'ContextSnap'
    })
  },
  anthropic: {
    endpoint: 'https://api.anthropic.com/v1/messages',
    defaultModel: 'claude-3-haiku-20240307',
    headers: (apiKey) => ({
      'x-api-key': apiKey,
      'Content-Type': 'application/json',
      'anthropic-version': '2023-06-01'
    })
  },
  perplexity: {
    endpoint: 'https://api.perplexity.ai/chat/completions',
    defaultModel: 'llama-3.1-8b-instant',
    headers: (apiKey) => ({
      'Authorization': `Bearer ${apiKey}`,
      'Content-Type': 'application/json'
    })
  },
  gemini: {
    endpoint: 'https://generativelanguage.googleapis.com/v1beta/models/gemini-pro:generateContent',
    defaultModel: 'gemini-pro',
    headers: (apiKey) => ({
      'Content-Type': 'application/json'
    })
  },
  cohere: {
    endpoint: 'https://api.cohere.ai/v1/chat',
    defaultModel: 'command-r-plus',
    headers: (apiKey) => ({
      'Authorization': `Bearer ${apiKey}`,
      'Content-Type': 'application/json'
    })
  }
};

// Secure proxy endpoint
app.post("/explain", async (req, res) => {
  const { text, apiKey, provider } = req.body;
  
  // Validate input
  if (!text || !apiKey || !provider) {
    console.log("❌ Missing required fields");
    return res.status(400).json({ 
      error: "Missing required fields: text, apiKey, provider" 
    });
  }

  // Rate limiting
  const userId = req.ip || req.connection.remoteAddress;
  if (!checkRateLimit(userId)) {
    return res.status(429).json({ 
      error: "Rate limit exceeded. Please try again later." 
    });
  }

  // Validate provider
  if (!PROVIDERS[provider]) {
    return res.status(400).json({ 
      error: `Unsupported provider: ${provider}. Supported providers: ${Object.keys(PROVIDERS).join(', ')}` 
    });
  }

  try {
    const providerConfig = PROVIDERS[provider];
    const requestBody = buildRequestBody(provider, text);
    
    console.log(` Requesting from ${provider} for text: ${text.substring(0, 50)}...`);

    const response = await fetch(providerConfig.endpoint, {
      method: "POST",
      headers: providerConfig.headers(apiKey),
      body: JSON.stringify(requestBody)
    });

    const data = await response.json();
    
    if (!response.ok) {
      console.error(`❌ ${provider} API error:`, data);
      return res.status(response.status).json({ 
        error: data.error?.message || data.message || `API request failed: ${response.status}` 
      });
    }

    const explanation = extractResponse(provider, data);
    
    if (explanation) {
      console.log(`✅ ${provider} response received`);
      return res.json({ explanation });
    } else {
      return res.status(500).json({ error: "No explanation received from model." });
    }

  } catch (err) {
    console.error("❌ Server error:", err);
    res.status(500).json({ error: "Server error." });
  }
});

// Build request body based on provider
function buildRequestBody(provider, text) {
  const systemPrompt = "You are ContextSnap, an AI assistant that explains academic or technical phrases in simple terms with examples, analogies, and context.";
  const userPrompt = `Explain the phrase "${text}" in simple, concise language for a 15-year-old. Keep it under 120 words. Avoid extra reasoning or analogies unless essential.`;

  switch (provider) {
    case 'anthropic':
      return {
        model: PROVIDERS.anthropic.defaultModel,
        max_tokens: 1000,
        messages: [
          { role: 'user', content: `${systemPrompt}\n\n${userPrompt}` }
        ]
      };
    
    case 'gemini':
      return {
        contents: [{
          parts: [{
            text: `${systemPrompt}\n\n${userPrompt}`
          }]
        }],
        generationConfig: {
          temperature: 0.7,
          maxOutputTokens: 1000
        }
      };
    
    case 'perplexity':
    case 'openai':
    case 'openrouter':
    case 'cohere':
    default:
      return {
        model: PROVIDERS[provider].defaultModel,
        messages: [
          { role: 'system', content: systemPrompt },
          { role: 'user', content: userPrompt }
        ],
        temperature: 0.7,
        max_tokens: 1000
      };
  }
}

// Extract response based on provider
function extractResponse(provider, data) {
  switch (provider) {
    case 'anthropic':
      return data.content?.[0]?.text?.trim();
    
    case 'gemini':
      return data.candidates?.[0]?.content?.parts?.[0]?.text?.trim();
    
    case 'perplexity':
    case 'openai':
    case 'openrouter':
    case 'cohere':
    default:
      return data.choices?.[0]?.message?.content?.trim();
  }
}

// Health check endpoint
app.get("/health", (req, res) => {
  res.json({ 
    status: "healthy", 
    timestamp: new Date().toISOString(),
    providers: Object.keys(PROVIDERS)
  });
});

// Get supported providers
app.get("/providers", (req, res) => {
  res.json({ 
    providers: Object.keys(PROVIDERS),
    models: Object.fromEntries(
      Object.entries(PROVIDERS).map(([key, config]) => [key, config.defaultModel])
    )
  });
});

app.listen(PORT, () => {
  console.log(`✅ Secure backend running on port ${PORT}`);
  console.log(`📋 Supported providers: ${Object.keys(PROVIDERS).join(', ')}`);
});
