"""
Smart Application Agent
Handles automated job applications with intelligent form filling and email sending
"""

import os
import re
import time
import random
import logging
import smtplib
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Tuple
from email.mime.text import MimeText
from email.mime.multipart import MimeMultipart
from email.mime.base import MimeBase
from email import encoders
from urllib.parse import urlparse, urljoin

import undetected_chromedriver as uc
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait, Select
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.common.action_chains import ActionChains
from selenium.common.exceptions import TimeoutException, NoSuchElementException, ElementClickInterceptedException
from fake_useragent import UserAgent

from core.config import UserProfile, EmailConfig
from core.database import DatabaseManager, JobListing, ApplicationResult

logger = logging.getLogger(__name__)

class FormFieldDetector:
    """Intelligent form field detection and classification"""
    
    @staticmethod
    def detect_field_type(element) -> str:
        """Detect the type of form field based on attributes"""
        # Get element attributes
        name = element.get_attribute('name') or ''
        id_attr = element.get_attribute('id') or ''
        placeholder = element.get_attribute('placeholder') or ''
        label_text = FormFieldDetector._get_label_text(element)
        
        combined_text = f"{name} {id_attr} {placeholder} {label_text}".lower()
        
        # Field type patterns
        field_patterns = {
            'first_name': r'\b(first.?name|fname|given.?name)\b',
            'last_name': r'\b(last.?name|lname|surname|family.?name)\b',
            'full_name': r'\b(full.?name|name|applicant.?name)\b',
            'email': r'\b(email|e.?mail)\b',
            'phone': r'\b(phone|mobile|telephone|tel)\b',
            'address': r'\b(address|street|location)\b',
            'city': r'\b(city|town)\b',
            'state': r'\b(state|province|region)\b',
            'zip': r'\b(zip|postal|post.?code)\b',
            'country': r'\b(country|nation)\b',
            'cover_letter': r'\b(cover.?letter|motivation|why.?interested)\b',
            'resume': r'\b(resume|cv|curriculum)\b',
            'experience': r'\b(experience|years|work.?experience)\b',
            'salary': r'\b(salary|compensation|pay|wage)\b',
            'availability': r'\b(availability|start.?date|notice)\b',
            'linkedin': r'\b(linkedin|profile)\b',
            'portfolio': r'\b(portfolio|website|github)\b',
            'work_authorization': r'\b(authorization|visa|permit|eligible)\b',
            'education': r'\b(education|degree|university|school)\b'
        }
        
        for field_type, pattern in field_patterns.items():
            if re.search(pattern, combined_text):
                return field_type
        
        return 'unknown'
    
    @staticmethod
    def _get_label_text(element) -> str:
        """Get associated label text for form element"""
        try:
            # Try to find label by 'for' attribute
            element_id = element.get_attribute('id')
            if element_id:
                driver = element._parent
                label = driver.find_element(By.CSS_SELECTOR, f'label[for="{element_id}"]')
                return label.text
        except:
            pass
        
        try:
            # Try to find label as parent or sibling
            parent = element.find_element(By.XPATH, '..')
            label = parent.find_element(By.TAG_NAME, 'label')
            return label.text
        except:
            pass
        
        return ''

class SmartApplicationAgent:
    """Intelligent job application agent with multiple strategies"""
    
    def __init__(self, user_profile: UserProfile, email_config: EmailConfig, 
                 db_manager: DatabaseManager, dry_run: bool = False):
        self.user_profile = user_profile
        self.email_config = email_config
        self.db_manager = db_manager
        self.dry_run = dry_run
        self.ua = UserAgent()
        
        # Application strategies
        self.strategies = {
            'direct_apply': self._direct_application,
            'email_application': self._email_application,
            'external_redirect': self._external_redirect_application
        }
    
    def apply_to_job(self, job: JobListing) -> ApplicationResult:
        """Apply to a job using the most appropriate strategy"""
        logger.info(f"🚀 Applying to: {job.title} at {job.company}")
        
        if self.dry_run:
            return ApplicationResult(
                id=None,
                job_id=job.id,
                success=True,
                method='dry_run',
                message='Dry run - no actual application sent',
                confirmation_id='DRY_RUN_' + job.id[:8],
                timestamp=datetime.now().isoformat()
            )
        
        # Determine application strategy
        strategy = self._determine_application_strategy(job)
        logger.info(f"📋 Using strategy: {strategy}")
        
        try:
            result = self.strategies[strategy](job)
            
            # Log application attempt
            self.db_manager.save_application_result(result)
            
            if result.success:
                logger.info(f"✅ Successfully applied to {job.company}")
            else:
                logger.warning(f"❌ Application failed for {job.company}: {result.message}")
            
            return result
            
        except Exception as e:
            logger.error(f"❌ Application error for {job.company}: {e}")
            return ApplicationResult(
                id=None,
                job_id=job.id,
                success=False,
                method=strategy,
                message=f"Application error: {str(e)}",
                confirmation_id=None,
                timestamp=datetime.now().isoformat()
            )
    
    def _determine_application_strategy(self, job: JobListing) -> str:
        """Determine the best application strategy for a job"""
        url_domain = urlparse(job.url).netloc.lower()
        
        # Check for direct application indicators
        if any(domain in url_domain for domain in ['indeed.com', 'linkedin.com', 'glassdoor.com']):
            return 'direct_apply'
        
        # Check for email indicators in description
        if re.search(r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b', job.description):
            return 'email_application'
        
        # Default to external redirect
        return 'external_redirect'
    
    def _direct_application(self, job: JobListing) -> ApplicationResult:
        """Handle direct application through job boards"""
        driver = self._create_application_driver()
        
        try:
            driver.get(job.url)
            self._random_delay(3, 6)
            
            # Handle different job boards
            if 'indeed.com' in job.url:
                return self._handle_indeed_application(driver, job)
            elif 'linkedin.com' in job.url:
                return self._handle_linkedin_application(driver, job)
            elif 'glassdoor.com' in job.url:
                return self._handle_glassdoor_application(driver, job)
            else:
                return self._handle_generic_application(driver, job)
                
        except Exception as e:
            logger.error(f"Direct application failed: {e}")
            return ApplicationResult(
                id=None,
                job_id=job.id,
                success=False,
                method='direct_apply',
                message=f"Direct application failed: {str(e)}",
                confirmation_id=None,
                timestamp=datetime.now().isoformat()
            )
        finally:
            try:
                driver.quit()
            except:
                pass
    
    def _handle_indeed_application(self, driver: uc.Chrome, job: JobListing) -> ApplicationResult:
        """Handle Indeed-specific application process"""
        try:
            # Look for apply button
            apply_selectors = [
                '[data-testid="apply-button"]',
                '.ia-IndeedApplyButton',
                'button[aria-label*="Apply"]',
                'a[aria-label*="Apply"]',
                '.jobsearch-SerpJobCard-footer button'
            ]
            
            apply_button = None
            for selector in apply_selectors:
                try:
                    apply_button = driver.find_element(By.CSS_SELECTOR, selector)
                    break
                except NoSuchElementException:
                    continue
            
            if not apply_button:
                return ApplicationResult(
                    id=None,
                    job_id=job.id,
                    success=False,
                    method='direct_apply',
                    message='Apply button not found on Indeed',
                    confirmation_id=None,
                    timestamp=datetime.now().isoformat()
                )
            
            # Check if it's an external application
            if 'external' in apply_button.get_attribute('class').lower():
                return self._handle_external_redirect(driver, apply_button, job)
            
            # Click apply button
            driver.execute_script("arguments[0].click();", apply_button)
            self._random_delay(2, 4)
            
            # Fill Indeed application form
            return self._fill_indeed_form(driver, job)
            
        except Exception as e:
            return ApplicationResult(
                id=None,
                job_id=job.id,
                success=False,
                method='direct_apply',
                message=f'Indeed application error: {str(e)}',
                confirmation_id=None,
                timestamp=datetime.now().isoformat()
            )
    
    def _fill_indeed_form(self, driver: uc.Chrome, job: JobListing) -> ApplicationResult:
        """Fill Indeed application form"""
        try:
            # Wait for form to load
            WebDriverWait(driver, 10).until(
                EC.presence_of_element_located((By.TAG_NAME, 'form'))
            )
            
            # Find and fill form fields
            form_fields = driver.find_elements(By.CSS_SELECTOR, 'input, textarea, select')
            
            for field in form_fields:
                field_type = FormFieldDetector.detect_field_type(field)
                value = self._get_field_value(field_type)
                
                if value and field.is_enabled():
                    try:
                        if field.tag_name == 'select':
                            self._select_dropdown_value(field, value)
                        else:
                            field.clear()
                            field.send_keys(value)
                        
                        self._random_delay(0.5, 1.5)
                    except Exception as e:
                        logger.warning(f"Failed to fill field {field_type}: {e}")
                        continue
            
            # Handle file uploads
            self._handle_file_uploads(driver, job)
            
            # Submit form
            submit_button = driver.find_element(By.CSS_SELECTOR, 'button[type="submit"], input[type="submit"]')
            driver.execute_script("arguments[0].click();", submit_button)
            
            # Wait for confirmation
            self._random_delay(3, 5)
            
            # Check for success confirmation
            confirmation_text = driver.page_source.lower()
            if any(phrase in confirmation_text for phrase in ['application submitted', 'thank you', 'successfully applied']):
                return ApplicationResult(
                    id=None,
                    job_id=job.id,
                    success=True,
                    method='direct_apply',
                    message='Application submitted via Indeed',
                    confirmation_id=f'INDEED_{job.id[:8]}',
                    timestamp=datetime.now().isoformat()
                )
            else:
                return ApplicationResult(
                    id=None,
                    job_id=job.id,
                    success=False,
                    method='direct_apply',
                    message='Application submission unclear',
                    confirmation_id=None,
                    timestamp=datetime.now().isoformat()
                )
                
        except Exception as e:
            return ApplicationResult(
                id=None,
                job_id=job.id,
                success=False,
                method='direct_apply',
                message=f'Form filling error: {str(e)}',
                confirmation_id=None,
                timestamp=datetime.now().isoformat()
            )
    
    def _handle_linkedin_application(self, driver: uc.Chrome, job: JobListing) -> ApplicationResult:
        """Handle LinkedIn application (requires login)"""
        return ApplicationResult(
            id=None,
            job_id=job.id,
            success=False,
            method='direct_apply',
            message='LinkedIn applications require manual login',
            confirmation_id=None,
            timestamp=datetime.now().isoformat()
        )
    
    def _handle_glassdoor_application(self, driver: uc.Chrome, job: JobListing) -> ApplicationResult:
        """Handle Glassdoor application"""
        try:
            # Find apply button
            apply_button = driver.find_element(By.CSS_SELECTOR, '[data-test="apply-button"], .applyButton')
            driver.execute_script("arguments[0].click();", apply_button)
            
            self._random_delay(3, 5)
            
            # Most Glassdoor applications redirect to company sites
            return self._handle_generic_application(driver, job)
            
        except Exception as e:
            return ApplicationResult(
                id=None,
                job_id=job.id,
                success=False,
                method='direct_apply',
                message=f'Glassdoor application error: {str(e)}',
                confirmation_id=None,
                timestamp=datetime.now().isoformat()
            )
    
    def _handle_generic_application(self, driver: uc.Chrome, job: JobListing) -> ApplicationResult:
        """Handle generic company website applications"""
        try:
            # Look for application forms
            forms = driver.find_elements(By.TAG_NAME, 'form')
            
            if not forms:
                # Look for apply buttons that might load forms
                apply_buttons = driver.find_elements(By.CSS_SELECTOR, 
                    'button[class*="apply"], a[class*="apply"], input[value*="apply"]')
                
                if apply_buttons:
                    apply_buttons[0].click()
                    self._random_delay(3, 5)
                    forms = driver.find_elements(By.TAG_NAME, 'form')
            
            if forms:
                return self._fill_generic_form(driver, forms[0], job)
            else:
                return ApplicationResult(
                    id=None,
                    job_id=job.id,
                    success=False,
                    method='direct_apply',
                    message='No application form found',
                    confirmation_id=None,
                    timestamp=datetime.now().isoformat()
                )
                
        except Exception as e:
            return ApplicationResult(
                id=None,
                job_id=job.id,
                success=False,
                method='direct_apply',
                message=f'Generic application error: {str(e)}',
                confirmation_id=None,
                timestamp=datetime.now().isoformat()
            )
    
    def _fill_generic_form(self, driver: uc.Chrome, form, job: JobListing) -> ApplicationResult:
        """Fill a generic application form"""
        try:
            # Find all form fields
            fields = form.find_elements(By.CSS_SELECTOR, 'input, textarea, select')
            
            filled_fields = 0
            for field in fields:
                if not field.is_displayed() or not field.is_enabled():
                    continue
                
                field_type = FormFieldDetector.detect_field_type(field)
                value = self._get_field_value(field_type)
                
                if value:
                    try:
                        if field.tag_name == 'select':
                            self._select_dropdown_value(field, value)
                        elif field.get_attribute('type') == 'file':
                            continue  # Handle separately
                        else:
                            field.clear()
                            field.send_keys(value)
                        
                        filled_fields += 1
                        self._random_delay(0.3, 1)
                        
                    except Exception as e:
                        logger.warning(f"Failed to fill field: {e}")
                        continue
            
            # Handle file uploads
            self._handle_file_uploads(driver, job)
            
            # Submit form if we filled enough fields
            if filled_fields >= 3:
                submit_buttons = form.find_elements(By.CSS_SELECTOR, 
                    'button[type="submit"], input[type="submit"], button[class*="submit"]')
                
                if submit_buttons:
                    driver.execute_script("arguments[0].click();", submit_buttons[0])
                    self._random_delay(3, 5)
                    
                    return ApplicationResult(
                        id=None,
                        job_id=job.id,
                        success=True,
                        method='direct_apply',
                        message=f'Application submitted via company website',
                        confirmation_id=f'COMPANY_{job.id[:8]}',
                        timestamp=datetime.now().isoformat()
                    )
            
            return ApplicationResult(
                id=None,
                job_id=job.id,
                success=False,
                method='direct_apply',
                message='Could not complete form - insufficient fields filled',
                confirmation_id=None,
                timestamp=datetime.now().isoformat()
            )
            
        except Exception as e:
            return ApplicationResult(
                id=None,
                job_id=job.id,
                success=False,
                method='direct_apply',
                message=f'Form submission error: {str(e)}',
                confirmation_id=None,
                timestamp=datetime.now().isoformat()
            )
    
    def _email_application(self, job: JobListing) -> ApplicationResult:
        """Send application via email"""
        try:
            # Extract email from job description
            email_pattern = r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'
            emails = re.findall(email_pattern, job.description + ' ' + job.requirements)
            
            if not emails:
                return ApplicationResult(
                    id=None,
                    job_id=job.id,
                    success=False,
                    method='email_application',
                    message='No email address found in job posting',
                    confirmation_id=None,
                    timestamp=datetime.now().isoformat()
                )
            
            # Use first email found
            recipient_email = emails[0]
            
            # Prepare email content
            subject = f"Application for {job.title} Position"
            
            # Get cover letter content
            cover_letter_path = getattr(job, 'cover_letter_path', None)
            if cover_letter_path and Path(cover_letter_path).exists():
                with open(cover_letter_path, 'r', encoding='utf-8') as f:
                    body = f.read()
            else:
                body = self._generate_email_body(job)
            
            # Get resume path
            resume_path = getattr(job, 'resume_path', None)
            if not resume_path or not Path(resume_path).exists():
                resume_path = self.user_profile.base_resume_path
            
            # Send email
            success = self._send_email(recipient_email, subject, body, resume_path)
            
            if success:
                return ApplicationResult(
                    id=None,
                    job_id=job.id,
                    success=True,
                    method='email_application',
                    message=f'Application sent to {recipient_email}',
                    confirmation_id=f'EMAIL_{job.id[:8]}',
                    timestamp=datetime.now().isoformat()
                )
            else:
                return ApplicationResult(
                    id=None,
                    job_id=job.id,
                    success=False,
                    method='email_application',
                    message='Failed to send email',
                    confirmation_id=None,
                    timestamp=datetime.now().isoformat()
                )
                
        except Exception as e:
            return ApplicationResult(
                id=None,
                job_id=job.id,
                success=False,
                method='email_application',
                message=f'Email application error: {str(e)}',
                confirmation_id=None,
                timestamp=datetime.now().isoformat()
            )
    
    def _external_redirect_application(self, job: JobListing) -> ApplicationResult:
        """Handle external redirect applications"""
        driver = self._create_application_driver()
        
        try:
            driver.get(job.url)
            self._random_delay(3, 6)
            
            # Look for external apply buttons or links
            external_selectors = [
                'a[href*="apply"]',
                'button[class*="apply"]',
                'a[class*="apply"]',
                '[data-testid*="apply"]'
            ]
            
            for selector in external_selectors:
                try:
                    elements = driver.find_elements(By.CSS_SELECTOR, selector)
                    for element in elements:
                        if 'apply' in element.text.lower():
                            element.click()
                            self._random_delay(3, 5)
                            return self._handle_generic_application(driver, job)
                except:
                    continue
            
            return ApplicationResult(
                id=None,
                job_id=job.id,
                success=False,
                method='external_redirect',
                message='No external apply link found',
                confirmation_id=None,
                timestamp=datetime.now().isoformat()
            )
            
        except Exception as e:
            return ApplicationResult(
                id=None,
                job_id=job.id,
                success=False,
                method='external_redirect',
                message=f'External redirect error: {str(e)}',
                confirmation_id=None,
                timestamp=datetime.now().isoformat()
            )
        finally:
            try:
                driver.quit()
            except:
                pass
    
    def _create_application_driver(self) -> uc.Chrome:
        """Create a stealth driver for applications"""
        options = uc.ChromeOptions()
        
        # Basic stealth options
        options.add_argument('--no-sandbox')
        options.add_argument('--disable-dev-shm-usage')
        options.add_argument('--disable-blink-features=AutomationControlled')
        options.add_argument(f'--user-agent={self.ua.random}')
        
        # Window size
        options.add_argument('--window-size=1366,768')
        
        driver = uc.Chrome(options=options)
        
        # Execute stealth scripts
        driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
        
        return driver
    
    def _get_field_value(self, field_type: str) -> Optional[str]:
        """Get appropriate value for form field type"""
        field_values = {
            'first_name': self.user_profile.name.split()[0] if self.user_profile.name else '',
            'last_name': self.user_profile.name.split()[-1] if self.user_profile.name else '',
            'full_name': self.user_profile.name,
            'email': self.user_profile.email,
            'phone': self.user_profile.phone,
            'address': self.user_profile.location,
            'city': self.user_profile.location.split(',')[0] if ',' in self.user_profile.location else self.user_profile.location,
            'country': 'Morocco',
            'experience': str(self.user_profile.experience_years),
            'linkedin': f"https://linkedin.com/in/{self.user_profile.name.lower().replace(' ', '-')}",
            'work_authorization': 'Yes' if not self.user_profile.visa_required else 'Requires Visa'
        }
        
        return field_values.get(field_type)
    
    def _select_dropdown_value(self, select_element, target_value: str):
        """Select value from dropdown"""
        try:
            select = Select(select_element)
            
            # Try exact match first
            for option in select.options:
                if option.text.lower() == target_value.lower():
                    select.select_by_visible_text(option.text)
                    return
            
            # Try partial match
            for option in select.options:
                if target_value.lower() in option.text.lower():
                    select.select_by_visible_text(option.text)
                    return
                    
        except Exception as e:
            logger.warning(f"Failed to select dropdown value: {e}")
    
    def _handle_file_uploads(self, driver: uc.Chrome, job: JobListing):
        """Handle file upload fields"""
        file_inputs = driver.find_elements(By.CSS_SELECTOR, 'input[type="file"]')
        
        for file_input in file_inputs:
            field_type = FormFieldDetector.detect_field_type(file_input)
            
            file_path = None
            if 'resume' in field_type or 'cv' in field_type:
                file_path = getattr(job, 'resume_path', self.user_profile.base_resume_path)
            elif 'cover' in field_type:
                file_path = getattr(job, 'cover_letter_path', self.user_profile.cover_letter_template_path)
            
            if file_path and Path(file_path).exists():
                try:
                    file_input.send_keys(str(Path(file_path).absolute()))
                    self._random_delay(1, 2)
                except Exception as e:
                    logger.warning(f"Failed to upload file: {e}")
    
    def _send_email(self, to_email: str, subject: str, body: str, attachment_path: str) -> bool:
        """Send email with attachment"""
        try:
            msg = MimeMultipart()
            msg['From'] = self.email_config.email
            msg['To'] = to_email
            msg['Subject'] = subject
            
            # Add body
            msg.attach(MimeText(body, 'plain'))
            
            # Add attachment if provided
            if attachment_path and Path(attachment_path).exists():
                with open(attachment_path, 'rb') as attachment:
                    part = MimeBase('application', 'octet-stream')
                    part.set_payload(attachment.read())
                
                encoders.encode_base64(part)
                part.add_header(
                    'Content-Disposition',
                    f'attachment; filename= {Path(attachment_path).name}'
                )
                msg.attach(part)
            
            # Send email
            server = smtplib.SMTP(self.email_config.smtp_server, self.email_config.smtp_port)
            if self.email_config.use_tls:
                server.starttls()
            
            server.login(self.email_config.email, self.email_config.password)
            server.send_message(msg)
            server.quit()
            
            logger.info(f"✅ Email sent to {to_email}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to send email: {e}")
            return False
    
    def _generate_email_body(self, job: JobListing) -> str:
        """Generate email body for application"""
        return f"""
Dear Hiring Manager,

I am writing to express my interest in the {job.title} position at {job.company}.

With {self.user_profile.experience_years} years of experience in software development and expertise in {', '.join(self.user_profile.skills[:3])}, I believe I would be a valuable addition to your team.

I have attached my resume for your review. I would welcome the opportunity to discuss how my skills and experience can contribute to {job.company}'s success.

Thank you for your time and consideration. I look forward to hearing from you.

Best regards,
{self.user_profile.name}
{self.user_profile.email}
{self.user_profile.phone}
"""
    
    def _random_delay(self, min_seconds: float = 1, max_seconds: float = 3):
        """Add random delay to mimic human behavior"""
        delay = random.uniform(min_seconds, max_seconds)
        time.sleep(delay)


# Legacy function for backwards compatibility
def apply_to_jobs(jobs):
    """Legacy function for backwards compatibility"""
    from core.config import load_config
    from core.database import DatabaseManager
    
    try:
        config = load_config()
        db_manager = DatabaseManager()
        
        agent = SmartApplicationAgent(
            user_profile=config.user_profile,
            email_config=config.email,
            db_manager=db_manager,
            dry_run=False
        )
        
        successful_applications = 0
        
        for job in jobs:
            # Convert dict to JobListing if needed
            if isinstance(job, dict):
                from core.database import JobListing
                job_listing = JobListing(
                    id=job.get('id', ''),
                    title=job.get('title', ''),
                    company=job.get('company', ''),
                    location=job.get('location', ''),
                    salary=job.get('salary', ''),
                    description=job.get('description', ''),
                    requirements=job.get('requirements', ''),
                    url=job.get('url', ''),
                    source=job.get('source', ''),
                    date_scraped=job.get('date_scraped', ''),
                    country=job.get('country', ''),
                    remote=job.get('remote', False),
                    visa_sponsorship=job.get('visa_sponsorship', False)
                )
            else:
                job_listing = job
            
            try:
                result = agent.apply_to_job(job_listing)
                if result.success:
                    successful_applications += 1
                    print(f"✅ [Applier] Applied to: {job_listing.title} at {job_listing.company}")
                else:
                    print(f"❌ [Applier] Failed to apply to: {job_listing.title} - {result.message}")
            except Exception as e:
                print(f"❌ [Applier] Error applying to {job_listing.title}: {e}")
                continue
        
        print(f"📊 [Applier] Summary: {successful_applications}/{len(jobs)} applications successful")
        
    except Exception as e:
        print(f"❌ [Applier] Critical error: {e}")
        logger.error(f"Legacy application process failed: {e}")