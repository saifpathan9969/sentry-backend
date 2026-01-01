"""
Unit tests for Redis job queue service
"""
import pytest
from uuid import uuid4
import json

from app.services.queue_service import QueueService
from app.models.user import UserTier


@pytest.mark.asyncio
class TestQueueService:
    """Test suite for QueueService"""
    
    @pytest.fixture
    async def queue_service(self):
        """Create a queue service instance for testing"""
        service = QueueService()
        yield service
        # Cleanup
        await service.clear_queue("all")
        await service.close()
    
    async def test_enqueue_scan_free_tier(self, queue_service):
        """Test enqueuing a scan for Free tier user"""
        scan_id = uuid4()
        user_id = uuid4()
        
        result = await queue_service.enqueue_scan(
            scan_id=scan_id,
            user_id=user_id,
            target_url="https://example.com",
            scan_mode="common",
            user_tier=UserTier.FREE,
        )
        
        assert result is True
        
        # Verify it's in the normal priority queue
        queue_length = await queue_service.get_queue_length("normal")
        assert queue_length == 1
        
        # Verify status is set
        status = await queue_service.get_job_status(scan_id)
        assert status == "queued"
    
    async def test_enqueue_scan_premium_tier(self, queue_service):
        """Test enqueuing a scan for Premium tier user (high priority)"""
        scan_id = uuid4()
        user_id = uuid4()
        
        result = await queue_service.enqueue_scan(
            scan_id=scan_id,
            user_id=user_id,
            target_url="https://example.com",
            scan_mode="full",
            user_tier=UserTier.PREMIUM,
        )
        
        assert result is True
        
        # Verify it's in the high priority queue
        queue_length = await queue_service.get_queue_length("high")
        assert queue_length == 1
    
    async def test_enqueue_scan_enterprise_tier(self, queue_service):
        """Test enqueuing a scan for Enterprise tier user (high priority)"""
        scan_id = uuid4()
        user_id = uuid4()
        
        result = await queue_service.enqueue_scan(
            scan_id=scan_id,
            user_id=user_id,
            target_url="https://example.com",
            scan_mode="custom",
            user_tier=UserTier.ENTERPRISE,
        )
        
        assert result is True
        
        # Verify it's in the high priority queue
        queue_length = await queue_service.get_queue_length("high")
        assert queue_length == 1
    
    async def test_dequeue_scan(self, queue_service):
        """Test dequeuing a scan job"""
        scan_id = uuid4()
        user_id = uuid4()
        target_url = "https://example.com"
        
        # Enqueue a job
        await queue_service.enqueue_scan(
            scan_id=scan_id,
            user_id=user_id,
            target_url=target_url,
            scan_mode="common",
            user_tier=UserTier.FREE,
        )
        
        # Dequeue the job
        job = await queue_service.dequeue_scan(timeout=0)
        
        assert job is not None
        assert job["scan_id"] == str(scan_id)
        assert job["user_id"] == str(user_id)
        assert job["target_url"] == target_url
        assert job["scan_mode"] == "common"
        assert "enqueued_at" in job
    
    async def test_dequeue_priority_order(self, queue_service):
        """Test that high priority jobs are dequeued first"""
        # Enqueue a normal priority job
        normal_scan_id = uuid4()
        await queue_service.enqueue_scan(
            scan_id=normal_scan_id,
            user_id=uuid4(),
            target_url="https://normal.com",
            scan_mode="common",
            user_tier=UserTier.FREE,
        )
        
        # Enqueue a high priority job
        high_scan_id = uuid4()
        await queue_service.enqueue_scan(
            scan_id=high_scan_id,
            user_id=uuid4(),
            target_url="https://premium.com",
            scan_mode="full",
            user_tier=UserTier.PREMIUM,
        )
        
        # Dequeue should get high priority first
        job = await queue_service.dequeue_scan(timeout=0)
        assert job["scan_id"] == str(high_scan_id)
        
        # Next dequeue should get normal priority
        job = await queue_service.dequeue_scan(timeout=0)
        assert job["scan_id"] == str(normal_scan_id)
    
    async def test_dequeue_empty_queue(self, queue_service):
        """Test dequeuing from empty queue"""
        job = await queue_service.dequeue_scan(timeout=0)
        assert job is None
    
    async def test_get_job_status(self, queue_service):
        """Test getting job status"""
        scan_id = uuid4()
        
        # Set status
        await queue_service.set_job_status(scan_id, "processing")
        
        # Get status
        status = await queue_service.get_job_status(scan_id)
        assert status == "processing"
    
    async def test_set_job_status(self, queue_service):
        """Test setting job status"""
        scan_id = uuid4()
        
        result = await queue_service.set_job_status(scan_id, "completed")
        assert result is True
        
        # Verify status was set
        status = await queue_service.get_job_status(scan_id)
        assert status == "completed"
    
    async def test_cancel_job(self, queue_service):
        """Test cancelling a job"""
        scan_id = uuid4()
        
        # Set initial status
        await queue_service.set_job_status(scan_id, "queued")
        
        # Cancel job
        result = await queue_service.cancel_job(scan_id)
        assert result is True
        
        # Verify status is cancelled
        status = await queue_service.get_job_status(scan_id)
        assert status == "cancelled"
    
    async def test_get_queue_length_normal(self, queue_service):
        """Test getting normal queue length"""
        # Enqueue 3 jobs
        for i in range(3):
            await queue_service.enqueue_scan(
                scan_id=uuid4(),
                user_id=uuid4(),
                target_url=f"https://example{i}.com",
                scan_mode="common",
                user_tier=UserTier.FREE,
            )
        
        length = await queue_service.get_queue_length("normal")
        assert length == 3
    
    async def test_get_queue_length_high(self, queue_service):
        """Test getting high priority queue length"""
        # Enqueue 2 high priority jobs
        for i in range(2):
            await queue_service.enqueue_scan(
                scan_id=uuid4(),
                user_id=uuid4(),
                target_url=f"https://example{i}.com",
                scan_mode="full",
                user_tier=UserTier.PREMIUM,
            )
        
        length = await queue_service.get_queue_length("high")
        assert length == 2
    
    async def test_get_queue_length_all(self, queue_service):
        """Test getting total queue length"""
        # Enqueue 2 normal priority jobs
        for i in range(2):
            await queue_service.enqueue_scan(
                scan_id=uuid4(),
                user_id=uuid4(),
                target_url=f"https://example{i}.com",
                scan_mode="common",
                user_tier=UserTier.FREE,
            )
        
        # Enqueue 3 high priority jobs
        for i in range(3):
            await queue_service.enqueue_scan(
                scan_id=uuid4(),
                user_id=uuid4(),
                target_url=f"https://example{i}.com",
                scan_mode="full",
                user_tier=UserTier.PREMIUM,
            )
        
        length = await queue_service.get_queue_length("all")
        assert length == 5
    
    async def test_clear_queue_normal(self, queue_service):
        """Test clearing normal priority queue"""
        # Enqueue jobs
        await queue_service.enqueue_scan(
            scan_id=uuid4(),
            user_id=uuid4(),
            target_url="https://example.com",
            scan_mode="common",
            user_tier=UserTier.FREE,
        )
        
        # Clear normal queue
        result = await queue_service.clear_queue("normal")
        assert result is True
        
        # Verify queue is empty
        length = await queue_service.get_queue_length("normal")
        assert length == 0
    
    async def test_clear_queue_all(self, queue_service):
        """Test clearing all queues"""
        # Enqueue jobs in both queues
        await queue_service.enqueue_scan(
            scan_id=uuid4(),
            user_id=uuid4(),
            target_url="https://example.com",
            scan_mode="common",
            user_tier=UserTier.FREE,
        )
        await queue_service.enqueue_scan(
            scan_id=uuid4(),
            user_id=uuid4(),
            target_url="https://example.com",
            scan_mode="full",
            user_tier=UserTier.PREMIUM,
        )
        
        # Clear all queues
        result = await queue_service.clear_queue("all")
        assert result is True
        
        # Verify both queues are empty
        length = await queue_service.get_queue_length("all")
        assert length == 0
        await queue_service.set_job_status(scan_id, "processing")
        
        # Get status
        status = await queue_service.get_job_status(scan_id)
        assert status == "processing"
    
    async def test_set_job_status(self, queue_service):
        """Test setting job status"""
        scan_id = uuid4()
        
        result = await queue_service.set_job_status(scan_id, "completed")
        assert result is True
        
        status = await queue_service.get_job_status(scan_id)
        assert status == "completed"
    
    async def test_cancel_job(self, queue_service):
        """Test cancelling a job"""
        scan_id = uuid4()
        
        # Set initial status
        await queue_service.set_job_status(scan_id, "queued")
        
        # Cancel job
        result = await queue_service.cancel_job(scan_id)
        assert result is True
        
        # Verify status is cancelled
        status = await queue_service.get_job_status(scan_id)
        assert status == "cancelled"
    
    async def test_get_queue_length_high(self, queue_service):
        """Test getting high priority queue length"""
        # Enqueue 3 high priority jobs
        for i in range(3):
            await queue_service.enqueue_scan(
                scan_id=uuid4(),
                user_id=uuid4(),
                target_url=f"https://example{i}.com",
                scan_mode="full",
                user_tier=UserTier.PREMIUM,
            )
        
        length = await queue_service.get_queue_length("high")
        assert length == 3
    
    async def test_get_queue_length_normal(self, queue_service):
        """Test getting normal priority queue length"""
        # Enqueue 2 normal priority jobs
        for i in range(2):
            await queue_service.enqueue_scan(
                scan_id=uuid4(),
                user_id=uuid4(),
                target_url=f"https://example{i}.com",
                scan_mode="common",
                user_tier=UserTier.FREE,
            )
        
        length = await queue_service.get_queue_length("normal")
        assert length == 2
    
    async def test_get_queue_length_all(self, queue_service):
        """Test getting total queue length"""
        # Enqueue 2 high priority jobs
        for i in range(2):
            await queue_service.enqueue_scan(
                scan_id=uuid4(),
                user_id=uuid4(),
                target_url=f"https://high{i}.com",
                scan_mode="full",
                user_tier=UserTier.PREMIUM,
            )
        
        # Enqueue 3 normal priority jobs
        for i in range(3):
            await queue_service.enqueue_scan(
                scan_id=uuid4(),
                user_id=uuid4(),
                target_url=f"https://normal{i}.com",
                scan_mode="common",
                user_tier=UserTier.FREE,
            )
        
        length = await queue_service.get_queue_length("all")
        assert length == 5
    
    async def test_clear_queue_high(self, queue_service):
        """Test clearing high priority queue"""
        # Enqueue jobs in both queues
        await queue_service.enqueue_scan(
            scan_id=uuid4(),
            user_id=uuid4(),
            target_url="https://high.com",
            scan_mode="full",
            user_tier=UserTier.PREMIUM,
        )
        await queue_service.enqueue_scan(
            scan_id=uuid4(),
            user_id=uuid4(),
            target_url="https://normal.com",
            scan_mode="common",
            user_tier=UserTier.FREE,
        )
        
        # Clear high priority queue
        await queue_service.clear_queue("high")
        
        # Verify high is empty, normal is not
        assert await queue_service.get_queue_length("high") == 0
        assert await queue_service.get_queue_length("normal") == 1
    
    async def test_clear_queue_all(self, queue_service):
        """Test clearing all queues"""
        # Enqueue jobs in both queues
        await queue_service.enqueue_scan(
            scan_id=uuid4(),
            user_id=uuid4(),
            target_url="https://high.com",
            scan_mode="full",
            user_tier=UserTier.PREMIUM,
        )
        await queue_service.enqueue_scan(
            scan_id=uuid4(),
            user_id=uuid4(),
            target_url="https://normal.com",
            scan_mode="common",
            user_tier=UserTier.FREE,
        )
        
        # Clear all queues
        await queue_service.clear_queue("all")
        
        # Verify both are empty
        assert await queue_service.get_queue_length("all") == 0
