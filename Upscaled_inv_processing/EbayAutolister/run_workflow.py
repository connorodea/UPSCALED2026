#!/usr/bin/env python3
"""
Simple script to run the eBay listing workflow with your batch file.

Usage:
    python run_workflow.py                    # Uses B1.csv by default
    python run_workflow.py your_file.csv      # Uses specified CSV file
"""

import sys
import os

# Add the current directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from integrated_workflow import main

if __name__ == "__main__":
    print("""
    ╔════════════════════════════════════════════════════════════════╗
    ║                                                                ║
    ║         AI-POWERED EBAY LISTING WORKFLOW                       ║
    ║                                                                ║
    ║  This workflow will:                                           ║
    ║  1. Enrich your products using AI agents                       ║
    ║  2. Create eBay inventory items                                ║
    ║  3. Optionally publish listings to eBay                        ║
    ║                                                                ║
    ║  Pricing: All items priced at 50% of MSRP                      ║
    ║                                                                ║
    ╚════════════════════════════════════════════════════════════════╝
    """)

    main()
