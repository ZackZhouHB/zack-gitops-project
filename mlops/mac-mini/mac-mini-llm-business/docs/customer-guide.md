# Customer User Guide

## Welcome to Your LLM Appliance

Your Mac Mini has been pre-configured with a local AI assistant that runs entirely on your device. No data leaves your network.

---

## Getting Started

### Accessing the AI Interface

1. Open your web browser
2. Navigate to: **http://[mac-mini-ip]:3000**
   - Or if on the Mac Mini itself: http://localhost:3000
3. Log in with credentials provided by your administrator

### First-Time Login

1. Enter your username and password
2. You'll see the chat interface
3. Select a model from the dropdown (top-left)
4. Start chatting!

---

## Choosing the Right Model

Your appliance may have multiple AI models installed. Here's when to use each:

| Model | Best For | Speed |
|-------|----------|-------|
| Llama 3.2 3B | Quick questions, drafts | ⚡ Very Fast |
| Llama 3.1 8B | General tasks, summaries | ⚡ Fast |
| Mistral 7B | Writing, explanations | ⚡ Fast |
| Qwen 14B/32B | Complex analysis, multilingual | 🔄 Medium |
| Llama 70B | Detailed reasoning, research | 🐢 Slower |
| DeepSeek Coder | Programming tasks | 🔄 Medium |

**Tip**: Start with smaller models for simple tasks. Use larger models when you need higher quality.

---

## Tips for Best Results

### Writing Good Prompts

**Be Specific**
- ❌ "Write something about sales"
- ✅ "Write a 3-paragraph email to a client explaining our Q4 sales results"

**Provide Context**
- ❌ "Summarize this"
- ✅ "Summarize the following meeting notes, focusing on action items and deadlines: [paste notes]"

**Specify Format**
- ❌ "Give me ideas"
- ✅ "Give me 5 bullet points with marketing ideas for our new product launch"

### Working with Documents

1. Copy text from your document
2. Paste into the chat with instructions
3. Example: "Review this contract clause and identify potential risks: [paste clause]"

**Note**: For very long documents, break them into sections.

---

## Common Use Cases

### Email Drafting
```
Write a professional email to [recipient] about [topic].
Tone: [formal/friendly/urgent]
Key points to include:
- Point 1
- Point 2
```

### Meeting Summaries
```
Summarize these meeting notes into:
1. Key decisions made
2. Action items with owners
3. Next steps

[Paste meeting notes]
```

### Document Review
```
Review this [contract/report/proposal] and:
1. Identify the main points
2. Flag any concerns or risks
3. Suggest improvements

[Paste document]
```

### Code Help (if coding model installed)
```
Write a [language] function that [description].
Requirements:
- [requirement 1]
- [requirement 2]
Include comments explaining the code.
```

---

## Features

### Chat History
- Your conversations are saved locally
- Access previous chats from the sidebar
- Search through past conversations

### Multiple Chats
- Click "New Chat" to start fresh
- Keep different topics in separate chats

### Model Switching
- Change models mid-conversation if needed
- Larger models give better answers but are slower

### Settings
- Adjust temperature (creativity) in settings
- Lower = more focused, Higher = more creative

---

## Troubleshooting

### Slow Responses
- Try a smaller model
- Close other applications
- Check if multiple users are active

### Poor Quality Answers
- Try a larger model
- Provide more context in your prompt
- Be more specific about what you want

### Connection Error
- Verify you're on the correct network
- Check if the Mac Mini is powered on
- Contact your IT administrator

### Model Not Responding
- Wait 30 seconds and try again
- Try a different model
- Restart the chat

---

## Privacy & Security

✅ **Your data stays local**
- All processing happens on this device
- No data is sent to external servers
- Conversations are stored only on the Mac Mini

✅ **Network isolated**
- The appliance doesn't require internet
- Works on air-gapped networks

⚠️ **Best Practices**
- Don't share login credentials
- Log out when finished on shared devices
- Report any unusual behavior to IT

---

## Getting Help

- **Technical Issues**: Contact your IT administrator
- **Usage Questions**: Refer to this guide
- **Feature Requests**: Submit to your IT team

---

## Limitations

Please be aware:
- AI can make mistakes - always verify important information
- Not suitable for final legal/medical advice
- May not have knowledge of very recent events
- Complex calculations should be double-checked
- Cannot access the internet or external systems
