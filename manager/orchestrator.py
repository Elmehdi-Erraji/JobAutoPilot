import os
import sys
import time
from datetime import datetime

# Add the project root to the path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from job_finder.job_aggregator import run_multi_site_job_search
from modifier.cv_cover_editor import generate_documents
from applier.apply_bot import apply_to_jobs

def run_pipeline():
    """
    Complete job automation pipeline orchestrator
    """
    print("🧠 Manager: Starting job automation pipeline...")
    print(f"📅 Started at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    try:
        # Phase 1: Job Discovery
        print("\n" + "=" * 50)
        print("🔍 PHASE 1: JOB DISCOVERY")
        print("=" * 50)
        
        jobs = run_multi_site_job_search(max_morocco=30, max_europe=30)
        
        if not jobs:
            print("❌ No jobs found. Pipeline terminated.")
            return
        
        print(f"✅ Found {len(jobs)} relevant job opportunities")
        
        # Phase 2: Document Generation
        print("\n" + "=" * 50)
        print("📄 PHASE 2: DOCUMENT GENERATION")
        print("=" * 50)
        
        successful_generations = 0
        for i, job in enumerate(jobs, 1):
            print(f"📝 Processing job {i}/{len(jobs)}: {job.get('title', 'Unknown Title')}")
            try:
                generate_documents(job)
                successful_generations += 1
                print(f"✅ Documents generated for {job.get('company', 'Unknown Company')}")
            except Exception as e:
                print(f"❌ Failed to generate documents for job {i}: {e}")
                continue
        
        print(f"✅ Successfully generated documents for {successful_generations}/{len(jobs)} jobs")
        
        # Phase 3: Job Application
        print("\n" + "=" * 50)
        print("🚀 PHASE 3: JOB APPLICATION")
        print("=" * 50)
        
        apply_to_jobs(jobs)
        
        # Pipeline Summary
        print("\n" + "=" * 50)
        print("📊 PIPELINE SUMMARY")
        print("=" * 50)
        print(f"🔍 Jobs Found: {len(jobs)}")
        print(f"📄 Documents Generated: {successful_generations}")
        print(f"📅 Completed at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        
    except KeyboardInterrupt:
        print("\n⚠️  Pipeline interrupted by user")
    except Exception as e:
        print(f"❌ Pipeline failed with error: {e}")
        raise
