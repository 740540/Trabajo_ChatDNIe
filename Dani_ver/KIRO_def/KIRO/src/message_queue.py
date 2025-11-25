"""Message queue for offline delivery"""

import json
import os
import time
from typing import List, Dict


class MessageQueue:
    """Manages queued messages for offline peers"""
    
    def __init__(self, queue_file: str):
        self.queue_file = queue_file
        self.queue: Dict[str, List[dict]] = {}
        self.load_queue()
    
    def load_queue(self):
        """Load message queue from file"""
        if os.path.exists(self.queue_file):
            with open(self.queue_file, 'r') as f:
                self.queue = json.load(f)
    
    def save_queue(self):
        """Save message queue to file"""
        with open(self.queue_file, 'w') as f:
            json.dump(self.queue, f, indent=2)
    
    def enqueue(self, recipient_fingerprint: str, message: str, stream_id: int):
        """Add message to queue for offline recipient"""
        if recipient_fingerprint not in self.queue:
            self.queue[recipient_fingerprint] = []
        
        self.queue[recipient_fingerprint].append({
            'message': message,
            'stream_id': stream_id,
            'timestamp': time.time()
        })
        self.save_queue()
    
    def dequeue(self, recipient_fingerprint: str) -> List[dict]:
        """Get and remove all queued messages for recipient"""
        messages = self.queue.get(recipient_fingerprint, [])
        if recipient_fingerprint in self.queue:
            del self.queue[recipient_fingerprint]
            self.save_queue()
        return messages
    
    def has_messages(self, recipient_fingerprint: str) -> bool:
        """Check if there are queued messages for recipient"""
        return recipient_fingerprint in self.queue and len(self.queue[recipient_fingerprint]) > 0
    
    def get_queue_size(self, recipient_fingerprint: str) -> int:
        """Get number of queued messages for recipient"""
        return len(self.queue.get(recipient_fingerprint, []))
