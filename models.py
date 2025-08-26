from datetime import datetime
from app import db

class BannedIP(db.Model):
    """Model for storing banned IP addresses from Fail2ban"""
    
    id = db.Column(db.Integer, primary_key=True)
    ip_address = db.Column(db.String(45), nullable=False)  # Support IPv4 and IPv6
    jail = db.Column(db.String(100), nullable=False)
    banned_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    
    # Create composite index for better query performance
    __table_args__ = (
        db.Index('idx_ip_jail', 'ip_address', 'jail'),
        db.Index('idx_banned_at', 'banned_at'),
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
