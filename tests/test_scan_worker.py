"""
Unit tests for Celery scan worker
"""
import pytest
from uuid import uuid4
from unittest.mock import Mock, patch, AsyncMock
from datetime import datetime
import json

from app.workers.scan_worker import (
    process_scan,
    _process_scan_async,
    _execute_cli_tool,
    _generate_text_report,
    _update_scan_status,
)
from app.models.scan import Scan, ScanStatus
from app.models.user import User, UserTier


@pytest.mark.asyncio
class TestScanWorker:
    """Test suite for scan worker"""
    
    async def test_update_scan_status(self, async_db_session):
        """Test updating scan status"""
        # Create user and scan
        user = User(
            id=uuid4(),
            email="test@example.com",
            password_hash="hashed",
            tier=UserTier.FREE,
        )
        async_db_session.add(user)
        
        scan = Scan(
            id=uuid4(),
            user_id=user.id,
            target="https://example.com",
            scan_mode="common",
            status=ScanStatus.QUEUED,
        )
        async_db_session.add(scan)
        await async_db_session.commit()
        
        # Update status
        started_at = datetime.utcnow()
        await _update_scan_status(
            async_db_session,
            scan.id,
            ScanStatus.RUNNING,
            started_at=started_at,
        )
        
        # Verify update
        await async_db_session.refresh(scan)
        assert scan.status == ScanStatus.RUNNING
        assert scan.started_at is not None
    
    async def test_update_scan_status_with_error(self, async_db_session):
        """Test updating scan status with error message"""
        # Create user and scan
        user = User(
            id=uuid4(),
            email="test@example.com",
            password_hash="hashed",
            tier=UserTier.FREE,
        )
        async_db_session.add(user)
        
        scan = Scan(
            id=uuid4(),
            user_id=user.id,
            target="https://example.com",
            scan_mode="common",
            status=ScanStatus.RUNNING,
        )
        async_db_session.add(scan)
        await async_db_session.commit()
        
        # Update with error
        error_msg = "Connection timeout"
        await _update_scan_status(
            async_db_session,
            scan.id,
            ScanStatus.FAILED,
            completed_at=datetime.utcnow(),
            error_message=error_msg,
        )
        
        # Verify update
        await async_db_session.refresh(scan)
        assert scan.status == ScanStatus.FAILED
        assert scan.error_message == error_msg
        assert scan.completed_at is not None
    
    @patch("app.workers.scan_worker.asyncio.create_subprocess_exec")
    async def test_execute_cli_tool_success(self, mock_subprocess):
        """Test successful CLI tool execution"""
        # Mock subprocess
        mock_process = AsyncMock()
        mock_process.returncode = 0
        mock_result = {
            "target": "https://example.com",
            "vulnerabilities": [
                {"type": "XSS", "severity": "high"},
                {"type": "SQL Injection", "severity": "critical"},
            ],
            "platform_detected": "WordPress",
            "confidence": 0.85,
        }
        mock_process.communicate.return_value = (
            json.dumps(mock_result).encode(),
            b"",
        )
        mock_subprocess.return_value = mock_process
        
        # Execute CLI tool
        result = await _execute_cli_tool("https://example.com", "common")
        
        # Verify result
        assert result["target"] == "https://example.com"
        assert len(result["vulnerabilities"]) == 2
        assert result["platform_detected"] == "WordPress"
    
    @patch("app.workers.scan_worker.asyncio.create_subprocess_exec")
    async def test_execute_cli_tool_failure(self, mock_subprocess):
        """Test CLI tool execution failure"""
        # Mock subprocess failure
        mock_process = AsyncMock()
        mock_process.returncode = 1
        mock_process.communicate.return_value = (
            b"",
            b"Error: Connection refused",
        )
        mock_subprocess.return_value = mock_process
        
        # Execute CLI tool (should raise exception)
        with pytest.raises(RuntimeError) as exc_info:
            await _execute_cli_tool("https://example.com", "common")
        
        assert "CLI tool execution failed" in str(exc_info.value)
    
    @patch("app.workers.scan_worker.asyncio.create_subprocess_exec")
    async def test_execute_cli_tool_invalid_json(self, mock_subprocess):
        """Test CLI tool with invalid JSON output"""
        # Mock subprocess with invalid JSON
        mock_process = AsyncMock()
        mock_process.returncode = 0
        mock_process.communicate.return_value = (
            b"Invalid JSON output",
            b"",
        )
        mock_subprocess.return_value = mock_process
        
        # Execute CLI tool (should raise exception)
        with pytest.raises(RuntimeError) as exc_info:
            await _execute_cli_tool("https://example.com", "common")
        
        assert "Failed to parse scan results" in str(exc_info.value)
    
    def test_generate_text_report(self):
        """Test text report generation"""
        scan_result = {
            "target": "https://example.com",
            "platform_detected": "WordPress",
            "confidence": 0.85,
            "scan_date": "2024-12-28",
            "vulnerabilities": [
                {
                    "type": "XSS",
                    "severity": "high",
                    "description": "Cross-site scripting vulnerability",
                    "recommendation": "Sanitize user input",
                },
                {
                    "type": "SQL Injection",
                    "severity": "critical",
                    "description": "SQL injection vulnerability",
                    "recommendation": "Use parameterized queries",
                },
            ],
        }
        
        report = _generate_text_report(scan_result)
        
        # Verify report content
        assert "SECURITY SCAN REPORT" in report
        assert "https://example.com" in report
        assert "WordPress" in report
        assert "XSS" in report
        assert "SQL Injection" in report
        assert "Critical: 1" in report
        assert "High: 1" in report
    
    def test_generate_text_report_no_vulnerabilities(self):
        """Test text report with no vulnerabilities"""
        scan_result = {
            "target": "https://example.com",
            "platform_detected": "Unknown",
            "confidence": 0.0,
            "scan_date": "2024-12-28",
            "vulnerabilities": [],
        }
        
        report = _generate_text_report(scan_result)
        
        # Verify report content
        assert "SECURITY SCAN REPORT" in report
        assert "Total: 0" in report
    
    @patch("app.workers.scan_worker._execute_cli_tool")
    @patch("app.workers.scan_worker.queue_service")
    async def test_process_scan_async_success(
        self,
        mock_queue_service,
        mock_execute_cli,
        async_db_session,
    ):
        """Test successful scan processing"""
        # Create user and scan
        user = User(
            id=uuid4(),
            email="test@example.com",
            password_hash="hashed",
            tier=UserTier.FREE,
        )
        async_db_session.add(user)
        
        scan = Scan(
            id=uuid4(),
            user_id=user.id,
            target="https://example.com",
            scan_mode="common",
            status=ScanStatus.QUEUED,
        )
        async_db_session.add(scan)
        await async_db_session.commit()
        
        # Mock CLI tool execution
        mock_execute_cli.return_value = {
            "target": "https://example.com",
            "vulnerabilities": [
                {"type": "XSS", "severity": "high"},
            ],
            "platform_detected": "WordPress",
            "confidence": 0.85,
            "scan_date": "2024-12-28",
        }
        
        # Mock queue service
        mock_queue_service.set_job_status = AsyncMock()
        
        # Process scan
        result = await _process_scan_async(
            str(scan.id),
            str(user.id),
            "https://example.com",
            "common",
        )
        
        # Verify result
        assert result["status"] == "completed"
        assert result["vulnerabilities_found"] == 1
        
        # Verify scan was updated
        await async_db_session.refresh(scan)
        assert scan.status == ScanStatus.COMPLETED
        assert scan.vulnerabilities_found == 1
        assert scan.high_count == 1
        assert scan.report_json is not None
        assert scan.report_text is not None
    
    @patch("app.workers.scan_worker._execute_cli_tool")
    @patch("app.workers.scan_worker.queue_service")
    async def test_process_scan_async_failure(
        self,
        mock_queue_service,
        mock_execute_cli,
        async_db_session,
    ):
        """Test scan processing failure"""
        # Create user and scan
        user = User(
            id=uuid4(),
            email="test@example.com",
            password_hash="hashed",
            tier=UserTier.FREE,
        )
        async_db_session.add(user)
        
        scan = Scan(
            id=uuid4(),
            user_id=user.id,
            target="https://example.com",
            scan_mode="common",
            status=ScanStatus.QUEUED,
        )
        async_db_session.add(scan)
        await async_db_session.commit()
        
        # Mock CLI tool failure
        mock_execute_cli.side_effect = RuntimeError("Connection timeout")
        
        # Mock queue service
        mock_queue_service.set_job_status = AsyncMock()
        
        # Process scan (should raise exception)
        with pytest.raises(RuntimeError):
            await _process_scan_async(
                str(scan.id),
                str(user.id),
                "https://example.com",
                "common",
            )
        
        # Verify scan was marked as failed
        await async_db_session.refresh(scan)
        assert scan.status == ScanStatus.FAILED
        assert scan.error_message is not None
    
    @patch("app.workers.scan_worker.asyncio.get_event_loop")
    @patch("app.workers.scan_worker._process_scan_async")
    def test_process_scan_task(self, mock_process_async, mock_get_loop):
        """Test Celery task wrapper"""
        # Mock event loop
        mock_loop = Mock()
        mock_get_loop.return_value = mock_loop
        mock_loop.run_until_complete.return_value = {
            "scan_id": "test-id",
            "status": "completed",
            "vulnerabilities_found": 5,
            "duration_seconds": 120,
        }
        
        # Call task
        result = process_scan(
            "test-id",
            "user-id",
            "https://example.com",
            "common",
        )
        
        # Verify result
        assert result["status"] == "completed"
        assert result["vulnerabilities_found"] == 5
        
        # Verify async function was called
        mock_loop.run_until_complete.assert_called_once()
