#!/usr/bin/env python3
"""
Test script to simulate scan progress for neural brain testing
"""
import asyncio
import sys
from datetime import datetime
from uuid import UUID

from app.db.session import async_session_maker
from app.models.scan import Scan
from sqlalchemy import select


async def simulate_scan_progress(scan_id: str):
    """Simulate a scan progressing through different states"""
    
    scan_uuid = UUID(scan_id)
    
    async with async_session_maker() as db:
        # Get the scan
        query = select(Scan).where(Scan.id == scan_uuid)
        result = await db.execute(query)
        scan = result.scalar_one_or_none()
        
        if not scan:
            print(f"❌ Scan {scan_id} not found")
            return
        
        print(f"🧠 Starting neural brain simulation for scan: {scan.target}")
        
        # Stage 1: Set to running
        print("⏳ Stage 1: Starting scan...")
        scan.status = 'running'
        scan.started_at = datetime.utcnow()
        await db.commit()
        await asyncio.sleep(3)
        
        # Stage 2: Add some vulnerabilities
        print("🔍 Stage 2: Finding vulnerabilities...")
        scan.critical_count = 0
        scan.high_count = 1
        scan.medium_count = 2
        scan.low_count = 1
        scan.vulnerabilities_found = 4
        await db.commit()
        await asyncio.sleep(5)
        
        # Stage 3: Add more vulnerabilities
        print("🚨 Stage 3: More vulnerabilities detected...")
        scan.critical_count = 1
        scan.high_count = 2
        scan.medium_count = 3
        scan.low_count = 2
        scan.vulnerabilities_found = 8
        await db.commit()
        await asyncio.sleep(5)
        
        # Stage 4: Complete the scan
        print("✅ Stage 4: Completing scan...")
        scan.status = 'completed'
        scan.completed_at = datetime.utcnow()
        scan.duration_seconds = int((scan.completed_at - scan.started_at).total_seconds())
        scan.platform_detected = "Web Application"
        scan.confidence = 0.85
        
        # Generate mock report
        scan.report_json = f'''{{
            "target": "{scan.target}",
            "scan_mode": "{scan.scan_mode}",
            "scan_date": "{scan.completed_at.isoformat()}",
            "platform_detected": "Web Application",
            "confidence": 0.85,
            "vulnerabilities": [
                {{
                    "type": "SQL Injection",
                    "severity": "critical",
                    "description": "Potential SQL injection vulnerability in login form",
                    "recommendation": "Use parameterized queries and input validation"
                }},
                {{
                    "type": "Cross-Site Scripting (XSS)",
                    "severity": "high",
                    "description": "Potential XSS vulnerability detected in user input fields",
                    "recommendation": "Implement proper input validation and output encoding"
                }},
                {{
                    "type": "Cross-Site Scripting (XSS)",
                    "severity": "high",
                    "description": "Reflected XSS in search parameter",
                    "recommendation": "Sanitize user input and implement CSP headers"
                }},
                {{
                    "type": "Missing Security Headers",
                    "severity": "medium",
                    "description": "Security headers like X-Frame-Options and CSP are missing",
                    "recommendation": "Add security headers to prevent clickjacking and XSS"
                }},
                {{
                    "type": "Information Disclosure",
                    "severity": "medium",
                    "description": "Server version information exposed in headers",
                    "recommendation": "Hide server version information in HTTP headers"
                }},
                {{
                    "type": "Weak SSL Configuration",
                    "severity": "medium",
                    "description": "SSL configuration could be strengthened",
                    "recommendation": "Update SSL/TLS configuration to use stronger ciphers"
                }},
                {{
                    "type": "Directory Listing",
                    "severity": "low",
                    "description": "Directory listing enabled on some paths",
                    "recommendation": "Disable directory listing in web server configuration"
                }},
                {{
                    "type": "Verbose Error Messages",
                    "severity": "low",
                    "description": "Application returns verbose error messages",
                    "recommendation": "Implement generic error messages for production"
                }}
            ],
            "scan_duration": {scan.duration_seconds},
            "status": "completed"
        }}'''
        
        scan.report_text = f'''
SECURITY SCAN REPORT
====================

Target: {scan.target}
Platform: Web Application
Confidence: 85%
Scan Date: {scan.completed_at.isoformat()}

VULNERABILITY COUNTS
--------------------
Critical: 1
High: 2
Medium: 3
Low: 2
Total: 8

DETAILED FINDINGS
-----------------

1. SQL Injection (CRITICAL)
   Description: Potential SQL injection vulnerability in login form
   Recommendation: Use parameterized queries and input validation

2. Cross-Site Scripting (XSS) (HIGH)
   Description: Potential XSS vulnerability detected in user input fields
   Recommendation: Implement proper input validation and output encoding

3. Cross-Site Scripting (XSS) (HIGH)
   Description: Reflected XSS in search parameter
   Recommendation: Sanitize user input and implement CSP headers

4. Missing Security Headers (MEDIUM)
   Description: Security headers like X-Frame-Options and CSP are missing
   Recommendation: Add security headers to prevent clickjacking and XSS

5. Information Disclosure (MEDIUM)
   Description: Server version information exposed in headers
   Recommendation: Hide server version information in HTTP headers

6. Weak SSL Configuration (MEDIUM)
   Description: SSL configuration could be strengthened
   Recommendation: Update SSL/TLS configuration to use stronger ciphers

7. Directory Listing (LOW)
   Description: Directory listing enabled on some paths
   Recommendation: Disable directory listing in web server configuration

8. Verbose Error Messages (LOW)
   Description: Application returns verbose error messages
   Recommendation: Implement generic error messages for production

END OF REPORT
=============
        '''
        
        await db.commit()
        
        print("🎉 Neural brain simulation complete!")
        print(f"   Target: {scan.target}")
        print(f"   Vulnerabilities: {scan.vulnerabilities_found}")
        print(f"   Duration: {scan.duration_seconds} seconds")
        print(f"   Status: {scan.status}")


async def main():
    if len(sys.argv) != 2:
        print("Usage: python test_scan_simulation.py <scan_id>")
        sys.exit(1)
    
    scan_id = sys.argv[1]
    await simulate_scan_progress(scan_id)


if __name__ == "__main__":
    asyncio.run(main())