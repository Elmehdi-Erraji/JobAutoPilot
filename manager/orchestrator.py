"""
JobAutoPilot Orchestrator
Coordinates all agents and manages the complete pipeline
"""

import os
import sys
import time
import logging
from datetime import datetime, timedelta
from typing import List, Dict, Optional
from pathlib import Path

# Add project root to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from job_finder.job_aggregator import EnhancedJobFinderAgent
from modifier.cv_cover_editor import AIDocumentModifier
from applier.apply_bot import SmartApplicationAgent
from core.database import DatabaseManager, JobListing
from core.config import JobAutoPilotConfig, validate_config

logger = logging.getLogger(__name__)

class JobAutoPilotOrchestrator:
    """
    Master orchestrator that coordinates all JobAutoPilot agents
    """
    
    def __init__(self, config: JobAutoPilotConfig, db_manager: DatabaseManager, dry_run: bool = False):
        self.config = config
        self.db_manager = db_manager
        self.dry_run = dry_run
        
        # Validate configuration
        config_issues = validate_config(config)
        if config_issues:
            logger.warning("⚠️ Configuration issues found:")
            for issue in config_issues:
                logger.warning(f"  - {issue}")
            if not dry_run:
                logger.error("❌ Cannot proceed with invalid configuration")
                raise ValueError("Invalid configuration")
        
        # Initialize agents
        self.job_finder = EnhancedJobFinderAgent(
            user_profile=config.user_profile,
            db_manager=db_manager,
            scraping_config=config.scraping
        )
        
        self.document_modifier = AIDocumentModifier(
            user_profile=config.user_profile,
            ai_config=config.ai
        )
        
        self.application_agent = SmartApplicationAgent(
            user_profile=config.user_profile,
            email_config=config.email,
            db_manager=db_manager,
            dry_run=dry_run
        )
        
        # Pipeline statistics
        self.stats = {
            'start_time': None,
            'end_time': None,
            'jobs_found': 0,
            'jobs_processed': 0,
            'documents_generated': 0,
            'applications_attempted': 0,
            'applications_successful': 0,
            'errors': []
        }
    
    def run_full_pipeline(self, max_jobs: int = 50) -> Dict:
        """
        Execute the complete job automation pipeline
        """
        logger.info("🚀 Starting JobAutoPilot full pipeline...")
        self.stats['start_time'] = datetime.now()
        
        try:
            # Phase 1: Job Discovery
            logger.info("\n" + "=" * 60)
            logger.info("🔍 PHASE 1: INTELLIGENT JOB DISCOVERY")
            logger.info("=" * 60)
            
            jobs = self._run_job_discovery(max_jobs)
            self.stats['jobs_found'] = len(jobs)
            
            if not jobs:
                logger.warning("❌ No suitable jobs found. Pipeline terminated.")
                return self._generate_pipeline_report()
            
            logger.info(f"✅ Found {len(jobs)} relevant job opportunities")
            
            # Phase 2: Smart Filtering and Prioritization
            logger.info("\n" + "=" * 60)
            logger.info("🧠 PHASE 2: SMART JOB FILTERING & PRIORITIZATION")
            logger.info("=" * 60)
            
            prioritized_jobs = self._prioritize_jobs(jobs)
            logger.info(f"📊 Prioritized {len(prioritized_jobs)} jobs for application")
            
            # Phase 3: Document Generation
            logger.info("\n" + "=" * 60)
            logger.info("📄 PHASE 3: AI-POWERED DOCUMENT GENERATION")
            logger.info("=" * 60)
            
            processed_jobs = self._generate_documents(prioritized_jobs)
            self.stats['documents_generated'] = len(processed_jobs)
            
            # Phase 4: Smart Application
            logger.info("\n" + "=" * 60)
            logger.info("🚀 PHASE 4: INTELLIGENT JOB APPLICATION")
            logger.info("=" * 60)
            
            application_results = self._apply_to_jobs(processed_jobs)
            
            # Phase 5: Pipeline Summary and Analytics
            logger.info("\n" + "=" * 60)
            logger.info("📊 PHASE 5: PIPELINE ANALYTICS & REPORTING")
            logger.info("=" * 60)
            
            return self._generate_pipeline_report()
            
        except KeyboardInterrupt:
            logger.warning("\n⚠️ Pipeline interrupted by user")
            return self._generate_pipeline_report()
        except Exception as e:
            logger.error(f"❌ Pipeline failed: {e}")
            self.stats['errors'].append(str(e))
            return self._generate_pipeline_report()
        finally:
            self.stats['end_time'] = datetime.now()
    
    def run_job_search_only(self, max_jobs: int = 50) -> List[JobListing]:
        """Run only the job discovery phase"""
        logger.info("🔍 Running job search only...")
        return self._run_job_discovery(max_jobs)
    
    def run_application_only(self) -> Dict:
        """Run application phase for pending jobs"""
        logger.info("🚀 Running application phase for pending jobs...")
        
        # Get jobs ready for application
        pending_jobs = self.db_manager.get_jobs(
            status='ready_to_apply',
            min_score=self.config.application.minimum_match_score
        )
        
        if not pending_jobs:
            logger.warning("No jobs ready for application")
            return {'applications_attempted': 0, 'applications_successful': 0}
        
        return self._apply_to_jobs(pending_jobs)
    
    def show_status_report(self):
        """Show current system status and statistics"""
        logger.info("📊 JobAutoPilot Status Report")
        logger.info("=" * 50)
        
        stats = self.db_manager.get_statistics()
        
        logger.info(f"📈 Total Jobs in Database: {stats.get('total_jobs', 0)}")
        logger.info(f"⭐ Average Relevance Score: {stats.get('avg_relevance_score', 0)}")
        logger.info(f"📨 Total Applications: {stats.get('total_applications', 0)}")
        logger.info(f"✅ Success Rate: {stats.get('success_rate', 0)}%")
        logger.info(f"📅 Jobs Found This Week: {stats.get('jobs_last_week', 0)}")
        logger.info(f"🚀 Applications This Week: {stats.get('applications_last_week', 0)}")
        
        # Jobs by status
        if stats.get('jobs_by_status'):
            logger.info("\n📋 Jobs by Status:")
            for status, count in stats['jobs_by_status'].items():
                logger.info(f"  • {status}: {count}")
        
        # Jobs by source
        if stats.get('jobs_by_source'):
            logger.info("\n🔍 Jobs by Source:")
            for source, count in stats['jobs_by_source'].items():
                logger.info(f"  • {source}: {count}")
    
    def _run_job_discovery(self, max_jobs: int) -> List[JobListing]:
        """Execute job discovery phase"""
        try:
            # Run comprehensive job search
            jobs = self.job_finder.run_comprehensive_search(max_jobs)
            
            # Apply company preferences filtering
            filtered_jobs = self._apply_company_filters(jobs)
            
            # Remove duplicates and update database
            unique_jobs = self._deduplicate_jobs(filtered_jobs)
            
            logger.info(f"🎯 Discovery complete: {len(unique_jobs)} unique jobs found")
            return unique_jobs
            
        except Exception as e:
            logger.error(f"Job discovery failed: {e}")
            self.stats['errors'].append(f"Job discovery: {e}")
            return []
    
    def _apply_company_filters(self, jobs: List[JobListing]) -> List[JobListing]:
        """Apply company blacklist/whitelist filters"""
        blacklisted = self.db_manager.get_company_preferences('blacklist')
        whitelisted = self.db_manager.get_company_preferences('whitelist')
        
        blacklist_companies = {pref['company_name'].lower() for pref in blacklisted}
        whitelist_companies = {pref['company_name'].lower() for pref in whitelisted}
        
        filtered_jobs = []
        
        for job in jobs:
            company_lower = job.company.lower()
            
            # Skip blacklisted companies
            if company_lower in blacklist_companies:
                logger.debug(f"⚫ Skipping blacklisted company: {job.company}")
                continue
            
            # If whitelist exists, only include whitelisted companies
            if whitelist_companies and company_lower not in whitelist_companies:
                logger.debug(f"⚪ Skipping non-whitelisted company: {job.company}")
                continue
            
            filtered_jobs.append(job)
        
        logger.info(f"🔍 Company filtering: {len(jobs)} → {len(filtered_jobs)} jobs")
        return filtered_jobs
    
    def _deduplicate_jobs(self, jobs: List[JobListing]) -> List[JobListing]:
        """Remove duplicate jobs based on URL and save to database"""
        seen_urls = set()
        unique_jobs = []
        
        for job in jobs:
            if job.url not in seen_urls:
                seen_urls.add(job.url)
                unique_jobs.append(job)
                self.db_manager.save_job(job)
            else:
                logger.debug(f"🔄 Duplicate job skipped: {job.title} at {job.company}")
        
        return unique_jobs
    
    def _prioritize_jobs(self, jobs: List[JobListing]) -> List[JobListing]:
        """Prioritize jobs based on relevance score and other factors"""
        # Filter by minimum score threshold
        min_score = self.config.application.minimum_match_score
        qualified_jobs = [job for job in jobs if job.relevance_score >= min_score]
        
        logger.info(f"📊 Score filtering: {len(jobs)} → {len(qualified_jobs)} jobs above {min_score} threshold")
        
        # Sort by priority factors
        def job_priority(job):
            priority_score = job.relevance_score
            
            # Boost for preferred companies
            if job.company.lower() in [c.lower() for c in self.config.application.preferred_companies]:
                priority_score += 10
            
            # Boost for remote jobs if preferred
            if job.remote and self.config.user_profile.remote_preference:
                priority_score += 5
            
            # Boost for visa sponsorship if needed
            if job.visa_sponsorship and self.config.user_profile.visa_required:
                priority_score += 8
            
            # Slight preference for recent postings
            try:
                job_date = datetime.fromisoformat(job.date_scraped)
                days_old = (datetime.now() - job_date).days
                if days_old == 0:  # Posted today
                    priority_score += 3
                elif days_old <= 2:  # Posted within 2 days
                    priority_score += 1
            except:
                pass
            
            return priority_score
        
        # Sort by priority score
        prioritized = sorted(qualified_jobs, key=job_priority, reverse=True)
        
        # Limit to max applications per day if configured
        max_daily = self.config.application.max_applications_per_day
        if max_daily > 0:
            prioritized = prioritized[:max_daily]
        
        logger.info(f"🎯 Prioritization complete: {len(prioritized)} jobs selected for processing")
        return prioritized
    
    def _generate_documents(self, jobs: List[JobListing]) -> List[JobListing]:
        """Generate tailored documents for each job"""
        processed_jobs = []
        
        for i, job in enumerate(jobs, 1):
            logger.info(f"📝 Processing job {i}/{len(jobs)}: {job.title} at {job.company}")
            
            try:
                # Generate tailored resume and cover letter
                resume_path, cover_letter_path = self.document_modifier.generate_documents_for_job(job)
                
                if resume_path and cover_letter_path:
                    # Update job status
                    self.db_manager.update_job_status(job.id, 'ready_to_apply')
                    
                    # Add document paths to job for application phase
                    job.resume_path = resume_path
                    job.cover_letter_path = cover_letter_path
                    
                    processed_jobs.append(job)
                    self.stats['jobs_processed'] += 1
                    
                    logger.info(f"✅ Documents generated for {job.company}")
                else:
                    logger.warning(f"❌ Failed to generate documents for {job.company}")
                    self.db_manager.update_job_status(job.id, 'document_generation_failed')
                    self.stats['errors'].append(f"Document generation failed: {job.title}")
                
            except Exception as e:
                logger.error(f"❌ Error processing {job.company}: {e}")
                self.db_manager.update_job_status(job.id, 'document_generation_failed')
                self.stats['errors'].append(f"Document generation error: {e}")
                continue
            
            # Add delay between document generations to avoid overwhelming AI API
            if not self.dry_run and i < len(jobs):
                time.sleep(2)
        
        logger.info(f"📄 Document generation complete: {len(processed_jobs)}/{len(jobs)} successful")
        return processed_jobs
    
    def _apply_to_jobs(self, jobs: List[JobListing]) -> Dict:
        """Apply to jobs with intelligent timing and error handling"""
        if not jobs:
            logger.warning("No jobs to apply to")
            return {'applications_attempted': 0, 'applications_successful': 0}
        
        application_results = {
            'applications_attempted': 0,
            'applications_successful': 0,
            'failed_applications': []
        }
        
        for i, job in enumerate(jobs, 1):
            logger.info(f"🚀 Applying {i}/{len(jobs)}: {job.title} at {job.company}")
            
            try:
                # Apply to job
                result = self.application_agent.apply_to_job(job)
                
                application_results['applications_attempted'] += 1
                self.stats['applications_attempted'] += 1
                
                if result.success:
                    application_results['applications_successful'] += 1
                    self.stats['applications_successful'] += 1
                    
                    # Update job status
                    self.db_manager.update_job_status(
                        job.id, 
                        'applied', 
                        datetime.now().isoformat()
                    )
                    
                    logger.info(f"✅ Successfully applied to {job.company}")
                    
                    # Save successful application
                    self.db_manager.save_application_result(result)
                    
                else:
                    logger.warning(f"❌ Application failed for {job.company}: {result.message}")
                    application_results['failed_applications'].append({
                        'job': job.title,
                        'company': job.company,
                        'error': result.message
                    })
                    
                    # Update job status
                    self.db_manager.update_job_status(job.id, 'application_failed')
                    
                    # Save failed application
                    self.db_manager.save_application_result(result)
                
            except Exception as e:
                logger.error(f"❌ Critical error applying to {job.company}: {e}")
                application_results['failed_applications'].append({
                    'job': job.title,
                    'company': job.company,
                    'error': str(e)
                })
                self.stats['errors'].append(f"Application error: {e}")
                continue
            
            # Intelligent delay between applications
            if not self.dry_run and i < len(jobs):
                delay = self.config.application.application_delay_hours * 3600
                if delay > 0:
                    logger.info(f"⏳ Waiting {self.config.application.application_delay_hours} hours before next application...")
                    time.sleep(min(delay, 300))  # Cap at 5 minutes for demo purposes
                else:
                    time.sleep(random.uniform(30, 120))  # Random delay 30s-2min
        
        logger.info(f"🎯 Application phase complete: {application_results['applications_successful']}/{application_results['applications_attempted']} successful")
        return application_results
    
    def _generate_pipeline_report(self) -> Dict:
        """Generate comprehensive pipeline execution report"""
        if self.stats['end_time'] is None:
            self.stats['end_time'] = datetime.now()
        
        duration = self.stats['end_time'] - self.stats['start_time']
        
        # Calculate success rates
        doc_success_rate = 0
        if self.stats['jobs_found'] > 0:
            doc_success_rate = (self.stats['documents_generated'] / self.stats['jobs_found']) * 100
        
        app_success_rate = 0
        if self.stats['applications_attempted'] > 0:
            app_success_rate = (self.stats['applications_successful'] / self.stats['applications_attempted']) * 100
        
        report = {
            'execution_summary': {
                'start_time': self.stats['start_time'].isoformat(),
                'end_time': self.stats['end_time'].isoformat(),
                'total_duration': str(duration),
                'dry_run': self.dry_run
            },
            'job_discovery': {
                'jobs_found': self.stats['jobs_found'],
                'jobs_processed': self.stats['jobs_processed']
            },
            'document_generation': {
                'documents_generated': self.stats['documents_generated'],
                'success_rate': round(doc_success_rate, 2)
            },
            'applications': {
                'applications_attempted': self.stats['applications_attempted'],
                'applications_successful': self.stats['applications_successful'],
                'success_rate': round(app_success_rate, 2)
            },
            'errors': self.stats['errors']
        }
        
        # Print summary report
        logger.info("\n" + "=" * 60)
        logger.info("📊 JOBAUTOPILOT EXECUTION REPORT")
        logger.info("=" * 60)
        logger.info(f"⏱️  Total Duration: {duration}")
        logger.info(f"🔍 Jobs Found: {self.stats['jobs_found']}")
        logger.info(f"📄 Documents Generated: {self.stats['documents_generated']} ({doc_success_rate:.1f}%)")
        logger.info(f"🚀 Applications Attempted: {self.stats['applications_attempted']}")
        logger.info(f"✅ Applications Successful: {self.stats['applications_successful']} ({app_success_rate:.1f}%)")
        
        if self.stats['errors']:
            logger.info(f"❌ Errors Encountered: {len(self.stats['errors'])}")
            for error in self.stats['errors'][:5]:  # Show first 5 errors
                logger.info(f"   • {error}")
        
        # Save analytics
        self.db_manager.save_analytics_metric('pipeline_execution', 'completed', report)
        
        logger.info("=" * 60)
        return report


def run_pipeline():
    """
    Legacy function for backwards compatibility
    """
    from core.config import load_config
    
    try:
        config = load_config()
        db_manager = DatabaseManager()
        
        orchestrator = JobAutoPilotOrchestrator(config, db_manager)
        return orchestrator.run_full_pipeline()
        
    except Exception as e:
        logger.error(f"Pipeline execution failed: {e}")
        raise