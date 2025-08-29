# 🚀 Telegram Messages Scraper & AI Validator

A professional Telegram scraping tool that extracts messages from groups and validates users with AI for business development purposes.

## 📋 Features

### 🎯 Core Functionality
- **Message Scraping**: Extract messages with gaming keyword detection
- **Data Processing**: Group messages by user in JSON format
- **AI Validation**: Use OpenRouter AI to validate potential customers
- **Gaming Detection**: 106+ gaming keywords detection in message content
- **Smart Filtering**: Filter users with relevant gaming/affiliate keywords

### 🤖 AI Integration
- **OpenRouter Integration**: Uses Gemini 2.0 Flash for user validation
- **Intelligent Analysis**: Analyzes user behavior patterns
- **Business Focus**: Identifies potential customers for traffic/payment services
- **JSON Output**: Structured data with validation results

### 🏗️ Professional Architecture
- **Modular Design**: Clean separation of concerns across multiple files
- **Modern Python**: Type hints, async/await, Pydantic validation
- **Configuration Management**: Environment-based settings with validation
- **Error Handling**: Comprehensive error handling and user feedback
- **Performance**: Caching, rate limiting, and optimized operations

## 🏛️ Architecture

```
telegram_scraper/
├── main.py           # 🎯 Application entry point & orchestration
├── tools.py          # 🔧 Core business logic & Telegram operations  
├── config.py         # ⚙️ Pydantic configuration & AI prompts
├── requirements.txt  # 📦 Dependencies specification
├── .env.example     # 🔐 Environment configuration template
├── README.md        # 📖 Documentation
└── data/            # 📁 Output directory for CSV/JSON files
```

### 📁 File Responsibilities

#### `main.py` - Entry Point & Orchestration
- Application lifecycle management
- User interface and menu system
- Error handling and logging
- Optional Telegram connection for data processing

#### `tools.py` - Business Logic Hub
- `TelegramTools` class with all scraping operations
- Message processing with keyword detection
- CSV to JSON data transformation
- AI validation with OpenRouter integration
- User filtering and data export

#### `config.py` - Configuration & Constants
- `Settings` class with Pydantic validation
- AI prompts and OpenRouter configuration
- `GamingKeywords` class with 106+ gaming terms
- Environment variable management
- Path and encoding configurations

## 🚀 Quick Start

### 1️⃣ Installation

```bash
# Clone or download the project
cd telegram_scraper

# Create virtual environment
python -m venv .venv
source .venv/bin/activate  # Linux/Mac
# .venv\Scripts\activate   # Windows

# Install dependencies
pip install -r requirements.txt
```

### 2️⃣ Configuration

```bash
# Copy environment template
cp .env.example .env

# Edit your configuration
nano .env
```

**Required settings in `.env`:**

**For Message Scraping:**
```env
API_ID=your_telegram_api_id
API_HASH=your_telegram_api_hash
PHONE=+1234567890
```

**For AI Validation (optional):**
```env
OPENROUTER_API_KEY=your_openrouter_api_key
AI_MODEL=google/gemini-2.0-flash-exp:free
```

**Get credentials:**
1. **Telegram API**: Visit https://my.telegram.org/apps
2. **OpenRouter**: Visit https://openrouter.ai/keys
3. Copy credentials to `.env`

### 3️⃣ First Run

```bash
python main.py
```

## 📱 Usage Guide

### 🎮 Main Menu Options

```
🚀 Telegram Messages Scraper

1. � Получить сообщения группы по периоду
2. 🤖 Обработать и валидировать данные с AI
```

### 1️⃣ Fetch Group Messages

**Features:**
- Extract messages from specified time periods (days/weeks/months)
- Gaming keyword detection in message content
- Sender information caching for performance
- Message text cleaning and formatting
- Detailed progress reporting

**Output CSV columns:**
```csv
message_id,date,sender_id,sender_username,sender_name,message_text,group,group_id,sender_bio,message_gaming_keywords,sender_common_groups
```

### 2️⃣ Process and Validate Data with AI

**Data Processing Pipeline:**

**Step 1: CSV to JSON Transformation**
- Groups messages by user
- Creates structured JSON format:
```json
{
  "user_id": {
    "sender_id": "123456",
    "sender_username": "username",
    "sender_name": "Full Name",
    "sender_bio": "User bio...",
    "messages": [
      {
        "message_id": "1",
        "date": "2024-01-01 12:00:00 UTC",
        "message_text": "Message content...",
        "message_gaming_keywords": "casino, betting"
      }
    ]
  }
}
```

**Step 2: Gaming Keywords Filtering**
- Filters users who have at least one message with gaming keywords
- Saves filtered data to `filtered-users-*.json`

**Step 3: AI Validation**
- Uses OpenRouter API with Gemini 2.0 Flash
- Analyzes user behavior patterns
- Determines if user is a potential customer for traffic/payment services
- Returns boolean validation result
- Saves validated users to `validated-users-*.json`

**AI Analysis Criteria:**
- Traffic arbitrage discussions
- Affiliate marketing interest
- Payment processing needs
- Geographic market focus
- Professional business communication

**Output CSV columns:**
```csv
message_id,date,sender_id,sender_username,sender_name,message_text,group,group_id,sender_bio,message_gaming_keywords,sender_common_groups
```

**🎯 Key Feature: Message Gaming Keywords**
- Gaming keywords are detected **only in message content**
- 106+ gaming terms including: casino, poker, betting, gambling, etc.
- Keywords found in messages are listed in `message_gaming_keywords` column

### 3️⃣ Add Users to Group

**Features:**
- Bulk add users from CSV files
- Intelligent error handling for privacy restrictions
- Rate limiting and flood protection
- Success/failure reporting

**Expected CSV format:**
```csv
username,user_id,access_hash,name,group,group_id,...
```

### 4️⃣ View CSV Files

**Features:**
- Browse and preview CSV files in data/ folder
- File selection interface
- Content preview with row limiting

## 🎯 Gaming Keywords Detection

### 📍 Detection Scope
**Gaming keywords are searched ONLY in message content**, not in user profiles.

### 🎮 Keyword Categories (106 total)

**Casino & Gambling:**
- casino, gambling, poker, blackjack, roulette, slots
- jackpot, betting, lottery, bingo, dice, baccarat

**Sports Betting:**
- football, basketball, tennis, soccer, hockey, boxing
- esports, cricket, baseball, golf, racing, olympics

**Online Gaming:**
- game, gaming, gamer, online, multiplayer, tournament
- battle, arena, championship, competition, league

**Crypto Gaming:**
- crypto, bitcoin, ethereum, nft, blockchain, token
- trading, exchange, wallet, defi, mining

**And many more...** (see `config.py` for the complete list)

## ⚙️ Configuration

### 🔧 Settings Class (Pydantic)

```python
class Settings(BaseSettings):
    # Telegram API
    api_id: int
    api_hash: str
    phone: str
    session_name: str = "telegram_session"
    
    # Performance
    fast_mode_delay: float = 0.1
    detailed_mode_delay: float = 1.0
    api_delay: float = 2.0
    
    # CSV Export
    csv_encoding: str = "utf-8"
    csv_delimiter: str = ","
    csv_line_terminator: str = "\n"
    
    # Caching
    max_cache_groups: int = 50
    max_common_groups: int = 10
    progress_update_frequency: int = 50
```

### 📂 Directory Structure

```
data/                     # Output folder (auto-created)
├── members-group-abc123.csv      # Group members
├── messages-chat-def456.csv      # Group messages
└── ...                   # More exports with UUID naming
```

## 🛡️ Error Handling

### 🔒 Telegram API Limits
- **FloodWaitError**: Automatic waiting and retry
- **UserPrivacyRestrictedError**: Graceful skipping with notification
- **PeerFloodError**: Rate limiting protection

### 📊 User Feedback
- Real-time progress indicators
- Detailed error reporting
- Success/failure statistics
- Color-coded console output

### 🔄 Recovery Features
- Cached user data to avoid duplicate API calls
- Session persistence across runs
- Graceful handling of network interruptions

## 🎨 Technical Features

### 🏗️ Modern Python Practices
- **Type Hints**: Full type annotation throughout
- **Async/Await**: Non-blocking operations
- **Pydantic**: Data validation and settings management
- **Pathlib**: Modern file path handling

### 🚀 Performance Optimizations
- **User Caching**: Avoid duplicate API calls for same users
- **Batch Processing**: Efficient handling of large datasets
- **Rate Limiting**: Respect Telegram's API limits
- **Memory Management**: Streaming CSV writes for large exports

### 🔐 Security Features
- **Environment Variables**: Secure credential management
- **Session Files**: Encrypted session storage
- **Input Validation**: Pydantic validation for all settings

## 📈 Performance Tips

### ⚡ Fast vs Detailed Mode
- **Fast Mode**: Names only, ~0.1s per user, good for large groups
- **Detailed Mode**: Full bios, ~1-2s per user, comprehensive data

### 🎯 Optimal Usage
- Use fast mode for initial group analysis
- Use detailed mode for targeted user research
- Leverage caching for repeated operations on same groups

## 🔍 Troubleshooting

### Common Issues

**"Phone number not authorized"**
- Ensure phone number format: +1234567890
- Check API_ID and API_HASH are correct
- Verify account has access to target groups

**"No groups found"**
- Account must be member of groups to access them
- Check group privacy settings
- Ensure account is not restricted

**"CSV encoding errors"**
- Default UTF-8 encoding handles most languages
- Adjust `csv_encoding` in settings if needed

### Debug Mode
```python
# Add logging for debugging
import logging
logging.basicConfig(level=logging.DEBUG)
```

## 📄 Dependencies

```
telethon>=1.35.0     # Telegram client library
pydantic>=2.5.0      # Data validation
pydantic-settings>=2.1.0  # Settings management
```

## 🤝 Contributing

This is a professional, modular codebase ready for:
- Feature extensions
- Additional keyword categories
- Export format options
- Advanced filtering capabilities

## 📜 License

Open source project for educational and research purposes.

---

**🎯 Ready to extract professional Telegram data with gaming keyword detection!**
