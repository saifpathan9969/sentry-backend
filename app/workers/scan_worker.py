"""
Celery worker for processing security scans
"""
import subprocess
import json
import asyncio
from datetime import datetime
from uuid import UUID
from typing import Dict, Any

from celery import Task
from celery.utils.log import get_task_logger
from sqlalchemy.ext.asyncio import AsyncSession

from app.workers.celery_app import celery_app
from app.db.session import async_session_maker
from app.models.scan import Scan
from app.services.queue_service import queue_service
from sqlalchemy import select

logger = get_task_logger(__name__)


class ScanTask(Task):
    """Custom task class with error handling"""
    
    autoretry_for = (Exception,)
    retry_kwargs = {"max_retries": 3}
    retry_backoff = True
    retry_backoff_max = 600  # 10 minutes
    retry_jitter = True


@celery_app.task(base=ScanTask, bind=True, name="app.workers.scan_worker.process_scan")
def process_scan(self, scan_id: str, user_id: str, target_url: str, scan_mode: str) -> Dict[str, Any]:
    """
    Process a security scan using the CLI tool
    
    Args:
        self: Task instance
        scan_id: Scan ID
        user_id: User ID
        target_url: Target URL to scan
        scan_mode: Scan mode (common, fast, full)
        
    Returns:
        Dict with scan results
    """
    logger.info(f"Starting scan {scan_id} for target {target_url}")
    
    # Run async function in event loop
    loop = asyncio.get_event_loop()
    result = loop.run_until_complete(
        _process_scan_async(scan_id, user_id, target_url, scan_mode)
    )
    
    return result


async def _process_scan_async(
    scan_id: str,
    user_id: str,
    target_url: str,
    scan_mode: str,
) -> Dict[str, Any]:
    """
    Async implementation of scan processing
    
    Args:
        scan_id: Scan ID
        user_id: User ID
        target_url: Target URL to scan
        scan_mode: Scan mode
        
    Returns:
        Dict with scan results
    """
    scan_uuid = UUID(scan_id)
    start_time = datetime.utcnow()
    
    try:
        # Update scan status to RUNNING - use string for PostgreSQL enum
        async with async_session_maker() as db:
            await _update_scan_status(
                db, scan_uuid, 'running', started_at=start_time
            )
        
        # Update job status in Redis
        await queue_service.set_job_status(scan_uuid, "processing")
        
        logger.info(f"Executing CLI tool for scan {scan_id}")
        
        # Execute the CLI tool
        result = await _execute_cli_tool(target_url, scan_mode)
        
        # Parse results
        vulnerabilities = result.get("vulnerabilities", [])
        platform_detected = result.get("platform_detected", "Unknown")
        confidence = result.get("confidence", 0.0)
        
        # Calculate vulnerability counts
        critical_count = sum(1 for v in vulnerabilities if v.get("severity") == "critical")
        high_count = sum(1 for v in vulnerabilities if v.get("severity") == "high")
        medium_count = sum(1 for v in vulnerabilities if v.get("severity") == "medium")
        low_count = sum(1 for v in vulnerabilities if v.get("severity") == "low")
        
        # Generate reports
        report_json = json.dumps(result, indent=2)
        report_text = _generate_text_report(result)
        
        # Calculate duration
        end_time = datetime.utcnow()
        duration_seconds = int((end_time - start_time).total_seconds())
        
        # Update scan with results
        async with async_session_maker() as db:
            query = select(Scan).where(Scan.id == scan_uuid)
            result_db = await db.execute(query)
            scan = result_db.scalar_one_or_none()
            
            if scan:
                scan.status = 'completed'
                scan.completed_at = end_time
                scan.duration_seconds = duration_seconds
                scan.vulnerabilities_found = len(vulnerabilities)
                scan.critical_count = critical_count
                scan.high_count = high_count
                scan.medium_count = medium_count
                scan.low_count = low_count
                scan.platform_detected = platform_detected
                scan.confidence = confidence
                scan.report_json = report_json
                scan.report_text = report_text
                
                await db.commit()
        
        # Update job status in Redis
        await queue_service.set_job_status(scan_uuid, "completed")
        
        logger.info(f"Scan {scan_id} completed successfully. Found {len(vulnerabilities)} vulnerabilities.")
        
        return {
            "scan_id": scan_id,
            "status": "completed",
            "vulnerabilities_found": len(vulnerabilities),
            "duration_seconds": duration_seconds,
        }
        
    except Exception as e:
        logger.error(f"Error processing scan {scan_id}: {str(e)}", exc_info=True)
        
        # Update scan status to FAILED - use string for PostgreSQL enum
        async with async_session_maker() as db:
            await _update_scan_status(
                db,
                scan_uuid,
                'failed',
                completed_at=datetime.utcnow(),
                error_message=str(e),
            )
        
        # Update job status in Redis
        await queue_service.set_job_status(scan_uuid, "failed")
        
        # Re-raise for Celery retry logic
        raise


async def _update_scan_status(
    db: AsyncSession,
    scan_id: UUID,
    status: str,
    started_at: datetime = None,
    completed_at: datetime = None,
    error_message: str = None,
):
    """
    Update scan status in database
    
    Args:
        db: Database session
        scan_id: Scan ID
        status: New status (string: 'queued', 'running', 'completed', 'failed')
        started_at: Start time (optional)
        completed_at: Completion time (optional)
        error_message: Error message (optional)
    """
    query = select(Scan).where(Scan.id == scan_id)
    result = await db.execute(query)
    scan = result.scalar_one_or_none()
    
    if scan:
        scan.status = status
        if started_at:
            scan.started_at = started_at
        if completed_at:
            scan.completed_at = completed_at
        if error_message:
            scan.error_message = error_message
        
        await db.commit()


async def _execute_cli_tool(target_url: str, scan_mode: str) -> Dict[str, Any]:
    """
    Execute the AI Pentest Brain CLI tool
    
    Args:
        target_url: Target URL to scan
        scan_mode: Scan mode
        
    Returns:
        Dict with scan results
    """
    # Build command
    cmd = [
        "python",
        "ai_pentest_brain_complete.py",
        target_url,
        "--scan-mode", scan_mode,
        "--report-format", "json",
        "--quiet",
    ]
    
    logger.info(f"Executing command: {' '.join(cmd)}")
    
    # Execute command
    process = await asyncio.create_subprocess_exec(
        *cmd,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
        cwd="../",  # Run from parent directory where CLI tool is located
    )
    
    stdout, stderr = await process.communicate()
    
    if process.returncode != 0:
        error_msg = stderr.decode() if stderr else "Unknown error"
        logger.error(f"CLI tool failed: {error_msg}")
        raise RuntimeError(f"CLI tool execution failed: {error_msg}")
    
    # Parse JSON output
    try:
        result = json.loads(stdout.decode())
        return result
    except json.JSONDecodeError as e:
        logger.error(f"Failed to parse CLI tool output: {e}")
        raise RuntimeError(f"Failed to parse scan results: {e}")


def _generate_text_report(scan_result: Dict[str, Any]) -> str:
    """
    Generate a text report from scan results
    
    Args:
        scan_result: Scan results dict
        
    Returns:
        Text report string
    """
    lines = []
    lines.append("=" * 80)
    lines.append("SECURITY SCAN REPORT")
    lines.append("=" * 80)
    lines.append("")
    
    # Summary
    lines.append("SUMMARY")
    lines.append("-" * 80)
    lines.append(f"Target: {scan_result.get('target', 'Unknown')}")
    lines.append(f"Platform: {scan_result.get('platform_detected', 'Unknown')}")
    lines.append(f"Confidence: {scan_result.get('confidence', 0.0):.2f}")
    lines.append(f"Scan Date: {scan_result.get('scan_date', 'Unknown')}")
    lines.append("")
    
    # Vulnerability counts
    vulnerabilities = scan_result.get("vulnerabilities", [])
    critical = sum(1 for v in vulnerabilities if v.get("severity") == "critical")
    high = sum(1 for v in vulnerabilities if v.get("severity") == "high")
    medium = sum(1 for v in vulnerabilities if v.get("severity") == "medium")
    low = sum(1 for v in vulnerabilities if v.get("severity") == "low")
    
    lines.append("VULNERABILITY COUNTS")
    lines.append("-" * 80)
    lines.append(f"Critical: {critical}")
    lines.append(f"High: {high}")
    lines.append(f"Medium: {medium}")
    lines.append(f"Low: {low}")
    lines.append(f"Total: {len(vulnerabilities)}")
    lines.append("")
    
    # Detailed findings
    if vulnerabilities:
        lines.append("DETAILED FINDINGS")
        lines.append("-" * 80)
        for i, vuln in enumerate(vulnerabilities, 1):
            lines.append(f"\n{i}. {vuln.get('type', 'Unknown')}")
            lines.append(f"   Severity: {vuln.get('severity', 'Unknown').upper()}")
            lines.append(f"   Description: {vuln.get('description', 'No description')}")
            if vuln.get('recommendation'):
                lines.append(f"   Recommendation: {vuln['recommendation']}")
        lines.append("")
    
    lines.append("=" * 80)
    lines.append("END OF REPORT")
    lines.append("=" * 80)
    
    return "\n".join(lines)
