"""
Database Manager for JobAutoPilot
Handles all database operations and data persistence
"""

import sqlite3
import json
import logging
from datetime import datetime, timedelta
from pathlib import Path
from typing import List, Dict, Optional, Tuple
from dataclasses import dataclass, asdict

logger = logging.getLogger(__name__)

@dataclass
class JobListing:
    """Job listing data model"""
    id: str
    title: str
    company: str
    location: str
    salary: str
    description: str
    requirements: str
    url: str
    source: str
    date_scraped: str
    country: str
    remote: bool
    visa_sponsorship: bool
    relevance_score: float = 0.0
    match_explanation: str = ""
    application_status: str = "pending"
    applied_date: Optional[str] = None

@dataclass
class ApplicationResult:
    """Application result data model"""
    id: Optional[int]
    job_id: str
    success: bool
    method: str
    message: str
    confirmation_id: Optional[str]
    timestamp: str
    resume_path: Optional[str] = None
    cover_letter_path: Optional[str] = None

class DatabaseManager:
    """Manages all database operations for JobAutoPilot"""
    
    def __init__(self, db_path: str = "data/jobautopilot.db"):
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(exist_ok=True)
        self.init_database()
    
    def init_database(self):
        """Initialize database with all required tables"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                # Jobs table
                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS jobs (
                        id TEXT PRIMARY KEY,
                        title TEXT NOT NULL,
                        company TEXT NOT NULL,
                        location TEXT,
                        salary TEXT,
                        description TEXT,
                        requirements TEXT,
                        url TEXT UNIQUE,
                        source TEXT,
                        date_scraped TEXT,
                        country TEXT,
                        remote BOOLEAN,
                        visa_sponsorship BOOLEAN,
                        relevance_score REAL DEFAULT 0.0,
                        match_explanation TEXT,
                        application_status TEXT DEFAULT 'pending',
                        applied_date TEXT,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    )
                ''')
                
                # Applications table
                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS applications (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        job_id TEXT NOT NULL,
                        success BOOLEAN NOT NULL,
                        method TEXT NOT NULL,
                        message TEXT,
                        confirmation_id TEXT,
                        timestamp TEXT NOT NULL,
                        resume_path TEXT,
                        cover_letter_path TEXT,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        FOREIGN KEY (job_id) REFERENCES jobs (id)
                    )
                ''')
                
                # User feedback table
                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS user_feedback (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        job_id TEXT NOT NULL,
                        feedback_type TEXT NOT NULL,
                        feedback_value TEXT,
                        notes TEXT,
                        timestamp TEXT NOT NULL,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        FOREIGN KEY (job_id) REFERENCES jobs (id)
                    )
                ''')
                
                # Company blacklist/whitelist
                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS company_preferences (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        company_name TEXT UNIQUE NOT NULL,
                        preference_type TEXT NOT NULL, -- 'blacklist' or 'whitelist'
                        reason TEXT,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    )
                ''')
                
                # Application analytics
                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS analytics (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        metric_name TEXT NOT NULL,
                        metric_value TEXT NOT NULL,
                        metadata TEXT, -- JSON
                        date TEXT NOT NULL,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    )
                ''')
                
                # Create indexes for better performance
                cursor.execute('CREATE INDEX IF NOT EXISTS idx_jobs_status ON jobs(application_status)')
                cursor.execute('CREATE INDEX IF NOT EXISTS idx_jobs_score ON jobs(relevance_score)')
                cursor.execute('CREATE INDEX IF NOT EXISTS idx_jobs_date ON jobs(date_scraped)')
                cursor.execute('CREATE INDEX IF NOT EXISTS idx_applications_job ON applications(job_id)')
                cursor.execute('CREATE INDEX IF NOT EXISTS idx_applications_timestamp ON applications(timestamp)')
                
                conn.commit()
                logger.info("✅ Database initialized successfully")
                
        except Exception as e:
            logger.error(f"❌ Database initialization failed: {e}")
            raise
    
    def save_job(self, job: JobListing) -> bool:
        """Save or update a job listing"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                # Check if job exists
                cursor.execute('SELECT id FROM jobs WHERE id = ?', (job.id,))
                exists = cursor.fetchone()
                
                if exists:
                    # Update existing job
                    cursor.execute('''
                        UPDATE jobs SET 
                        title=?, company=?, location=?, salary=?, description=?, 
                        requirements=?, url=?, source=?, date_scraped=?, country=?,
                        remote=?, visa_sponsorship=?, relevance_score=?, 
                        match_explanation=?, application_status=?, applied_date=?,
                        updated_at=CURRENT_TIMESTAMP
                        WHERE id=?
                    ''', (
                        job.title, job.company, job.location, job.salary, job.description,
                        job.requirements, job.url, job.source, job.date_scraped, job.country,
                        job.remote, job.visa_sponsorship, job.relevance_score,
                        job.match_explanation, job.application_status, job.applied_date,
                        job.id
                    ))
                    logger.debug(f"Updated job: {job.title} at {job.company}")
                else:
                    # Insert new job
                    cursor.execute('''
                        INSERT INTO jobs VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
                    ''', (
                        job.id, job.title, job.company, job.location, job.salary,
                        job.description, job.requirements, job.url, job.source,
                        job.date_scraped, job.country, job.remote, job.visa_sponsorship,
                        job.relevance_score, job.match_explanation, job.application_status,
                        job.applied_date
                    ))
                    logger.debug(f"Saved new job: {job.title} at {job.company}")
                
                conn.commit()
                return True
                
        except sqlite3.IntegrityError as e:
            logger.warning(f"Job already exists or constraint violation: {e}")
            return False
        except Exception as e:
            logger.error(f"Error saving job: {e}")
            return False
    
    def get_jobs(self, status: Optional[str] = None, limit: Optional[int] = None, 
                 min_score: Optional[float] = None) -> List[JobListing]:
        """Retrieve jobs with optional filtering"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                query = 'SELECT * FROM jobs WHERE 1=1'
                params = []
                
                if status:
                    query += ' AND application_status = ?'
                    params.append(status)
                
                if min_score is not None:
                    query += ' AND relevance_score >= ?'
                    params.append(min_score)
                
                query += ' ORDER BY relevance_score DESC, date_scraped DESC'
                
                if limit:
                    query += ' LIMIT ?'
                    params.append(limit)
                
                cursor.execute(query, params)
                rows = cursor.fetchall()
                
                return [JobListing(*row) for row in rows]
                
        except Exception as e:
            logger.error(f"Error retrieving jobs: {e}")
            return []
    
    def get_job_by_id(self, job_id: str) -> Optional[JobListing]:
        """Get a specific job by ID"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute('SELECT * FROM jobs WHERE id = ?', (job_id,))
                row = cursor.fetchone()
                
                if row:
                    return JobListing(*row)
                return None
                
        except Exception as e:
            logger.error(f"Error retrieving job {job_id}: {e}")
            return None
    
    def update_job_status(self, job_id: str, status: str, applied_date: Optional[str] = None) -> bool:
        """Update job application status"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                if applied_date:
                    cursor.execute('''
                        UPDATE jobs SET application_status=?, applied_date=?, updated_at=CURRENT_TIMESTAMP 
                        WHERE id=?
                    ''', (status, applied_date, job_id))
                else:
                    cursor.execute('''
                        UPDATE jobs SET application_status=?, updated_at=CURRENT_TIMESTAMP 
                        WHERE id=?
                    ''', (status, job_id))
                
                conn.commit()
                return cursor.rowcount > 0
                
        except Exception as e:
            logger.error(f"Error updating job status: {e}")
            return False
    
    def save_application_result(self, result: ApplicationResult) -> bool:
        """Save application attempt result"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    INSERT INTO applications 
                    (job_id, success, method, message, confirmation_id, timestamp, resume_path, cover_letter_path)
                    VALUES (?,?,?,?,?,?,?,?)
                ''', (
                    result.job_id, result.success, result.method, result.message,
                    result.confirmation_id, result.timestamp, result.resume_path,
                    result.cover_letter_path
                ))
                conn.commit()
                return True
                
        except Exception as e:
            logger.error(f"Error saving application result: {e}")
            return False
    
    def get_application_history(self, job_id: Optional[str] = None) -> List[ApplicationResult]:
        """Get application history"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                if job_id:
                    cursor.execute('SELECT * FROM applications WHERE job_id = ? ORDER BY timestamp DESC', (job_id,))
                else:
                    cursor.execute('SELECT * FROM applications ORDER BY timestamp DESC')
                
                rows = cursor.fetchall()
                return [ApplicationResult(*row) for row in rows]
                
        except Exception as e:
            logger.error(f"Error retrieving application history: {e}")
            return []
    
    def save_user_feedback(self, job_id: str, feedback_type: str, feedback_value: str, notes: str = "") -> bool:
        """Save user feedback on jobs/applications"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    INSERT INTO user_feedback (job_id, feedback_type, feedback_value, notes, timestamp)
                    VALUES (?,?,?,?,?)
                ''', (job_id, feedback_type, feedback_value, notes, datetime.now().isoformat()))
                conn.commit()
                return True
                
        except Exception as e:
            logger.error(f"Error saving user feedback: {e}")
            return False
    
    def add_company_preference(self, company_name: str, preference_type: str, reason: str = "") -> bool:
        """Add company to blacklist or whitelist"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    INSERT OR REPLACE INTO company_preferences (company_name, preference_type, reason)
                    VALUES (?,?,?)
                ''', (company_name, preference_type, reason))
                conn.commit()
                return True
                
        except Exception as e:
            logger.error(f"Error adding company preference: {e}")
            return False
    
    def get_company_preferences(self, preference_type: Optional[str] = None) -> List[Dict]:
        """Get company preferences"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                if preference_type:
                    cursor.execute('SELECT * FROM company_preferences WHERE preference_type = ?', (preference_type,))
                else:
                    cursor.execute('SELECT * FROM company_preferences')
                
                rows = cursor.fetchall()
                columns = [desc[0] for desc in cursor.description]
                return [dict(zip(columns, row)) for row in rows]
                
        except Exception as e:
            logger.error(f"Error retrieving company preferences: {e}")
            return []
    
    def save_analytics_metric(self, metric_name: str, metric_value: str, metadata: Dict = None) -> bool:
        """Save analytics metric"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    INSERT INTO analytics (metric_name, metric_value, metadata, date)
                    VALUES (?,?,?,?)
                ''', (metric_name, metric_value, json.dumps(metadata) if metadata else None, 
                     datetime.now().date().isoformat()))
                conn.commit()
                return True
                
        except Exception as e:
            logger.error(f"Error saving analytics: {e}")
            return False
    
    def get_statistics(self) -> Dict:
        """Get comprehensive statistics"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                stats = {}
                
                # Job statistics
                cursor.execute('SELECT COUNT(*) FROM jobs')
                stats['total_jobs'] = cursor.fetchone()[0]
                
                cursor.execute('SELECT application_status, COUNT(*) FROM jobs GROUP BY application_status')
                stats['jobs_by_status'] = dict(cursor.fetchall())
                
                cursor.execute('SELECT source, COUNT(*) FROM jobs GROUP BY source')
                stats['jobs_by_source'] = dict(cursor.fetchall())
                
                cursor.execute('SELECT AVG(relevance_score) FROM jobs WHERE relevance_score > 0')
                avg_score = cursor.fetchone()[0]
                stats['avg_relevance_score'] = round(avg_score, 2) if avg_score else 0
                
                # Application statistics
                cursor.execute('SELECT COUNT(*) FROM applications')
                stats['total_applications'] = cursor.fetchone()[0]
                
                cursor.execute('SELECT success, COUNT(*) FROM applications GROUP BY success')
                app_results = dict(cursor.fetchall())
                stats['successful_applications'] = app_results.get(1, 0)
                stats['failed_applications'] = app_results.get(0, 0)
                
                # Success rate
                if stats['total_applications'] > 0:
                    stats['success_rate'] = round((stats['successful_applications'] / stats['total_applications']) * 100, 2)
                else:
                    stats['success_rate'] = 0
                
                # Recent activity (last 7 days)
                week_ago = (datetime.now() - timedelta(days=7)).isoformat()
                cursor.execute('SELECT COUNT(*) FROM jobs WHERE date_scraped >= ?', (week_ago,))
                stats['jobs_last_week'] = cursor.fetchone()[0]
                
                cursor.execute('SELECT COUNT(*) FROM applications WHERE timestamp >= ?', (week_ago,))
                stats['applications_last_week'] = cursor.fetchone()[0]
                
                return stats
                
        except Exception as e:
            logger.error(f"Error generating statistics: {e}")
            return {}
    
    def cleanup_old_data(self, days_to_keep: int = 30) -> int:
        """Clean up old data beyond specified days"""
        try:
            cutoff_date = (datetime.now() - timedelta(days=days_to_keep)).isoformat()
            
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                # Delete old rejected/failed jobs
                cursor.execute('''
                    DELETE FROM jobs WHERE 
                    application_status IN ('rejected', 'failed', 'expired') 
                    AND date_scraped < ?
                ''', (cutoff_date,))
                
                deleted_jobs = cursor.rowcount
                
                # Delete orphaned applications
                cursor.execute('''
                    DELETE FROM applications WHERE 
                    job_id NOT IN (SELECT id FROM jobs)
                ''')
                
                deleted_apps = cursor.rowcount
                
                conn.commit()
                
                logger.info(f"🧹 Cleaned up {deleted_jobs} old jobs and {deleted_apps} orphaned applications")
                return deleted_jobs + deleted_apps
                
        except Exception as e:
            logger.error(f"Error during cleanup: {e}")
            return 0
    
    def export_data(self, output_path: str = "data/export.json") -> bool:
        """Export all data to JSON"""
        try:
            data = {
                'jobs': [asdict(job) for job in self.get_jobs()],
                'applications': [asdict(app) for app in self.get_application_history()],
                'statistics': self.get_statistics(),
                'export_date': datetime.now().isoformat()
            }
            
            with open(output_path, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
            
            logger.info(f"✅ Data exported to {output_path}")
            return True
            
        except Exception as e:
            logger.error(f"Error exporting data: {e}")
            return False