"""
Enhanced Job Finder Agent with AI-Powered Matching
Comprehensive job scraping with intelligent filtering and scoring
"""

import undetected_chromedriver as uc
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.common.action_chains import ActionChains
from selenium.common.exceptions import TimeoutException, NoSuchElementException, WebDriverException
import requests
from bs4 import BeautifulSoup
import pandas as pd
import json
import time
import random
import re
import hashlib
from fake_useragent import UserAgent
from urllib.parse import urlencode, quote_plus, urlparse
import os
from datetime import datetime, timedelta
import logging
from typing import List, Dict, Optional, Tuple
from pathlib import Path

# ML and NLP imports
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
import nltk
from nltk.corpus import stopwords
from nltk.tokenize import word_tokenize
from nltk.stem import WordNetLemmatizer

from core.database import DatabaseManager, JobListing
from core.config import UserProfile, ScrapingConfig

logger = logging.getLogger(__name__)

class JobMatchingEngine:
    """AI-powered job matching and scoring engine"""
    
    def __init__(self, user_profile: UserProfile):
        self.user_profile = user_profile
        self.vectorizer = TfidfVectorizer(
            stop_words='english',
            max_features=1000,
            ngram_range=(1, 2),
            min_df=1
        )
        self.lemmatizer = WordNetLemmatizer()
        self._download_nltk_data()
    
    def _download_nltk_data(self):
        """Download required NLTK data if not present"""
        try:
            nltk.data.find('tokenizers/punkt')
            nltk.data.find('corpora/stopwords')
            nltk.data.find('corpora/wordnet')
        except LookupError:
            logger.info("📥 Downloading NLTK data...")
            nltk.download('punkt', quiet=True)
            nltk.download('stopwords', quiet=True)
            nltk.download('wordnet', quiet=True)
    
    def preprocess_text(self, text: str) -> str:
        """Clean and preprocess text for analysis"""
        if not text:
            return ""
        
        # Remove HTML tags and special characters
        text = re.sub(r'<[^>]+>', '', text)
        text = re.sub(r'[^\w\s]', ' ', text)
        text = re.sub(r'\s+', ' ', text)
        text = text.lower().strip()
        
        # Tokenize and lemmatize
        try:
            tokens = word_tokenize(text)
            tokens = [self.lemmatizer.lemmatize(token) for token in tokens if len(token) > 2]
            
            # Remove stopwords
            stop_words = set(stopwords.words('english'))
            tokens = [token for token in tokens if token not in stop_words]
            
            return ' '.join(tokens)
        except:
            return text
    
    def extract_job_requirements(self, job_description: str, job_requirements: str = "") -> Dict:
        """Extract structured requirements from job text"""
        full_text = f"{job_description} {job_requirements}".lower()
        
        requirements = {
            'technical_skills': [],
            'experience_years': 0,
            'education_level': '',
            'languages': [],
            'soft_skills': [],
            'must_have': [],
            'nice_to_have': [],
            'frameworks': [],
            'tools': []
        }
        
        # Technical skills patterns
        tech_patterns = {
            'languages': r'\b(java|python|javascript|typescript|c\+\+|c#|php|ruby|go|rust|kotlin|scala|swift)\b',
            'frameworks': r'\b(spring|hibernate|react|angular|vue|django|flask|express|laravel|rails|\.net)\b',
            'databases': r'\b(mysql|postgresql|mongodb|redis|elasticsearch|oracle|sql server|sqlite)\b',
            'tools': r'\b(docker|kubernetes|git|jenkins|maven|gradle|webpack|npm|yarn|jira|confluence)\b',
            'cloud': r'\b(aws|azure|gcp|google cloud|amazon web services|microsoft azure)\b'
        }
        
        for category, pattern in tech_patterns.items():
            matches = re.findall(pattern, full_text)
            if category == 'frameworks':
                requirements['frameworks'].extend(matches)
            elif category in ['databases', 'cloud', 'tools']:
                requirements['tools'].extend(matches)
            else:
                requirements['technical_skills'].extend(matches)
        
        # Experience level extraction
        exp_patterns = [
            r'(\d+)\+?\s*(?:to\s*\d+)?\s*years?\s*(?:of\s*)?(?:experience|exp)',
            r'(\d+)\+?\s*years?\s*(?:minimum|min|required)',
            r'minimum\s*(?:of\s*)?(\d+)\s*years?',
            r'at\s*least\s*(\d+)\s*years?'
        ]
        
        for pattern in exp_patterns:
            match = re.search(pattern, full_text)
            if match:
                requirements['experience_years'] = int(match.group(1))
                break
        
        # Education level
        if any(term in full_text for term in ['phd', 'doctorate', 'ph.d']):
            requirements['education_level'] = 'phd'
        elif any(term in full_text for term in ['master', 'msc', 'ms', 'mba']):
            requirements['education_level'] = 'masters'
        elif any(term in full_text for term in ['bachelor', 'bsc', 'bs', 'ba', 'degree']):
            requirements['education_level'] = 'bachelors'
        
        # Languages
        lang_pattern = r'\b(english|french|arabic|spanish|german|italian|portuguese|chinese|japanese)\b'
        requirements['languages'] = re.findall(lang_pattern, full_text)
        
        # Soft skills
        soft_skills_pattern = r'\b(leadership|communication|teamwork|problem.solving|analytical|creative|innovative|adaptable|collaborative)\b'
        requirements['soft_skills'] = re.findall(soft_skills_pattern, full_text)
        
        return requirements
    
    def calculate_skills_match(self, job_requirements: Dict, user_skills: List[str]) -> Tuple[float, str]:
        """Calculate skills matching score"""
        user_skills_lower = [skill.lower() for skill in user_skills]
        job_skills = job_requirements.get('technical_skills', []) + job_requirements.get('frameworks', [])
        
        if not job_skills:
            return 0.5, "No specific technical skills mentioned"
        
        matched_skills = []
        for skill in job_skills:
            if any(skill in user_skill for user_skill in user_skills_lower):
                matched_skills.append(skill)
        
        match_ratio = len(matched_skills) / len(job_skills) if job_skills else 0
        match_score = min(match_ratio * 100, 100)
        
        explanation = f"Matched {len(matched_skills)}/{len(job_skills)} skills: {', '.join(matched_skills[:3])}"
        return match_score, explanation
    
    def calculate_experience_match(self, required_years: int, user_years: int) -> Tuple[float, str]:
        """Calculate experience level match"""
        if required_years == 0:
            return 80, "No specific experience requirement"
        
        if user_years >= required_years:
            # Perfect match or overqualified
            if user_years <= required_years + 2:
                return 100, f"Perfect match: {user_years} >= {required_years} years"
            else:
                # Slightly penalize overqualification
                return 90, f"Overqualified: {user_years} > {required_years} years"
        else:
            # Under-qualified but might still be considered
            gap = required_years - user_years
            if gap <= 1:
                return 75, f"Close match: {user_years} vs {required_years} years required"
            elif gap <= 2:
                return 60, f"Slightly under: {user_years} vs {required_years} years required"
            else:
                return 30, f"Under-qualified: {user_years} vs {required_years} years required"
    
    def calculate_location_match(self, job: JobListing, user_profile: UserProfile) -> Tuple[float, str]:
        """Calculate location preference match"""
        if job.remote and user_profile.remote_preference:
            return 100, "Perfect: Remote job matches preference"
        
        job_location_lower = job.location.lower()
        
        # Check preferred locations
        for pref_location in user_profile.preferred_locations:
            if pref_location.lower() in job_location_lower:
                return 90, f"Excellent: {pref_location} matches preference"
        
        # Check same country
        if job.country.lower() == user_profile.location.lower():
            return 70, "Good: Same country"
        
        # Check visa sponsorship if needed
        if job.visa_sponsorship and user_profile.visa_required:
            return 80, "Good: Visa sponsorship available"
        
        # No match
        return 30, "Location doesn't match preferences"
    
    def calculate_comprehensive_match_score(self, job: JobListing) -> Tuple[float, str]:
        """Calculate comprehensive job match score"""
        explanations = []
        total_score = 0
        
        # Extract job requirements
        requirements = self.extract_job_requirements(job.description, job.requirements)
        
        # 1. Skills matching (40% weight)
        skills_score, skills_exp = self.calculate_skills_match(requirements, self.user_profile.skills)
        total_score += skills_score * 0.4
        explanations.append(f"Skills: {skills_score:.0f}% ({skills_exp})")
        
        # 2. Experience matching (25% weight)
        exp_score, exp_exp = self.calculate_experience_match(
            requirements['experience_years'], 
            self.user_profile.experience_years
        )
        total_score += exp_score * 0.25
        explanations.append(f"Experience: {exp_score:.0f}% ({exp_exp})")
        
        # 3. Location matching (20% weight)
        loc_score, loc_exp = self.calculate_location_match(job, self.user_profile)
        total_score += loc_score * 0.2
        explanations.append(f"Location: {loc_score:.0f}% ({loc_exp})")
        
        # 4. Title relevance (15% weight)
        title_score = self.calculate_title_relevance(job.title)
        total_score += title_score * 0.15
        explanations.append(f"Title: {title_score:.0f}%")
        
        # Bonus factors
        bonus_score = 0
        bonus_explanations = []
        
        if job.visa_sponsorship and self.user_profile.visa_required:
            bonus_score += 5
            bonus_explanations.append("Visa sponsorship")
        
        if job.remote and self.user_profile.remote_preference:
            bonus_score += 3
            bonus_explanations.append("Remote work")
        
        # Check for seniority match
        title_lower = job.title.lower()
        if 'senior' in title_lower and self.user_profile.experience_years >= 5:
            bonus_score += 3
            bonus_explanations.append("Senior role fits experience")
        elif 'junior' in title_lower and self.user_profile.experience_years <= 3:
            bonus_score += 3
            bonus_explanations.append("Junior role fits experience")
        
        total_score += bonus_score
        
        if bonus_explanations:
            explanations.append(f"Bonus: {', '.join(bonus_explanations)} (+{bonus_score})")
        
        # Cap at 100
        final_score = min(total_score, 100)
        
        return final_score, " | ".join(explanations)
    
    def calculate_title_relevance(self, job_title: str) -> float:
        """Calculate how well job title matches target positions"""
        job_title_lower = job_title.lower()
        
        # Direct matches
        for target in self.user_profile.target_positions:
            if target.lower() in job_title_lower:
                return 100
        
        # Partial matches
        for target in self.user_profile.target_positions:
            target_words = target.lower().split()
            matches = sum(1 for word in target_words if word in job_title_lower)
            if matches > 0:
                return min(80, (matches / len(target_words)) * 100)
        
        # Generic developer roles
        if any(term in job_title_lower for term in ['developer', 'engineer', 'programmer']):
            return 60
        
        return 30


class EnhancedJobFinderAgent:
    """Enhanced job finder with multiple sources and intelligent filtering"""
    
    def __init__(self, user_profile: UserProfile, db_manager: DatabaseManager, 
                 scraping_config: ScrapingConfig):
        self.user_profile = user_profile
        self.db_manager = db_manager
        self.scraping_config = scraping_config
        self.matching_engine = JobMatchingEngine(user_profile)
        self.ua = UserAgent()
        self.session = requests.Session()
        
        # Setup cache directory
        self.cache_dir = Path("cache")
        self.cache_dir.mkdir(exist_ok=True)
    
    def create_stealth_driver(self) -> uc.Chrome:
        """Create advanced stealth browser driver"""
        options = uc.ChromeOptions()
        
        # Advanced stealth options
        stealth_options = [
            '--no-sandbox',
            '--disable-dev-shm-usage',
            '--disable-blink-features=AutomationControlled',
            '--disable-extensions',
            '--disable-plugins-discovery',
            '--disable-web-security',
            '--allow-running-insecure-content',
            '--no-first-run',
            '--no-default-browser-check',
            '--disable-default-apps',
            '--disable-popup-blocking',
            '--disable-notifications',
            '--disable-background-timer-throttling',
            '--disable-backgrounding-occluded-windows',
            '--disable-renderer-backgrounding',
            '--disable-features=TranslateUI',
            '--disable-ipc-flooding-protection',
            '--disable-hang-monitor',
            '--disable-prompt-on-repost',
            '--disable-sync',
            '--disable-translate',
            '--hide-scrollbars',
            '--mute-audio'
        ]
        
        for option in stealth_options:
            options.add_argument(option)
        
        # Headless mode if configured
        if self.scraping_config.headless_mode:
            options.add_argument('--headless')
        
        # Random user agent and window size
        options.add_argument(f'--user-agent={self.ua.random}')
        window_sizes = ['1920,1080', '1366,768', '1440,900', '1536,864', '1280,720', '1600,900']
        options.add_argument(f'--window-size={random.choice(window_sizes)}')
        
        try:
            driver = uc.Chrome(options=options)
            
            # Execute stealth scripts
            stealth_scripts = [
                "Object.defineProperty(navigator, 'webdriver', {get: () => undefined})",
                "Object.defineProperty(navigator, 'plugins', {get: () => [1, 2, 3, 4, 5]})",
                "Object.defineProperty(navigator, 'languages', {get: () => ['en-US', 'en', 'fr']})",
                "window.chrome = { runtime: {} }",
                "Object.defineProperty(navigator, 'permissions', {get: () => ({query: () => Promise.resolve({state: 'granted'})})})",
                "Object.defineProperty(navigator, 'hardwareConcurrency', {get: () => 4})",
                "Object.defineProperty(navigator, 'deviceMemory', {get: () => 8})"
            ]
            
            for script in stealth_scripts:
                try:
                    driver.execute_script(script)
                except:
                    pass
            
            # Override CDP commands
            try:
                driver.execute_cdp_cmd('Network.setUserAgentOverride', {
                    "userAgent": self.ua.random,
                    "acceptLanguage": "en-US,en;q=0.9,fr;q=0.8",
                    "platform": "Win32"
                })
            except:
                pass
            
            return driver
            
        except Exception as e:
            logger.error(f"Failed to create stealth driver: {e}")
            raise
    
    def human_like_delay(self, min_delay: float = None, max_delay: float = None):
        """Human-like random delay"""
        min_delay = min_delay or self.scraping_config.delay_min
        max_delay = max_delay or self.scraping_config.delay_max
        delay = random.uniform(min_delay, max_delay)
        time.sleep(delay)
    
    def extract_job_details(self, driver: uc.Chrome, job_url: str) -> Tuple[str, str]:
        """Extract detailed job description and requirements"""
        try:
            driver.get(job_url)
            self.human_like_delay(2, 4)
            
            # Common selectors for job descriptions across platforms
            description_selectors = [
                '[data-testid="jobsearch-JobComponent-description"]',
                '.jobsearch-jobDescriptionText',
                '#jobDescriptionText',
                '.job-description',
                '.jobDescription',
                '[data-testid="job-description"]',
                '.description',
                'div[data-testid="jobDescription"]',
                '.job-view-component',
                '.job-details',
                '.vacancy-description'
            ]
            
            description = ""
            requirements = ""
            
            for selector in description_selectors:
                try:
                    element = driver.find_element(By.CSS_SELECTOR, selector)
                    full_text = element.text.strip()
                    
                    if len(full_text) > 100:  # Ensure we got substantial content
                        # Try to split description and requirements
                        lower_text = full_text.lower()
                        
                        # Look for requirements section
                        req_indicators = [
                            'requirements:', 'required:', 'qualifications:', 
                            'what you need:', 'you should have:', 'skills required:'
                        ]
                        
                        for indicator in req_indicators:
                            if indicator in lower_text:
                                parts = re.split(rf'{re.escape(indicator)}', full_text, flags=re.IGNORECASE)
                                if len(parts) > 1:
                                    description = parts[0].strip()
                                    requirements = indicator + parts[1].strip()
                                    break
                        
                        if not requirements:
                            description = full_text
                        
                        break
                        
                except NoSuchElementException:
                    continue
            
            return description, requirements
            
        except Exception as e:
            logger.warning(f"Failed to extract job details from {job_url}: {e}")
            return "", ""
    
    def scrape_indeed_morocco(self, max_results: int = 30) -> List[JobListing]:
        """Enhanced Indeed Morocco scraping"""
        logger.info("🇲🇦 Scraping Indeed Morocco...")
        jobs = []
        
        driver = self.create_stealth_driver()
        try:
            # Build dynamic search queries
            base_queries = self.user_profile.target_positions.copy()
            
            # Add variations
            query_variations = []
            for query in base_queries:
                query_variations.extend([
                    query,
                    f"{query} remote",
                    f"senior {query}",
                    f"junior {query}",
                    query.replace("developer", "dev"),
                    query.replace("full stack", "fullstack")
                ])
            
            # Remove duplicates
            unique_queries = list(set(query_variations))
            
            for query in unique_queries[:5]:  # Limit queries to avoid rate limiting
                if len(jobs) >= max_results:
                    break
                
                search_url = (
                    f"https://ma.indeed.com/jobs?"
                    f"q={quote_plus(query)}&"
                    f"l=Morocco&"
                    f"sort=date&"
                    f"fromage=7&"
                    f"filter=0"
                )
                
                logger.info(f"🔍 Searching: '{query}' in Morocco")
                
                try:
                    driver.get(search_url)
                    self.human_like_delay(3, 6)
                    
                    # Handle popups and overlays
                    self._handle_popups(driver)
                    
                    # Scroll to load more results
                    self._scroll_page(driver, 3)
                    
                    # Extract job cards
                    job_cards = driver.find_elements(By.CSS_SELECTOR, '[data-jk]')
                    logger.info(f"Found {len(job_cards)} job cards")
                    
                    for card in job_cards[:10]:  # Limit per query
                        try:
                            job_data = self._extract_indeed_job_card(driver, card)
                            if job_data:
                                # Calculate match score
                                score, explanation = self.matching_engine.calculate_comprehensive_match_score(job_data)
                                job_data.relevance_score = score
                                job_data.match_explanation = explanation
                                
                                jobs.append(job_data)
                                logger.debug(f"✅ {job_data.title} at {job_data.company} (Score: {score:.1f})")
                        
                        except Exception as e:
                            logger.warning(f"Error extracting job card: {e}")
                            continue
                
                except Exception as e:
                    logger.error(f"Error scraping query '{query}': {e}")
                    continue
                
                self.human_like_delay(3, 5)
        
        except Exception as e:
            logger.error(f"Fatal error in Indeed Morocco scraping: {e}")
        finally:
            try:
                driver.quit()
            except:
                pass
        
        logger.info(f"🎉 Indeed Morocco: Found {len(jobs)} jobs")
        return jobs
    
    def _extract_indeed_job_card(self, driver: uc.Chrome, card) -> Optional[JobListing]:
        """Extract job data from Indeed job card"""
        try:
            # Basic job info
            title_elem = card.find_element(By.CSS_SELECTOR, 'h2 a span[title]')
            company_elem = card.find_element(By.CSS_SELECTOR, '[data-testid="company-name"]')
            location_elem = card.find_element(By.CSS_SELECTOR, '[data-testid="job-location"]')
            link_elem = card.find_element(By.CSS_SELECTOR, 'h2 a')
            
            job_url = "https://ma.indeed.com" + link_elem.get_attribute('href')
            job_id = hashlib.md5(job_url.encode()).hexdigest()
            
            # Extract salary if available
            salary = "Not specified"
            try:
                salary_elem = card.find_element(By.CSS_SELECTOR, '[data-testid="attribute_snippet_testid"]')
                salary = salary_elem.text
            except NoSuchElementException:
                pass
            
            # Get snippet description
            snippet = ""
            try:
                snippet_elem = card.find_element(By.CSS_SELECTOR, '.slider_container .slider_item')
                snippet = snippet_elem.text
            except NoSuchElementException:
                pass
            
            # Get full job description (optional - can be slow)
            description, requirements = "", ""
            if len(jobs) < 20:  # Only get full details for first few jobs
                description, requirements = self.extract_job_details(driver, job_url)
            
            if not description:
                description = snippet
            
            return JobListing(
                id=job_id,
                title=title_elem.get_attribute('title'),
                company=company_elem.text.strip(),
                location=location_elem.text.strip(),
                salary=salary,
                description=description,
                requirements=requirements,
                url=job_url,
                source='Indeed Morocco',
                date_scraped=datetime.now().isoformat(),
                country='Morocco',
                remote='remote' in (description + requirements + snippet).lower(),
                visa_sponsorship='visa' in (description + requirements + snippet).lower()
            )
        
        except Exception as e:
            logger.warning(f"Error extracting Indeed job card: {e}")
            return None
    
    def scrape_linkedin_jobs(self, max_results: int = 20) -> List[JobListing]:
        """Enhanced LinkedIn job scraping"""
        logger.info("💼 Scraping LinkedIn Jobs...")
        jobs = []
        
        driver = self.create_stealth_driver()
        try:
            for query in self.user_profile.target_positions[:3]:  # Limit queries
                if len(jobs) >= max_results:
                    break
                
                # Build LinkedIn search URL
                search_params = {
                    'keywords': query,
                    'location': 'Morocco',
                    'f_TPR': 'r86400',  # Last 24 hours
                    'f_JT': 'F',  # Full-time
                    'f_WT': '2' if self.user_profile.remote_preference else None  # Remote work
                }
                
                # Remove None values
                search_params = {k: v for k, v in search_params.items() if v is not None}
                
                linkedin_url = f"https://www.linkedin.com/jobs/search/?{urlencode(search_params)}"
                logger.info(f"🔍 LinkedIn: '{query}' in Morocco")
                
                try:
                    driver.get(linkedin_url)
                    self.human_like_delay(4, 7)
                    
                    # Handle login popup if present
                    try:
                        close_button = driver.find_element(By.CSS_SELECTOR, '.modal__dismiss')
                        close_button.click()
                        self.human_like_delay(1, 2)
                    except NoSuchElementException:
                        pass
                    
                    # Scroll and load more jobs
                    self._scroll_page(driver, 4)
                    
                    # Try to click "Show more jobs" button
                    for _ in range(2):
                        try:
                            show_more = driver.find_element(By.CSS_SELECTOR, '.infinite-scroller__show-more-button')
                            driver.execute_script("arguments[0].click();", show_more)
                            self.human_like_delay(3, 5)
                        except NoSuchElementException:
                            break
                    
                    # Extract job cards
                    job_cards = driver.find_elements(By.CSS_SELECTOR, '.job-search-card')
                    logger.info(f"Found {len(job_cards)} LinkedIn job cards")
                    
                    for card in job_cards[:8]:  # Limit per query
                        try:
                            job_data = self._extract_linkedin_job_card(driver, card)
                            if job_data:
                                # Calculate match score
                                score, explanation = self.matching_engine.calculate_comprehensive_match_score(job_data)
                                job_data.relevance_score = score
                                job_data.match_explanation = explanation
                                
                                jobs.append(job_data)
                                logger.debug(f"✅ {job_data.title} at {job_data.company} (Score: {score:.1f})")
                        
                        except Exception as e:
                            logger.warning(f"Error extracting LinkedIn job: {e}")
                            continue
                
                except Exception as e:
                    logger.error(f"Error scraping LinkedIn for '{query}': {e}")
                    continue
                
                self.human_like_delay(4, 6)
        
        except Exception as e:
            logger.error(f"Fatal error in LinkedIn scraping: {e}")
        finally:
            try:
                driver.quit()
            except:
                pass
        
        logger.info(f"🎉 LinkedIn: Found {len(jobs)} jobs")
        return jobs
    
    def _extract_linkedin_job_card(self, driver: uc.Chrome, card) -> Optional[JobListing]:
        """Extract job data from LinkedIn job card"""
        try:
            title = card.find_element(By.CSS_SELECTOR, '.base-search-card__title').text.strip()
            company = card.find_element(By.CSS_SELECTOR, '.base-search-card__subtitle').text.strip()
            location = card.find_element(By.CSS_SELECTOR, '.job-search-card__location').text.strip()
            link = card.find_element(By.CSS_SELECTOR, '.base-card__full-link').get_attribute('href')
            
            job_id = hashlib.md5(link.encode()).hexdigest()
            
            # Try to get job description by clicking on the card
            description = ""
            try:
                card.click()
                self.human_like_delay(2, 3)
                
                # Wait for description to load
                description_elem = WebDriverWait(driver, 5).until(
                    EC.presence_of_element_located((By.CSS_SELECTOR, '.show-more-less-html__markup'))
                )
                description = description_elem.text
            except:
                # Fallback to snippet if available
                try:
                    snippet_elem = card.find_element(By.CSS_SELECTOR, '.job-search-card__snippet')
                    description = snippet_elem.text
                except NoSuchElementException:
                    pass
            
            return JobListing(
                id=job_id,
                title=title,
                company=company,
                location=location,
                salary="Not specified",
                description=description,
                requirements="",
                url=link,
                source='LinkedIn',
                date_scraped=datetime.now().isoformat(),
                country='Morocco',
                remote='remote' in description.lower(),
                visa_sponsorship='visa' in description.lower()
            )
        
        except Exception as e:
            logger.warning(f"Error extracting LinkedIn job: {e}")
            return None
    
    def scrape_glassdoor_jobs(self, max_results: int = 15) -> List[JobListing]:
        """Scrape Glassdoor for job listings"""
        logger.info("🏢 Scraping Glassdoor...")
        jobs = []
        
        driver = self.create_stealth_driver()
        try:
            for query in self.user_profile.target_positions[:2]:  # Limit queries
                if len(jobs) >= max_results:
                    break
                
                search_url = (
                    f"https://www.glassdoor.com/Job/morocco-{quote_plus(query)}-jobs-"
                    f"SRCH_IL.0,7_IN176_KO8,{8+len(query)}.htm"
                )
                
                logger.info(f"🔍 Glassdoor: '{query}' in Morocco")
                
                try:
                    driver.get(search_url)
                    self.human_like_delay(4, 7)
                    
                    # Handle cookie consent
                    try:
                        cookie_button = driver.find_element(By.CSS_SELECTOR, '#onetrust-accept-btn-handler')
                        cookie_button.click()
                        self.human_like_delay(1, 2)
                    except NoSuchElementException:
                        pass
                    
                    # Extract job listings
                    job_cards = driver.find_elements(By.CSS_SELECTOR, '[data-test="job-listing"]')
                    
                    for card in job_cards[:8]:
                        try:
                            job_data = self._extract_glassdoor_job_card(card)
                            if job_data:
                                # Calculate match score
                                score, explanation = self.matching_engine.calculate_comprehensive_match_score(job_data)
                                job_data.relevance_score = score
                                job_data.match_explanation = explanation
                                
                                jobs.append(job_data)
                        
                        except Exception as e:
                            logger.warning(f"Error extracting Glassdoor job: {e}")
                            continue
                
                except Exception as e:
                    logger.error(f"Error scraping Glassdoor: {e}")
                    continue
                
                self.human_like_delay(3, 5)
        
        except Exception as e:
            logger.error(f"Fatal error in Glassdoor scraping: {e}")
        finally:
            try:
                driver.quit()
            except:
                pass
        
        logger.info(f"🎉 Glassdoor: Found {len(jobs)} jobs")
        return jobs
    
    def _extract_glassdoor_job_card(self, card) -> Optional[JobListing]:
        """Extract job data from Glassdoor job card"""
        try:
            title_elem = card.find_element(By.CSS_SELECTOR, '[data-test="job-title"]')
            company_elem = card.find_element(By.CSS_SELECTOR, '[data-test="employer-name"]')
            location_elem = card.find_element(By.CSS_SELECTOR, '[data-test="job-location"]')
            link_elem = card.find_element(By.CSS_SELECTOR, '[data-test="job-title"] a')
            
            job_url = "https://www.glassdoor.com" + link_elem.get_attribute('href')
            job_id = hashlib.md5(job_url.encode()).hexdigest()
            
            # Try to get salary
            salary = "Not specified"
            try:
                salary_elem = card.find_element(By.CSS_SELECTOR, '[data-test="detailSalary"]')
                salary = salary_elem.text
            except NoSuchElementException:
                pass
            
            return JobListing(
                id=job_id,
                title=title_elem.text.strip(),
                company=company_elem.text.strip(),
                location=location_elem.text.strip(),
                salary=salary,
                description="",  # Would need separate request to get full description
                requirements="",
                url=job_url,
                source='Glassdoor',
                date_scraped=datetime.now().isoformat(),
                country='Morocco',
                remote=False,
                visa_sponsorship=False
            )
        
        except Exception as e:
            logger.warning(f"Error extracting Glassdoor job: {e}")
            return None
    
    def _handle_popups(self, driver: uc.Chrome):
        """Handle common popups and overlays"""
        popup_selectors = [
            '[data-testid="close-popup"]',
            '.popover-x-button-close',
            '.modal-close',
            '#onetrust-accept-btn-handler',
            '.cookie-consent-accept',
            '.dismiss-button'
        ]
        
        for selector in popup_selectors:
            try:
                element = driver.find_element(By.CSS_SELECTOR, selector)
                element.click()
                self.human_like_delay(0.5, 1)
                break
            except NoSuchElementException:
                continue
    
    def _scroll_page(self, driver: uc.Chrome, times: int = 3):
        """Scroll page to load more content"""
        for i in range(times):
            driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
            self.human_like_delay(1, 2)
    
    def run_comprehensive_search(self, max_jobs: int = 50) -> List[JobListing]:
        """Run comprehensive job search across all platforms"""
        logger.info("🚀 Starting comprehensive job search...")
        all_jobs = []
        
        # Job sources with their limits
        sources = [
            ('Indeed Morocco', self.scrape_indeed_morocco, max_jobs // 2),
            ('LinkedIn', self.scrape_linkedin_jobs, max_jobs // 3),
            ('Glassdoor', self.scrape_glassdoor_jobs, max_jobs // 5)
        ]
        
        for source_name, scraper_func, limit in sources:
            try:
                logger.info(f"\n📡 Scraping {source_name}...")
                jobs = scraper_func(limit)
                all_jobs.extend(jobs)
                logger.info(f"✅ {source_name}: {len(jobs)} jobs collected")
            except Exception as e:
                logger.error(f"❌ {source_name} failed: {e}")
                continue
            
            # Delay between sources
            self.human_like_delay(5, 10)
        
        # Remove duplicates based on URL
        unique_jobs = self._remove_duplicates(all_jobs)
        
        # Sort by relevance score
        unique_jobs.sort(key=lambda x: x.relevance_score, reverse=True)
        
        logger.info(f"🎉 Search complete: {len(unique_jobs)} unique jobs found")
        
        # Save summary statistics
        self._save_search_summary(unique_jobs)
        
        return unique_jobs
    
    def _remove_duplicates(self, jobs: List[JobListing]) -> List[JobListing]:
        """Remove duplicate jobs based on URL and similar titles"""
        seen_urls = set()
        unique_jobs = []
        
        for job in jobs:
            # Check URL duplicates
            if job.url in seen_urls:
                continue
            
            # Check for similar titles at same company (fuzzy matching)
            is_duplicate = False
            for existing_job in unique_jobs:
                if (job.company.lower() == existing_job.company.lower() and
                    self._are_titles_similar(job.title, existing_job.title)):
                    is_duplicate = True
                    break
            
            if not is_duplicate:
                seen_urls.add(job.url)
                unique_jobs.append(job)
            else:
                logger.debug(f"🔄 Duplicate detected: {job.title} at {job.company}")
        
        logger.info(f"🧹 Deduplication: {len(jobs)} → {len(unique_jobs)} jobs")
        return unique_jobs
    
    def _are_titles_similar(self, title1: str, title2: str, threshold: float = 0.8) -> bool:
        """Check if two job titles are similar enough to be considered duplicates"""
        title1_clean = re.sub(r'[^\w\s]', '', title1.lower()).strip()
        title2_clean = re.sub(r'[^\w\s]', '', title2.lower()).strip()
        
        # Simple word overlap check
        words1 = set(title1_clean.split())
        words2 = set(title2_clean.split())
        
        if len(words1) == 0 or len(words2) == 0:
            return False
        
        overlap = len(words1.intersection(words2))
        similarity = overlap / max(len(words1), len(words2))
        
        return similarity >= threshold
    
    def _save_search_summary(self, jobs: List[JobListing]):
        """Save search summary and statistics"""
        summary = {
            'total_jobs': len(jobs),
            'sources': {},
            'avg_score': 0,
            'top_companies': {},
            'location_distribution': {},
            'remote_jobs': 0,
            'visa_sponsorship_jobs': 0,
            'search_timestamp': datetime.now().isoformat()
        }
        
        if jobs:
            # Calculate statistics
            summary['avg_score'] = sum(job.relevance_score for job in jobs) / len(jobs)
            
            # Count by source
            for job in jobs:
                source = job.source
                summary['sources'][source] = summary['sources'].get(source, 0) + 1
            
            # Top companies
            for job in jobs:
                company = job.company
                summary['top_companies'][company] = summary['top_companies'].get(company, 0) + 1
            
            # Location distribution
            for job in jobs:
                location = job.location
                summary['location_distribution'][location] = summary['location_distribution'].get(location, 0) + 1
            
            # Special flags
            summary['remote_jobs'] = sum(1 for job in jobs if job.remote)
            summary['visa_sponsorship_jobs'] = sum(1 for job in jobs if job.visa_sponsorship)
        
        # Save to file
        summary_path = self.cache_dir / f"search_summary_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        with open(summary_path, 'w', encoding='utf-8') as f:
            json.dump(summary, f, indent=2, ensure_ascii=False)
        
        logger.info(f"📊 Search summary saved to {summary_path}")


# Legacy function for backwards compatibility
def run_multi_site_job_search(max_morocco=30, max_europe=30):
    """
    Legacy function for backwards compatibility with existing orchestrator
    """
    from core.config import load_config
    from core.database import DatabaseManager
    
    try:
        config = load_config()
        db_manager = DatabaseManager()
        
        agent = EnhancedJobFinderAgent(
            user_profile=config.user_profile,
            db_manager=db_manager,
            scraping_config=config.scraping
        )
        
        # Run search with legacy parameters
        max_jobs = max_morocco + max_europe
        jobs = agent.run_comprehensive_search(max_jobs)
        
        # Convert to dict format for backwards compatibility
        job_dicts = []
        for job in jobs:
            job_dict = {
                'id': job.id,
                'title': job.title,
                'company': job.company,
                'location': job.location,
                'salary': job.salary,
                'description': job.description,
                'requirements': job.requirements,
                'url': job.url,
                'source': job.source,
                'date_scraped': job.date_scraped,
                'country': job.country,
                'remote': job.remote,
                'visa_sponsorship': job.visa_sponsorship,
                'relevance_score': job.relevance_score,
                'match_explanation': job.match_explanation
            }
            job_dicts.append(job_dict)
        
        # Print summary for backwards compatibility
        print("\n" + "=" * 50)
        print("📊 JOB SEARCH RESULTS")
        print("=" * 50)
        print(f"✅ Total Jobs Found: {len(job_dicts)}")
        
        if job_dicts:
            avg_score = sum(job['relevance_score'] for job in job_dicts) / len(job_dicts)
            print(f"⭐ Average Relevance Score: {avg_score:.1f}")
            
            remote_count = sum(1 for job in job_dicts if job['remote'])
            if remote_count > 0:
                print(f"🏠 Remote Jobs: {remote_count}")
            
            visa_count = sum(1 for job in job_dicts if job['visa_sponsorship'])
            if visa_count > 0:
                print(f"🛂 Visa Sponsorship: {visa_count}")
            
            # Count by source
            sources = {}
            for job in job_dicts:
                source = job['source']
                sources[source] = sources.get(source, 0) + 1
            
            print("\n🔍 By Source:")
            for source, count in sources.items():
                print(f"  • {source}: {count} jobs")
        
        print(f"\n📁 Data saved to database")
        print("=" * 50)
        
        return job_dicts
        
    except Exception as e:
        logger.error(f"Legacy job search failed: {e}")
        print(f"❌ Job search failed: {e}")
        return []