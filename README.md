# 🚀 JobAutoPilot

**AI-Powered Job Application Automation System**

JobAutoPilot is a comprehensive, intelligent job application automation system that uses AI agents to find, analyze, and apply to job opportunities automatically. Built with advanced web scraping, natural language processing, and intelligent matching algorithms.

## 🌟 Features

### 🔍 **Intelligent Job Discovery**
- Multi-platform scraping (Indeed, LinkedIn, Glassdoor)
- AI-powered job matching and relevance scoring
- Advanced anti-detection mechanisms
- Duplicate removal and smart filtering

### 📄 **AI Document Generation**
- Automated resume tailoring for each job
- Personalized cover letter creation
- ATS-optimized formatting
- Multiple output formats (TXT, DOCX, PDF)

### 🤖 **Smart Application Agent**
- Automated form filling with intelligent field detection
- Email application handling
- Multi-strategy application approach
- Success/failure tracking and analytics

### 📊 **Analytics & Reporting**
- Comprehensive application tracking
- Success rate analysis
- Performance metrics and insights
- Export capabilities

## 🏗️ Architecture

```
JobAutoPilot/
├── main.py                 # Main entry point
├── config.json            # Configuration file
├── requirements.txt        # Dependencies
├── core/
│   ├── config.py          # Configuration management
│   └── database.py        # Database operations
├── manager/
│   └── orchestrator.py    # Main orchestrator
├── job_finder/
│   └── job_aggregator.py  # Job scraping agents
├── modifier/
│   └── cv_cover_editor.py # Document generation
├── applier/
│   └── apply_bot.py       # Application automation
├── data/                  # Data storage
├── logs/                  # Log files
├── documents/             # Generated documents
└── templates/             # Resume/cover letter templates
```

## 🚀 Quick Start

### 1. Installation

```bash
# Clone the repository
git clone https://github.com/yourusername/jobautopilot.git
cd jobautopilot

# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
```

### 2. Configuration

1. **Copy and edit configuration:**
   ```bash
   cp config.json.example config.json
   ```

2. **Update `config.json` with your details:**
   - Personal information (name, email, phone)
   - Target job positions and skills
   - OpenAI API key (for AI features)
   - Email credentials (for applications)
   - Preferred locations and companies

3. **Create resume template:**
   - Add your base resume to `templates/resume_template.txt`
   - Add cover letter template to `templates/cover_letter_template.txt`

### 3. Usage

#### Full Pipeline (Recommended)
```bash
python main.py --mode full --max-jobs 50
```

#### Job Search Only
```bash
python main.py --mode search --max-jobs 30
```

#### Apply to Existing Jobs
```bash
python main.py --mode apply
```

#### View Status Report
```bash
python main.py --mode status
```

#### Dry Run (Testing)
```bash
python main.py --mode full --dry-run --verbose
```

## ⚙️ Configuration Options

### User Profile
```json
{
  "user_profile": {
    "name": "Your Name",
    "email": "your.email@example.com",
    "target_positions": ["Full Stack Developer", "Software Engineer"],
    "skills": ["Java", "Python", "React", "Docker"],
    "experience_years": 3,
    "remote_preference": true,
    "visa_required": false
  }
}
```

### AI Configuration
```json
{
  "ai": {
    "openai_api_key": "sk-...",
    "model_name": "gpt-3.5-turbo",
    "temperature": 0.4,
    "fallback_to_local": true
  }
}
```

### Application Settings
```json
{
  "application": {
    "max_applications_per_day": 20,
    "minimum_match_score": 60.0,
    "application_delay_hours": 2,
    "preferred_companies": ["Google", "Microsoft"]
  }
}
```

## 🧠 AI Features

### Job Matching Algorithm
- **Skills Analysis**: Semantic matching between job requirements and user skills
- **Experience Matching**: Intelligent seniority level assessment
- **Location Preferences**: Geographic and remote work compatibility
- **Company Culture Fit**: Analysis of company values and work environment

### Document Generation
- **Resume Tailoring**: Automatic emphasis of relevant experience and skills
- **Cover Letter Personalization**: Company-specific content generation
- **ATS Optimization**: Keyword optimization for applicant tracking systems
- **Multiple Formats**: Support for various document formats

### Application Intelligence
- **Form Field Detection**: Automatic identification of form fields
- **Strategy Selection**: Choose optimal application method per job
- **Error Handling**: Robust error recovery and retry mechanisms
- **Success Tracking**: Comprehensive application result monitoring

## 📊 Analytics Dashboard

View comprehensive analytics with:
```bash
python main.py --mode status
```

**Metrics Include:**
- Total jobs found and processed
- Application success rates
- Average relevance scores
- Source performance comparison
- Weekly/monthly trends

## 🛡️ Security & Privacy

- **Stealth Browsing**: Advanced anti-detection mechanisms
- **Data Protection**: Local data storage with encryption options
- **Rate Limiting**: Respectful scraping practices
- **Error Recovery**: Robust handling of edge cases

## 🔧 Advanced Usage

### Custom Scraping
```python
from job_finder.job_aggregator import EnhancedJobFinderAgent
from core.config import load_config

config = load_config()
agent = EnhancedJobFinderAgent(config.user_profile, db_manager, config.scraping)
jobs = agent.run_comprehensive_search(max_jobs=100)
```

### Custom Document Generation
```python
from modifier.cv_cover_editor import AIDocumentModifier

modifier = AIDocumentModifier(user_profile, ai_config)
resume_path, cover_path = modifier.generate_documents_for_job(job)
```

### Database Operations
```python
from core.database import DatabaseManager

db = DatabaseManager()
jobs = db.get_jobs(status='pending', min_score=70.0)
stats = db.get_statistics()
```

## 🐛 Troubleshooting

### Common Issues

1. **Chrome Driver Issues**
   ```bash
   pip install --upgrade undetected-chromedriver
   ```

2. **OpenAI API Errors**
   - Verify API key in config.json
   - Check API quota and billing
   - Enable fallback mode: `"fallback_to_local": true`

3. **Email Authentication**
   - Use app-specific passwords for Gmail
   - Enable 2FA and generate app password
   - Check SMTP settings for your provider

4. **Job Site Blocking**
   - Enable stealth mode: `"stealth_mode": true`
   - Reduce scraping frequency
   - Use proxy rotation if needed

### Debug Mode
```bash
python main.py --verbose --dry-run
```

## 📈 Performance Optimization

### Speed Optimization
- Use headless browsing: `"headless_mode": true`
- Increase delay ranges for stability
- Limit concurrent operations

### Accuracy Improvement
- Update skills list regularly
- Refine target positions
- Adjust minimum match score
- Review and improve templates

## 🤝 Contributing

1. Fork the repository
2. Create feature branch: `git checkout -b feature-name`
3. Commit changes: `git commit -am 'Add feature'`
4. Push branch: `git push origin feature-name`
5. Submit pull request

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## ⚠️ Legal Disclaimer

- **Use Responsibly**: Respect websites' terms of service and robots.txt
- **Rate Limiting**: Built-in delays prevent overwhelming servers
- **Personal Use**: Intended for personal job searching, not commercial scraping
- **Compliance**: Users responsible for ensuring compliance with local laws

## 🆘 Support

- **Issues**: [GitHub Issues](https://github.com/yourusername/jobautopilot/issues)
- **Discussions**: [GitHub Discussions](https://github.com/yourusername/jobautopilot/discussions)
- **Documentation**: [Wiki](https://github.com/yourusername/jobautopilot/wiki)

## 🙏 Acknowledgments

- OpenAI for GPT API
- Selenium WebDriver team
- Beautiful Soup developers
- Open source community

---

**Made with ❤️ for job seekers everywhere**

*Automate your job search, focus on what matters most - preparing for interviews and building your career.*