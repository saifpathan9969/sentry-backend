"""
Redis job queue service for scan processing
"""
import json
import redis.asyncio as redis
from typing import Optional
from uuid import UUID
from datetime import datetime

from app.core.config import settings


def normalize_tier(tier) -> str:
    """Convert tier to lowercase string regardless of whether it's an enum or string"""
    if isinstance(tier, str):
        return tier.lower()
    elif hasattr(tier, 'value'):
        return tier.value.lower()
    else:
        return str(tier).lower()


class QueueService:
    """Service for managing scan job queue with Redis"""
    
    # Queue names
    QUEUE_HIGH_PRIORITY = "scan_queue:high"  # Premium/Enterprise
    QUEUE_NORMAL_PRIORITY = "scan_queue:normal"  # Free tier
    QUEUE_STATUS = "scan_status:"  # Prefix for status tracking
    
    def __init__(self):
        """Initialize Redis connection"""
        self._redis: Optional[redis.Redis] = None
    
    async def get_redis(self) -> redis.Redis:
        """Get or create Redis connection"""
        if self._redis is None:
            self._redis = await redis.from_url(
                settings.REDIS_URL,
                encoding="utf-8",
                decode_responses=True
            )
        return self._redis
    
    async def close(self):
        """Close Redis connection"""
        if self._redis:
            await self._redis.close()
            self._redis = None
    
    async def enqueue_scan(
        self,
        scan_id: UUID,
        user_id: UUID,
        target_url: str,
        scan_mode: str,
        user_tier,
    ) -> bool:
        """
        Enqueue a scan for processing
        
        Args:
            scan_id: Scan ID
            user_id: User ID
            target_url: Target URL to scan
            scan_mode: Scan mode
            user_tier: User's subscription tier (string or enum)
            
        Returns:
            True if enqueued successfully
        """
        redis_client = await self.get_redis()
        
        # Create job data
        job_data = {
            "scan_id": str(scan_id),
            "user_id": str(user_id),
            "target_url": target_url,
            "scan_mode": scan_mode,
            "enqueued_at": datetime.utcnow().isoformat(),
        }
        
        # Normalize tier to string for comparison
        tier_str = normalize_tier(user_tier)
        
        # Determine queue based on tier (Premium/Enterprise get priority)
        queue_name = (
            self.QUEUE_HIGH_PRIORITY
            if tier_str in ['premium', 'enterprise']
            else self.QUEUE_NORMAL_PRIORITY
        )
        
        # Push to queue (LPUSH for FIFO with BRPOP)
        await redis_client.lpush(queue_name, json.dumps(job_data))
        
        # Set initial status
        await self.set_job_status(scan_id, "queued")
        
        return True
    
    async def dequeue_scan(self, timeout: int = 0) -> Optional[dict]:
        """
        Dequeue a scan job for processing
        
        Priority: High priority queue first, then normal priority
        
        Args:
            timeout: Blocking timeout in seconds (0 = non-blocking)
            
        Returns:
            Job data dict or None if no jobs available
        """
        redis_client = await self.get_redis()
        
        # Try high priority queue first
        if timeout > 0:
            result = await redis_client.brpop(
                [self.QUEUE_HIGH_PRIORITY, self.QUEUE_NORMAL_PRIORITY],
                timeout=timeout
            )
        else:
            # Non-blocking: try high priority first, then normal
            result = await redis_client.rpop(self.QUEUE_HIGH_PRIORITY)
            if result:
                result = (self.QUEUE_HIGH_PRIORITY, result)
            else:
                result = await redis_client.rpop(self.QUEUE_NORMAL_PRIORITY)
                if result:
                    result = (self.QUEUE_NORMAL_PRIORITY, result)
        
        if result:
            _, job_json = result
            job_data = json.loads(job_json)
            return job_data
        
        return None
    
    async def get_job_status(self, scan_id: UUID) -> Optional[str]:
        """
        Get job status from Redis
        
        Args:
            scan_id: Scan ID
            
        Returns:
            Status string or None if not found
        """
        redis_client = await self.get_redis()
        status = await redis_client.get(f"{self.QUEUE_STATUS}{scan_id}")
        return status
    
    async def set_job_status(
        self,
        scan_id: UUID,
        status: str,
        ttl: int = 86400,  # 24 hours
    ) -> bool:
        """
        Set job status in Redis
        
        Args:
            scan_id: Scan ID
            status: Status string (queued, processing, completed, failed, cancelled)
            ttl: Time to live in seconds
            
        Returns:
            True if set successfully
        """
        redis_client = await self.get_redis()
        await redis_client.setex(
            f"{self.QUEUE_STATUS}{scan_id}",
            ttl,
            status
        )
        return True
    
    async def cancel_job(self, scan_id: UUID) -> bool:
        """
        Cancel a queued job
        
        Note: This only marks the job as cancelled in Redis.
        The job may still be in the queue, but workers should check
        the status before processing.
        
        Args:
            scan_id: Scan ID
            
        Returns:
            True if cancelled successfully
        """
        await self.set_job_status(scan_id, "cancelled")
        return True
    
    async def get_queue_length(self, priority: str = "all") -> int:
        """
        Get the number of jobs in queue(s)
        
        Args:
            priority: "high", "normal", or "all"
            
        Returns:
            Number of jobs in queue
        """
        redis_client = await self.get_redis()
        
        if priority == "high":
            return await redis_client.llen(self.QUEUE_HIGH_PRIORITY)
        elif priority == "normal":
            return await redis_client.llen(self.QUEUE_NORMAL_PRIORITY)
        else:  # all
            high = await redis_client.llen(self.QUEUE_HIGH_PRIORITY)
            normal = await redis_client.llen(self.QUEUE_NORMAL_PRIORITY)
            return high + normal
    
    async def clear_queue(self, priority: str = "all") -> bool:
        """
        Clear queue(s) - for testing/admin purposes
        
        Args:
            priority: "high", "normal", or "all"
            
        Returns:
            True if cleared successfully
        """
        redis_client = await self.get_redis()
        
        if priority in ["high", "all"]:
            await redis_client.delete(self.QUEUE_HIGH_PRIORITY)
        if priority in ["normal", "all"]:
            await redis_client.delete(self.QUEUE_NORMAL_PRIORITY)
        
        return True


# Global queue service instance
queue_service = QueueService()
