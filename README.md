# 🤖 ProActive Work-Life Assistant

An intelligent AI-powered assistant for restaurant booking, team coordination, and work-life management with advanced Selenium automation capabilities.

![Python](https://img.shields.io/badge/python-v3.12+-blue.svg)
![Streamlit](https://img.shields.io/badge/streamlit-v1.28+-red.svg)
![Docker](https://img.shields.io/badge/docker-ready-blue.svg)
![License](https://img.shields.io/badge/license-MIT-green.svg)

## ✨ Features

- 🍽️ **Smart Restaurant Booking** - AI-powered restaurant search with team availability
- 🔧 **Selenium Automation** - Automated restaurant booking through websites
- 📧 **Email Integration** - Birthday wishes, urgent notifications, team communications  
- 📅 **Calendar Sync** - Google Calendar integration for team coordination
- 🎯 **Intent Classification** - Smart routing of user requests using Google Gemini AI
- 🔍 **Advanced Search** - Research agent for comprehensive restaurant discovery
- 📋 **Event Planning** - Dedicated planning agent for celebrations and events
- 🌍 **Multi-location Support** - Support for major Indian cities
- 📱 **User-friendly Interface** - Streamlit-based web interface

## 🚀 Quick Start

### **Option 1: Streamlit Cloud (Recommended)**

1. **Fork this repository**
2. **Deploy to Streamlit Cloud:**
   - Go to [share.streamlit.io](https://share.streamlit.io)
   - Connect your GitHub account
   - Deploy this repository
3. **Configure API keys in Streamlit interface** (no .env needed!)

### **Option 2: Local Development**

```bash
# Clone the repository
git clone https://github.com/A4xMimic/proactive-work-life-assistant.git
cd proactive-work-life-assistant

# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Run the application
streamlit run app.py
```

### **Option 3: Docker Deployment**

```bash
# Build and run with Docker
docker-compose up --build

# Access at http://localhost:8501
```

## ⚙️ Configuration

The application uses a **user-friendly Streamlit interface** for configuration - no environment files needed!

### **Required API Keys:**
1. **Google Gemini API Key** - For AI intent classification and intelligent responses
2. **GoMaps API Key** - For restaurant search and location services

### **Optional Configuration:**
- **Email Settings** - For sending birthday wishes and notifications
- **Google Calendar** - For team availability checking
- **Team Information** - Member emails and preferences

### **Getting API Keys:**

#### **Google Gemini API:**
1. Visit [Google AI Studio](https://makersuite.google.com/app/apikey)
2. Create new API key
3. Copy and paste in Streamlit sidebar

#### **GoMaps API:**
1. Visit [GoMaps Platform](https://gomaps.pro/) or your GoMaps provider
2. Create account and generate API key
3. Enable location and places services
4. Copy and paste in Streamlit sidebar

## 📁 Project Structure

```
proactive-work-life-assistant/
├── app.py                      # Main Streamlit application
├── agents/
│   ├── __init__.py             # Agents package initialization
│   ├── orchestrator.py         # Main agent orchestrator with intent classification
│   ├── intent_classifier.py    # AI-powered intent classification using Gemini
│   ├── email_agent.py          # Email communication handling
│   ├── communication_agent.py  # Advanced communication features
│   ├── restaurant_agent.py     # Restaurant search and booking
│   ├── calendar_agent.py       # Google Calendar integration
│   ├── planning_agent.py       # Event and celebration planning
│   ├── research_agent.py       # Advanced restaurant research
│   ├── reservation_agent.py    # Restaurant reservation management
│   └── web_automation.py       # Selenium automation for bookings
├── utils/
│   ├── __init__.py             # Utils package initialization
│   ├── config.py               # Application configuration
│   └── logger.py               # Logging configuration
├── logs/                       # Application logs directory
├── venv/                       # Virtual environment (excluded from git)
├── .gitignore                  # Git ignore file
├── docker-compose.yml          # Docker Compose configuration
├── Dockerfile                  # Docker container configuration
├── requirements.txt            # Python dependencies
├── selenium_booking_17....png  # Selenium automation booking screenshot
└── README.md                   # This file
```

## 🤖 Agent Architecture

### **Core Agents:**

- **🎯 Orchestrator Agent** - Central coordinator with intent classification
- **🧠 Intent Classifier** - AI-powered request understanding using Google Gemini
- **🍽️ Restaurant Agent** - Restaurant discovery and booking management
- **📧 Email Agent** - Team communication and notifications
- **📅 Calendar Agent** - Google Calendar integration and availability
- **🔍 Research Agent** - Advanced restaurant research and recommendations
- **📋 Planning Agent** - Event planning and celebration coordination
- **🏨 Reservation Agent** - Booking management and confirmation
- **💬 Communication Agent** - Advanced team communication features
- **🔧 Web Automation Agent** - Selenium-powered website automation

### **Multi-Agent Workflow:**
```
User Input → Intent Classifier → Orchestrator → Specialized Agent → Response
```

## 🎯 Usage Examples

### **Restaurant & Event Planning:**
```
"Organize a birthday party for my 6-person team in Delhi tomorrow"
"Find restaurants with great food and vibes near Connaught Place"
"Book dinner for team in Mumbai with North Indian cuisine"
"Research best restaurants in Bangalore for team celebration"
```

### **Email Communications:**
```
"Mail Mayank birthday wishes"
"Send urgent meeting email to all team members"
"Notify team about project update"
"Send celebration invitation to team"
```

### **Calendar & Planning:**
```
"Check team availability for tomorrow"
"Schedule team meeting for next Tuesday"
"Find best time for group dinner this week"
"Plan team building event next month"
```

### **Research & Discovery:**
```
"Research top-rated restaurants in Hyderabad"
"Find vegetarian restaurants near office"
"Discover trending places for team dinner"
```

## 🔧 Technical Features

- **Multi-Agent Architecture:** Specialized agents for different domains
- **AI Intent Classification:** Google Gemini-powered request understanding
- **Advanced Restaurant Discovery:** GoMaps API integration for real-time data
- **Selenium Automation:** Automated web interactions for bookings
- **Email Automation:** SMTP integration for team communications
- **Calendar Integration:** Google Calendar API for availability management
- **Event Planning:** Dedicated planning workflows for celebrations
- **Research Capabilities:** Advanced restaurant research and recommendations
- **Docker Containerization:** Production-ready deployment
- **Comprehensive Logging:** Detailed application monitoring

## 🌟 Demo

Try these sample requests to see the multi-agent system in action:

1. **Event Planning:** "Organize birthday celebration for team in Hyderabad"
2. **Restaurant Research:** "Research best North Indian restaurants in Delhi"
3. **Email Features:** "Send birthday wishes to team member"
4. **Availability Check:** "Check when team is free this week"
5. **Automation:** "Book restaurant automatically using Selenium"

## 🔄 Selenium Automation

The system includes advanced Selenium automation capabilities:

- **Automated Booking:** Direct restaurant website booking
- **Form Filling:** Intelligent form completion
- **Multi-browser Support:** Chrome, Firefox, Edge compatibility
- **Headless Operation:** Background automation support
- **Error Handling:** Robust failure recovery
- **Screenshot Capture:** Booking confirmation evidence

## 📊 API Integration

### **GoMaps API Features:**
- Real-time restaurant data
- Location-based search
- Reviews and ratings
- Photos and details
- Availability information
- Multi-city support

### **Google Gemini AI:**
- Natural language understanding
- Intent classification
- Smart response generation
- Context awareness
- Multi-turn conversations

## 🤝 Contributing

1. Fork the repository
2. Create feature branch (`git checkout -b feature/AmazingFeature`)
3. Commit changes (`git commit -m 'Add AmazingFeature'`)
4. Push to branch (`git push origin feature/AmazingFeature`)
5. Open Pull Request

### **Development Setup:**
```bash
# Clone and setup
git clone https://github.com/A4xMimic/proactive-work-life-assistant.git
cd proactive-work-life-assistant
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# Run tests
python -m pytest tests/

# Run application
streamlit run app.py
```

## 📝 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🙏 Acknowledgments

- Built with [Streamlit](https://streamlit.io/) for the web interface
- Powered by [Google Gemini AI](https://ai.google.dev/) for intelligent processing
- Restaurant data from [GoMaps API](https://gomaps.pro/) for real-time information
- Automation with [Selenium WebDriver](https://selenium-python.readthedocs.io/) for bookings
- Calendar integration via [Google Calendar API](https://developers.google.com/calendar)

## 📧 Contact

**Author:** A4xMimic  
**Project Link:** [https://github.com/A4xMimic/proactive-work-life-assistant](https://github.com/A4xMimic/proactive-work-life-assistant)  
**Current Version:** 1.0.0  
**Last Updated:** 2025-07-21

## 🔮 Roadmap

### **Upcoming Features:**
- [ ] Voice command integration
- [ ] Mobile app companion
- [ ] Advanced AI meal recommendations
- [ ] Multi-language support
- [ ] Enterprise team management
- [ ] Advanced analytics dashboard
- [ ] Integration with more booking platforms
- [ ] AI-powered event planning suggestions

### **Version History:**
- **v1.0.0** (2025-07-21) - Initial release with multi-agent architecture
- Multi-agent system with specialized workflows
- AI-powered intent classification
- Advanced Selenium automation
- Comprehensive email and calendar integration

---

⭐ **Star this repository if you found it helpful!**

💡 **Have suggestions?** Open an issue or contribute to make this assistant even better!