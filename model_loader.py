"""
Dynamic model loader for SQLAlchemy models.
This module handles safe model registration and prevents mapping conflicts.
"""
import threading
from database import db

# Thread-safe singleton pattern
_model_lock = threading.Lock()
_banned_ip_model = None

def get_model(model_name):
    """Get a model class by name, thread-safe singleton"""
    global _banned_ip_model
    
    if model_name == 'BannedIP':
        if _banned_ip_model is not None:
            return _banned_ip_model
        
        with _model_lock:
            # Double-check pattern
            if _banned_ip_model is not None:
                return _banned_ip_model
            
            # Check if model already exists in SQLAlchemy registry
            try:
                registry = db.Model.registry._class_registry
                if 'BannedIP' in registry:
                    _banned_ip_model = registry['BannedIP']
                    return _banned_ip_model
            except (AttributeError, KeyError):
                pass
            
            # Create the model
            from datetime import datetime
            
            class BannedIP(db.Model):
                """Model for storing banned IP addresses from Fail2ban"""
                __tablename__ = 'banned_ip'
                
                id = db.Column(db.Integer, primary_key=True)
                ip_address = db.Column(db.String(45), nullable=False)  # Support IPv4 and IPv6
                jail = db.Column(db.String(100), nullable=False)
                banned_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
                
                # Create composite index for better query performance
                __table_args__ = (
                    db.Index('idx_ip_jail', 'ip_address', 'jail'),
                    db.Index('idx_banned_at', 'banned_at'),
                    {'extend_existing': True}
                )
                
                def __repr__(self):
                    return f'<BannedIP {self.ip_address} in {self.jail}>'
                
                def to_dict(self):
                    """Convert to dictionary for JSON serialization"""
                    return {
                        'id': self.id,
                        'ip_address': self.ip_address,
                        'jail': self.jail,
                        'banned_at': self.banned_at.isoformat(),
                        'abuse_url': f"https://abuseipdb.com/check/{self.ip_address}"
                    }
            
            _banned_ip_model = BannedIP
            return _banned_ip_model
    
    raise ValueError(f"Unknown model: {model_name}")