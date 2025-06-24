import undetected_chromedriver as uc
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException
import requests
from bs4 import BeautifulSoup
import pandas as pd
import json
import time
import random
from fake_useragent import UserAgent
from urllib.parse import urlencode, quote_plus
import os
from datetime import datetime, timedelta
import logging

# Setup directories
os.makedirs('data', exist_ok=True)
os.makedirs('logs', exist_ok=True)

# Configure logging
logging.basicConfig(
    level=logging.INFO, 
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('logs/job_finder.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

class JobFinderAgent:
    def __init__(self):
        self.ua = UserAgent()
        self.session = requests.Session()
        self.job_data = []
    
    def create_stealth_driver(self):
        """Create undetected Chrome driver with stealth options"""
        options = uc.ChromeOptions()
        
        # Stealth options
        options.add_argument('--no-sandbox')
        options.add_argument('--disable-dev-shm-usage')
        options.add_argument('--disable-blink-features=AutomationControlled')
        options.add_argument('--disable-extensions')
        options.add_argument('--disable-plugins-discovery')
        options.add_argument('--disable-web-security')
        options.add_argument('--allow-running-insecure-content')
        options.add_argument('--no-first-run')
        options.add_argument('--no-default-browser-check')
        options.add_argument('--disable-default-apps')
        options.add_argument('--disable-popup-blocking')
        options.add_argument('--disable-notifications')
        
        # Random user agent
        options.add_argument(f'--user-agent={self.ua.random}')
        
        # Random window size
        window_sizes = ['1920,1080', '1366,768', '1440,900', '1280,720']
        options.add_argument(f'--window-size={random.choice(window_sizes)}')
        
        try:
            driver = uc.Chrome(options=options)
            
            # Execute stealth scripts
            driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
            driver.execute_cdp_cmd('Network.setUserAgentOverride', {
                "userAgent": self.ua.random,
                "acceptLanguage": "en-US,en;q=0.9",
                "platform": "Win32"
            })
            
            return driver
        except Exception as e:
            logger.error(f"Failed to create driver: {e}")
            raise
    
    def random_delay(self, min_delay=2, max_delay=5):
        """Random delay to mimic human behavior"""
        delay = random.uniform(min_delay, max_delay)
        time.sleep(delay)
    
    def scrape_indeed_morocco(self, max_results=30):
        """Scrape Indeed Morocco for Full Stack Java Developer positions"""
        logger.info("🇲🇦 Scraping Indeed Morocco...")
        jobs = []
        
        driver = self.create_stealth_driver()
        try:
            queries = [
                "full stack java developer",
                "développeur full stack java",
                "java developer full stack",
                "senior java developer",
                "junior java developer morocco"
            ]
            
            for query in queries:
                if len(jobs) >= max_results:
                    break
                    
                url = f"https://ma.indeed.com/jobs?q={quote_plus(query)}&l=Morocco&sort=date&fromage=7"
                logger.info(f"Searching Morocco: {query}")
                
                driver.get(url)
                self.random_delay(3, 6)
                
                # Handle potential captcha or verification
                if "robot" in driver.page_source.lower() or "captcha" in driver.page_source.lower():
                    logger.warning("Captcha detected, waiting...")
                    time.sleep(15)
                
                # Extract job listings
                try:
                    job_cards = driver.find_elements(By.CSS_SELECTOR, '[data-jk]')
                    
                    for card in job_cards[:8]:  # Limit per query
                        try:
                            title_elem = card.find_element(By.CSS_SELECTOR, 'h2 a span')
                            company_elem = card.find_element(By.CSS_SELECTOR, '[data-testid="company-name"]')
                            location_elem = card.find_element(By.CSS_SELECTOR, '[data-testid="job-location"]')
                            link_elem = card.find_element(By.CSS_SELECTOR, 'h2 a')
                            
                            job_url = "https://ma.indeed.com" + link_elem.get_attribute('href')
                            
                            # Extract salary if available
                            salary = "Not specified"
                            try:
                                salary_elem = card.find_element(By.CSS_SELECTOR, '[data-testid="attribute_snippet_testid"]')
                                salary = salary_elem.text
                            except NoSuchElementException:
                                pass
                            
                            jobs.append({
                                'title': title_elem.text.strip(),
                                'company': company_elem.text.strip(),
                                'location': location_elem.text.strip(),
                                'salary': salary,
                                'url': job_url,
                                'source': 'Indeed Morocco',
                                'date_scraped': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                                'country': 'Morocco',
                                'remote': False,
                                'visa_sponsorship': False
                            })
                            
                        except Exception as e:
                            logger.warning(f"Error extracting job data: {e}")
                            continue
                            
                except Exception as e:
                    logger.warning(f"Error finding job cards: {e}")
                    continue
                
                self.random_delay(2, 4)
                
        except Exception as e:
            logger.error(f"Error scraping Indeed Morocco: {e}")
        finally:
            driver.quit()
        
        logger.info(f"Found {len(jobs)} jobs from Indeed Morocco")
        return jobs
    
    def scrape_indeed_europe(self, max_results=30):
        """Scrape Indeed Europe for remote/visa sponsorship positions"""
        logger.info("🇪🇺 Scraping Indeed Europe...")
        jobs = []
        
        european_sites = [
            ('indeed.com', 'Remote'),
            ('indeed.de', 'Germany'),
            ('indeed.fr', 'France'),
            ('indeed.co.uk', 'United Kingdom'),
            ('indeed.nl', 'Netherlands')
        ]
        
        driver = self.create_stealth_driver()
        try:
            for site, country in european_sites[:3]:  # Limit to 3 sites to avoid overload
                if len(jobs) >= max_results:
                    break
                
                queries = [
                    "full stack java developer remote",
                    "java developer visa sponsorship",
                    "senior java developer remote work"
                ]
                
                for query in queries[:2]:  # Limit queries per site
                    if len(jobs) >= max_results:
                        break
                    
                    url = f"https://{site}/jobs?q={quote_plus(query)}&sort=date&fromage=7"
                    logger.info(f"Searching {country}: {query}")
                    
                    try:
                        driver.get(url)
                        self.random_delay(3, 6)
                        
                        job_cards = driver.find_elements(By.CSS_SELECTOR, '[data-jk]')
                        
                        for card in job_cards[:5]:  # Limit per query per site
                            try:
                                title_elem = card.find_element(By.CSS_SELECTOR, 'h2 a span')
                                company_elem = card.find_element(By.CSS_SELECTOR, '[data-testid="company-name"]')
                                link_elem = card.find_element(By.CSS_SELECTOR, 'h2 a')
                                
                                job_url = f"https://{site}" + link_elem.get_attribute('href')
                                
                                # Check for remote/visa keywords
                                card_text = card.text.lower()
                                is_remote = any(keyword in card_text for keyword in ['remote', 'télétravail', 'home office', 'work from home'])
                                has_visa = any(keyword in card_text for keyword in ['visa', 'sponsorship', 'relocation'])
                                
                                if is_remote or has_visa or 'remote' in query.lower():
                                    jobs.append({
                                        'title': title_elem.text.strip(),
                                        'company': company_elem.text.strip(),
                                        'location': f"{country} ({'Remote' if is_remote else 'Visa Sponsorship'})",
                                        'salary': 'Not specified',
                                        'url': job_url,
                                        'source': f'Indeed {country}',
                                        'date_scraped': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                                        'country': country,
                                        'remote': is_remote,
                                        'visa_sponsorship': has_visa
                                    })
                                
                            except Exception as e:
                                logger.warning(f"Error extracting job data: {e}")
                                continue
                                
                    except Exception as e:
                        logger.warning(f"Error scraping {site}: {e}")
                        continue
                    
                    self.random_delay(2, 4)
                
        except Exception as e:
            logger.error(f"Error scraping Indeed Europe: {e}")
        finally:
            driver.quit()
        
        logger.info(f"Found {len(jobs)} jobs from Indeed Europe")
        return jobs
    
    def scrape_linkedin_jobs(self, max_results=20):
        """Scrape LinkedIn for Java developer positions"""
        logger.info("💼 Scraping LinkedIn...")
        jobs = []
        
        driver = self.create_stealth_driver()
        try:
            # Morocco search
            morocco_url = "https://www.linkedin.com/jobs/search/?keywords=full%20stack%20java%20developer&location=Morocco&f_TPR=r86400&f_JT=F"
            driver.get(morocco_url)
            self.random_delay(4, 7)
            
            # Scroll to load more jobs
            for _ in range(2):
                driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
                self.random_delay(2, 4)
            
            try:
                job_cards = driver.find_elements(By.CSS_SELECTOR, '.job-search-card')
                
                for card in job_cards[:max_results//2]:
                    try:
                        title = card.find_element(By.CSS_SELECTOR, '.base-search-card__title').text.strip()
                        company = card.find_element(By.CSS_SELECTOR, '.base-search-card__subtitle').text.strip()
                        location = card.find_element(By.CSS_SELECTOR, '.job-search-card__location').text.strip()
                        link = card.find_element(By.CSS_SELECTOR, '.base-card__full-link').get_attribute('href')
                        
                        jobs.append({
                            'title': title,
                            'company': company,
                            'location': location,
                            'salary': 'Not specified',
                            'url': link,
                            'source': 'LinkedIn',
                            'date_scraped': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                            'country': 'Morocco',
                            'remote': False,
                            'visa_sponsorship': False
                        })
                        
                    except Exception as e:
                        logger.warning(f"Error extracting LinkedIn job: {e}")
                        continue
                        
            except Exception as e:
                logger.warning(f"Error finding LinkedIn job cards: {e}")
            
        except Exception as e:
            logger.error(f"Error scraping LinkedIn: {e}")
        finally:
            driver.quit()
        
        logger.info(f"Found {len(jobs)} jobs from LinkedIn")
        return jobs
    
    def filter_and_enhance_jobs(self, jobs):
        """Filter jobs based on criteria and enhance with additional info"""
        logger.info("🔍 Filtering and enhancing job listings...")
        
        filtered_jobs = []
        java_keywords = ['java', 'spring', 'springboot', 'hibernate', 'maven', 'gradle']
        fullstack_keywords = ['full stack', 'fullstack', 'full-stack', 'frontend', 'backend', 'react', 'angular', 'vue']
        
        for job in jobs:
            title_lower = job['title'].lower()
            
            # Check if it's a Java full-stack position
            has_java = any(keyword in title_lower for keyword in java_keywords)
            has_fullstack = any(keyword in title_lower for keyword in fullstack_keywords)
            
            # More lenient filtering - include if has either java OR fullstack
            if has_java or has_fullstack or 'developer' in title_lower:
                # Enhance with relevance score
                relevance_score = 0
                if has_java: relevance_score += 5
                if has_fullstack: relevance_score += 5
                if 'senior' in title_lower: relevance_score += 2
                if 'junior' in title_lower: relevance_score += 1
                if job.get('remote', False): relevance_score += 3
                if job.get('visa_sponsorship', False): relevance_score += 3
                if 'developer' in title_lower: relevance_score += 2
                
                job['relevance_score'] = relevance_score
                filtered_jobs.append(job)
        
        # Sort by relevance score
        filtered_jobs.sort(key=lambda x: x.get('relevance_score', 0), reverse=True)
        
        logger.info(f"Filtered to {len(filtered_jobs)} relevant jobs")
        return filtered_jobs
    
    def save_jobs_data(self, jobs):
        """Save job data to multiple formats"""
        logger.info("💾 Saving job data...")
        
        try:
            # Save as JSON
            with open('data/job_listings.json', 'w', encoding='utf-8') as f:
                json.dump(jobs, f, indent=2, ensure_ascii=False)
            
            # Save as CSV
            df = pd.DataFrame(jobs)
            df.to_csv('data/job_listings.csv', index=False, encoding='utf-8')
            
            # Save as Excel
            df.to_excel('data/job_listings.xlsx', index=False)
            
            # Create summary report
            summary = {
                'total_jobs': len(jobs),
                'by_country': df['country'].value_counts().to_dict() if not df.empty else {},
                'by_source': df['source'].value_counts().to_dict() if not df.empty else {},
                'remote_jobs': len(df[df.get('remote', pd.Series([False]*len(df))) == True]) if not df.empty else 0,
                'visa_sponsorship': len(df[df.get('visa_sponsorship', pd.Series([False]*len(df))) == True]) if not df.empty else 0,
                'generated_at': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            }
            
            with open('data/job_summary.json', 'w', encoding='utf-8') as f:
                json.dump(summary, f, indent=2, ensure_ascii=False)
            
            logger.info(f"✅ Saved {len(jobs)} jobs to data/ directory")
            return summary
            
        except Exception as e:
            logger.error(f"Error saving job data: {e}")
            return {'total_jobs': len(jobs), 'by_country': {}, 'by_source': {}, 'remote_jobs': 0, 'visa_sponsorship': 0}
    
    def run_complete_search(self, morocco_jobs=30, europe_jobs=30, linkedin_jobs=20):
        """Run complete job search across all platforms"""
        logger.info("🚀 Starting comprehensive job search...")
        
        all_jobs = []
        
        # Scrape all platforms with error handling
        try:
            all_jobs.extend(self.scrape_indeed_morocco(morocco_jobs))
        except Exception as e:
            logger.error(f"Indeed Morocco failed: {e}")
        
        try:
            all_jobs.extend(self.scrape_indeed_europe(europe_jobs))
        except Exception as e:
            logger.error(f"Indeed Europe failed: {e}")
        
        try:
            all_jobs.extend(self.scrape_linkedin_jobs(linkedin_jobs))
        except Exception as e:
            logger.error(f"LinkedIn failed: {e}")
        
        # Remove duplicates based on URL
        unique_jobs = []
        seen_urls = set()
        for job in all_jobs:
            if job['url'] not in seen_urls:
                seen_urls.add(job['url'])
                unique_jobs.append(job)
        
        # Filter and enhance
        filtered_jobs = self.filter_and_enhance_jobs(unique_jobs)
        
        # Save data
        summary = self.save_jobs_data(filtered_jobs)
        
        logger.info(f"🎉 Job search completed! Found {summary['total_jobs']} relevant positions")
        return filtered_jobs, summary

def run_multi_site_job_search(max_morocco=30, max_europe=30):
    """
    Main function for orchestrator compatibility
    Returns list of job dictionaries compatible with your existing pipeline
    """
    logger.info("🚀 Starting multi-site job search...")
    
    try:
        agent = JobFinderAgent()
        
        # Run the complete search with custom limits
        jobs, summary = agent.run_complete_search(
            morocco_jobs=max_morocco,
            europe_jobs=max_europe,
            linkedin_jobs=20
        )
        
        # Print summary for orchestrator
        print("\n" + "=" * 50)
        print("📊 JOB SEARCH RESULTS")
        print("=" * 50)
        print(f"✅ Total Jobs Found: {summary['total_jobs']}")
        if summary.get('remote_jobs', 0) > 0:
            print(f"🏠 Remote Jobs: {summary['remote_jobs']}")
        if summary.get('visa_sponsorship', 0) > 0:
            print(f"🛂 Visa Sponsorship: {summary['visa_sponsorship']}")
        
        if summary.get('by_country'):
            print("\n📍 By Location:")
            for country, count in summary['by_country'].items():
                print(f"  • {country}: {count} jobs")
        
        if summary.get('by_source'):
            print("\n🔍 By Source:")
            for source, count in summary['by_source'].items():
                print(f"  • {source}: {count} jobs")
        
        print(f"\n📁 Data saved to data/ directory")
        print("=" * 50)
        
        return jobs
        
    except Exception as e:
        logger.error(f"Job search failed: {e}")
        print(f"❌ Job search failed: {e}")
        return []