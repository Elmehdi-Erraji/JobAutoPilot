#!/usr/bin/env python3
"""
JobAutoPilot - Main Entry Point
Complete AI-powered job application automation system
"""

import os
import sys
import argparse
from datetime import datetime
from pathlib import Path

# Add project root to path
sys.path.append(str(Path(__file__).parent))

from manager.orchestrator import JobAutoPilotOrchestrator
from core.config import load_config, setup_logging
from core.database import DatabaseManager

def main():
    """Main entry point for JobAutoPilot"""
    parser = argparse.ArgumentParser(description='JobAutoPilot - AI Job Application System')
    parser.add_argument('--config', '-c', default='config.json', help='Configuration file path')
    parser.add_argument('--mode', '-m', choices=['search', 'apply', 'full', 'status'], 
                       default='full', help='Operation mode')
    parser.add_argument('--max-jobs', '-j', type=int, default=50, help='Maximum jobs to process')
    parser.add_argument('--dry-run', '-d', action='store_true', help='Run without applying to jobs')
    parser.add_argument('--verbose', '-v', action='store_true', help='Verbose output')
    
    args = parser.parse_args()
    
    # Setup logging
    log_level = 'DEBUG' if args.verbose else 'INFO'
    setup_logging(log_level)
    
    print("🚀 JobAutoPilot - AI-Powered Job Application System")
    print("=" * 60)
    print(f"🕐 Started at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"⚙️  Mode: {args.mode.upper()}")
    print(f"📊 Max Jobs: {args.max_jobs}")
    print(f"🧪 Dry Run: {'Yes' if args.dry_run else 'No'}")
    print("=" * 60)
    
    try:
        # Load configuration
        config = load_config(args.config)
        
        # Initialize database
        db_manager = DatabaseManager()
        
        # Initialize orchestrator
        orchestrator = JobAutoPilotOrchestrator(
            config=config,
            db_manager=db_manager,
            dry_run=args.dry_run
        )
        
        # Execute based on mode
        if args.mode == 'search':
            orchestrator.run_job_search_only(max_jobs=args.max_jobs)
        elif args.mode == 'apply':
            orchestrator.run_application_only()
        elif args.mode == 'status':
            orchestrator.show_status_report()
        else:  # full pipeline
            orchestrator.run_full_pipeline(max_jobs=args.max_jobs)
        
        print("\n" + "=" * 60)
        print("🎉 JobAutoPilot completed successfully!")
        print("=" * 60)
        
    except KeyboardInterrupt:
        print("\n⚠️  JobAutoPilot interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ JobAutoPilot failed: {e}")
        if args.verbose:
            import traceback
            traceback.print_exc()
        sys.exit(1)

if __name__ == "__main__":
    main()