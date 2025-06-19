#!/usr/bin/env python3
"""
Command-line interface for the Comprehensive Document Analyzer
Called by Node.js backend to process uploaded files
"""

import sys
import json
import os
from pathlib import Path

# Add the current directory to Python path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from comprehensive_document_analyzer import ComprehensiveDocumentAnalyzer

def main():
    """Main CLI entry point"""
    if len(sys.argv) < 3:
        print(json.dumps({
            "error": "Insufficient arguments",
            "usage": "python cli_analyzer.py <command> <arguments>"
        }))
        sys.exit(1)
    
    command = sys.argv[1]
    
    try:
        # Initialize analyzer with environment variables
        analyzer = ComprehensiveDocumentAnalyzer(
            aws_access_key=os.getenv('AWS_ACCESS_KEY_ID'),
            aws_secret_key=os.getenv('AWS_SECRET_ACCESS_KEY'),
            aws_region=os.getenv('AWS_REGION', 'us-east-1'),
            google_credentials_path=os.getenv('GOOGLE_APPLICATION_CREDENTIALS')
        )
        
        if command == "analyze_single":
            file_path = sys.argv[2]
            result = analyzer.analyze_document(file_path)
            print(json.dumps(result, default=str))
            
        elif command == "analyze_multiple":
            file_paths_json = sys.argv[2]
            file_paths = json.loads(file_paths_json)
            result = analyzer.analyze_multiple_documents(file_paths)
            print(json.dumps(result, default=str))
            
        else:
            print(json.dumps({
                "error": f"Unknown command: {command}",
                "available_commands": ["analyze_single", "analyze_multiple"]
            }))
            sys.exit(1)
            
    except Exception as e:
        print(json.dumps({
            "error": str(e),
            "type": type(e).__name__,
            "traceback": str(e)
        }), file=sys.stderr)
        sys.exit(1)

if __name__ == "__main__":
    main() 