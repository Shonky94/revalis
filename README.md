# ContextSnap - AI Text Explanation Extension

A secure browser extension that provides AI-powered explanations for selected text using multiple AI providers.

## 🔐 Security Features

- **Client-side encryption** for API keys
- **Multi-provider support** (OpenAI, OpenRouter, Anthropic, Perplexity, Gemini, Cohere)
- **Rate limiting** to prevent abuse
- **CORS protection** for extension security
- **No server-side key storage** - keys never touch the server

## 🚀 Quick Start

### 1. Install the Extension

1. Download the extension files
2. Open Chrome and go to `chrome://extensions/`
3. Enable "Developer mode"
4. Click "Load unpacked" and select the `extension` folder

### 2. Configure API Key

1. Open the extension sidebar
2. Select your preferred AI provider
3. Enter your API key
4. Click "Save" and "Test" to verify

### 3. Use the Extension

- **Manual Mode**: Right-click selected text → "Analyze with ContextSnap"
- **Hyper Search Mode**: Toggle on for automatic analysis on text selection

## 🛠️ Development

### Backend Setup

```bash
cd backend
npm install
npm start
```

### Extension Development

1. Make changes to files in `extension/` folder
2. Reload extension in Chrome
3. Test changes

## 🌐 Deployment

### Render Deployment

1. **Push to GitHub**:
   ```bash
   git init
   git add .
   git commit -m "Initial commit"
   git remote add origin https://github.com/yourusername/contextsnap.git
   git push -u origin main
   ```

2. **Deploy on Render**:
   - Go to [render.com](https://render.com)
   - Create new Web Service
   - Connect your GitHub repository
   - Set build command: `npm install`
   - Set start command: `npm start`
   - Deploy!

3. **Update Extension**:
   - Replace `http://localhost:3000` with your Render URL in `extension/security.js` and `extension/sidebar.js`

## 📁 Project Structure

```
contextsnap/
├── backend/           # Express.js server
│   ├── index.js      # Main server file
│   └── package.json  # Dependencies
├── extension/         # Chrome extension
│   ├── content.js    # Content script
│   ├── sidebar.html  # Sidebar UI
│   ├── sidebar.js    # Sidebar logic
│   ├── security.js   # API key management
│   ├── styles.css    # Styling
│   └── manifest.json # Extension manifest
└── README.md         # This file
```

## 🔧 Configuration

### Supported AI Providers

- **OpenAI**: GPT-3.5-turbo, GPT-4
- **OpenRouter**: Access to 100+ models
- **Anthropic**: Claude models
- **Perplexity**: Fast inference models
- **Google Gemini**: Gemini Pro
- **Cohere**: Command models

### Environment Variables

Create `.env` file in backend folder:
```env
PORT=3000
NODE_ENV=production
```

## 🛡️ Security

- API keys are encrypted and stored locally
- Server acts as a secure proxy
- Rate limiting prevents abuse
- CORS configured for extension only
- No sensitive data logged

## 📝 License

MIT License - see LICENSE file for details

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Test thoroughly
5. Submit a pull request

## 🐛 Troubleshooting

### Common Issues

1. **Extension not loading**: Check manifest.json syntax
2. **API errors**: Verify API key and provider selection
3. **CORS errors**: Ensure backend URL is correct
4. **Rate limiting**: Wait before making more requests

### Debug Mode

Enable console logging in the extension for debugging:
1. Open DevTools
2. Go to Console tab
3. Look for ContextSnap logs

## 📞 Support

For issues and questions:
- Create an issue on GitHub
- Check the troubleshooting section
- Review the security documentation 