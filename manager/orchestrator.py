import schedule
import time
from job_finder.indeed_scraper import run_job_search
from modifier.cv_cover_editor import generate_documents
from applier.apply_bot import apply_to_jobs

def run_pipeline():
    print("🧠 Manager: Starting job automation pipeline...")

    # 1. Find jobs
    jobs = run_job_search()
    if not jobs:
        print("No jobs found. Skipping the rest of the pipeline.")
        return

    # 2. Tailor documents
    for job in jobs:
        generate_documents(job)

    # 3. Apply to jobs
    apply_to_jobs(jobs)

    print("✅ Pipeline completed.")

# Schedule to run every day at 10 AM (example)
schedule.every().day.at("10:00").do(run_pipeline)

def start_manager():
    print("👔 Manager is active and scheduling jobs...")
    while True:
        schedule.run_pending()
        time.sleep(60)
