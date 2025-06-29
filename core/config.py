"""
Configuration Management for JobAutoPilot
"""

import json
import logging
import os
from pathlib import Path
from typing import Dict, List, Optional
from dataclasses import dataclass, asdict, field

@dataclass
class UserProfile:
    """User profile configuration"""
    name: str = ""
    email: str = ""
    phone: str = ""
    location: str = "Morocco"
    target_positions: List[str] = field(default_factory=lambda: ["Full Stack Developer", "Java Developer", "Software Engineer"])
    skills: List[str] = field(default_factory=lambda: ["Java", "Spring Boot", "React", "JavaScript", "Python"])
    experience_years: int = 3
    education: str = "Bachelor's Degree"
    preferred_locations: List[str] = field(default_factory=lambda: ["Casablanca", "Rabat", "Remote"])
    remote_preference: bool = True
    visa_required: bool = False
    salary_min: int = 8000
    salary_max: int = 25000
    base_resume_path: str = "templates/resume_template.txt"
    cover_letter_template_path: str = "templates/cover_letter_template.txt"

@dataclass
class ScrapingConfig:
    """Web scraping configuration"""
    max_jobs_per_site: int = 30
    delay_min: float = 2.0
    delay_max: float = 5.0
    user_agents_rotation: bool = True
    proxy_enabled: bool = False
    proxy_list: List[str] = field(default_factory=list)
    headless_mode: bool = False
    stealth_mode: bool = True
    timeout_seconds: int = 30

@dataclass
class AIConfig:
    """AI service configuration"""
    openai_api_key: str = ""
    model_name: str = "gpt-3.5-turbo"
    max_tokens: int = 2000
    temperature: float = 0.4
    fallback_to_local: bool = True
    local_model_path: str = ""

@dataclass
class EmailConfig:
    """Email configuration for applications"""
    smtp_server: str = "smtp.gmail.com"
    smtp_port: int = 587
    email: str = ""
    password: str = ""
    use_tls: bool = True

@dataclass
class ApplicationConfig:
    """Application behavior configuration"""
    max_applications_per_day: int = 20
    apply_immediately: bool = False
    minimum_match_score: float = 60.0
    exclude_companies: List[str] = field(default_factory=list)
    preferred_companies: List[str] = field(default_factory=list)
    application_delay_hours: int = 2

@dataclass
class JobAutoPilotConfig:
    """Main configuration class"""
    user_profile: UserProfile = field(default_factory=UserProfile)
    scraping: ScrapingConfig = field(default_factory=ScrapingConfig)
    ai: AIConfig = field(default_factory=AIConfig)
    email: EmailConfig = field(default_factory=EmailConfig)
    application: ApplicationConfig = field(default_factory=ApplicationConfig)
    database_path: str = "data/jobautopilot.db"
    log_level: str = "INFO"
    enable_notifications: bool = True

def create_default_config() -> JobAutoPilotConfig:
    """Create default configuration"""
    return JobAutoPilotConfig()

def load_config(config_path: str = "config.json") -> JobAutoPilotConfig:
    """Load configuration from JSON file"""
    config_file = Path(config_path)
    
    if not config_file.exists():
        # Create default config
        default_config = create_default_config()
        save_config(default_config, config_path)
        print(f"📝 Created default config at {config_path}")
        print("⚠️  Please update config.json with your details before running!")
        return default_config
    
    try:
        with open(config_file, 'r', encoding='utf-8') as f:
            config_dict = json.load(f)
        
        # Convert nested dictionaries to dataclasses
        config = JobAutoPilotConfig(
            user_profile=UserProfile(**config_dict.get('user_profile', {})),
            scraping=ScrapingConfig(**config_dict.get('scraping', {})),
            ai=AIConfig(**config_dict.get('ai', {})),
            email=EmailConfig(**config_dict.get('email', {})),
            application=ApplicationConfig(**config_dict.get('application', {}))
        )
        
        # Update other fields
        for key, value in config_dict.items():
            if hasattr(config, key) and key not in ['user_profile', 'scraping', 'ai', 'email', 'application']:
                setattr(config, key, value)
        
        return config
        
    except Exception as e:
        print(f"❌ Error loading config: {e}")
        print("📝 Using default configuration")
        return create_default_config()

def save_config(config: JobAutoPilotConfig, config_path: str = "config.json"):
    """Save configuration to JSON file"""
    try:
        config_dict = asdict(config)
        
        with open(config_path, 'w', encoding='utf-8') as f:
            json.dump(config_dict, f, indent=2, ensure_ascii=False)
        
        print(f"✅ Configuration saved to {config_path}")
        
    except Exception as e:
        print(f"❌ Error saving config: {e}")

def setup_logging(log_level: str = "INFO"):
    """Setup logging configuration"""
    # Create logs directory
    Path("logs").mkdir(exist_ok=True)
    
    # Configure logging
    level = getattr(logging, log_level.upper(), logging.INFO)
    
    logging.basicConfig(
        level=level,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler('logs/jobautopilot.log', encoding='utf-8'),
            logging.StreamHandler()
        ]
    )
    
    # Reduce noise from external libraries
    logging.getLogger('selenium').setLevel(logging.WARNING)
    logging.getLogger('urllib3').setLevel(logging.WARNING)
    logging.getLogger('requests').setLevel(logging.WARNING)

def validate_config(config: JobAutoPilotConfig) -> List[str]:
    """Validate configuration and return list of issues"""
    issues = []
    
    # Check required fields
    if not config.user_profile.name:
        issues.append("User name is required")
    
    if not config.user_profile.email:
        issues.append("User email is required")
    
    if not config.user_profile.target_positions:
        issues.append("At least one target position is required")
    
    if not config.user_profile.skills:
        issues.append("At least one skill is required")
    
    # Check AI configuration
    if not config.ai.openai_api_key and not config.ai.fallback_to_local:
        issues.append("OpenAI API key is required or enable local fallback")
    
    # Check email configuration for applications
    if not config.email.email or not config.email.password:
        issues.append("Email credentials are required for applications")
    
    # Check file paths
    resume_path = Path(config.user_profile.base_resume_path)
    if not resume_path.exists():
        issues.append(f"Base resume not found: {resume_path}")
    
    cover_letter_path = Path(config.user_profile.cover_letter_template_path)
    if not cover_letter_path.exists():
        issues.append(f"Cover letter template not found: {cover_letter_path}")
    
    return issues

# Environment variable overrides
def load_env_overrides(config: JobAutoPilotConfig) -> JobAutoPilotConfig:
    """Load configuration overrides from environment variables"""
    
    # AI Config
    if os.getenv("OPENAI_API_KEY"):
        config.ai.openai_api_key = os.getenv("OPENAI_API_KEY")
    
    # Email Config
    if os.getenv("EMAIL_USER"):
        config.email.email = os.getenv("EMAIL_USER")
    if os.getenv("EMAIL_PASSWORD"):
        config.email.password = os.getenv("EMAIL_PASSWORD")
    
    # Database
    if os.getenv("DATABASE_PATH"):
        config.database_path = os.getenv("DATABASE_PATH")
    
    # Log Level
    if os.getenv("LOG_LEVEL"):
        config.log_level = os.getenv("LOG_LEVEL")
    
    return config