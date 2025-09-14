# Version: v2.1.0
import subprocess
import re
import logging
from typing import List, Dict, Any

logger = logging.getLogger(__name__)

class Fail2banService:
    """Service class for interacting with Fail2ban"""
    
    def __init__(self):
        self.fail2ban_client = 'fail2ban-client'
    
    def get_service_status(self) -> Dict[str, Any]:
        """Check if Fail2ban service is running and accessible"""
        try:
            result = subprocess.run(
                [self.fail2ban_client, 'ping'],
                capture_output=True,
                text=True,
                timeout=10
            )
            
            if result.returncode == 0:
                return {
                    'running': True,
                    'message': 'Fail2ban service is running',
                    'version': self._get_version()
                }
            else:
                return {
                    'running': False,
                    'error': f"Fail2ban client error: {result.stderr.strip()}"
                }
                
        except subprocess.TimeoutExpired:
            return {
                'running': False,
                'error': 'Timeout connecting to Fail2ban service'
            }
        except FileNotFoundError:
            return {
                'running': False,
                'error': 'fail2ban-client not found. Is Fail2ban installed?'
            }
        except Exception as e:
            return {
                'running': False,
                'error': f'Unexpected error: {str(e)}'
            }
    
    def _get_version(self) -> str:
        """Get Fail2ban version"""
        try:
            result = subprocess.run(
                [self.fail2ban_client, 'version'],
                capture_output=True,
                text=True,
                timeout=5
            )
            
            if result.returncode == 0:
                return result.stdout.strip()
            return 'Unknown'
        except Exception:
            return 'Unknown'
    
    def get_jails(self) -> List[str]:
        """Get list of active Fail2ban jails"""
        try:
            result = subprocess.run(
                [self.fail2ban_client, 'status'],
                capture_output=True,
                text=True,
                timeout=10
            )
            
            if result.returncode != 0:
                logger.error(f"Failed to get jails: {result.stderr}")
                return []
            
            # Parse jail list from output
            output = result.stdout
            jail_line_pattern = r'Jail list:\s*(.+)'
            match = re.search(jail_line_pattern, output)
            
            if match:
                jail_list_str = match.group(1).strip()
                if jail_list_str:
                    jails = [jail.strip() for jail in jail_list_str.split(',')]
                    return jails
            
            return []
            
        except Exception as e:
            logger.error(f"Error getting jails: {str(e)}")
            return []
    
    def get_banned_ips_for_jail(self, jail: str) -> List[str]:
        """Get banned IPs for a specific jail"""
        try:
            result = subprocess.run(
                [self.fail2ban_client, 'status', jail],
                capture_output=True,
                text=True,
                timeout=10
            )
            
            if result.returncode != 0:
                logger.error(f"Failed to get banned IPs for jail {jail}: {result.stderr}")
                return []
            
            # Parse banned IPs from output
            output = result.stdout
            banned_ip_pattern = r'Banned IP list:\s*(.+)'
            match = re.search(banned_ip_pattern, output)
            
            if match:
                banned_ips_str = match.group(1).strip()
                if banned_ips_str and banned_ips_str != '':
                    # Split by whitespace and filter out empty strings
                    banned_ips = [ip.strip() for ip in banned_ips_str.split() if ip.strip()]
                    return banned_ips
            
            return []
            
        except Exception as e:
            logger.error(f"Error getting banned IPs for jail {jail}: {str(e)}")
            return []
    
    def get_banned_ips(self) -> List[Dict[str, str]]:
        """Get all banned IPs from all active jails"""
        banned_ips = []
        
        # Check service status first
        status = self.get_service_status()
        if not status['running']:
            logger.warning(f"Fail2ban service not running: {status.get('error', 'Unknown error')}")
            return []
        
        # Get all jails
        jails = self.get_jails()
        logger.info(f"Found {len(jails)} active jails: {jails}")
        
        # Get banned IPs for each jail
        for jail in jails:
            try:
                jail_banned_ips = self.get_banned_ips_for_jail(jail)
                logger.info(f"Jail '{jail}' has {len(jail_banned_ips)} banned IPs")
                
                for ip in jail_banned_ips:
                    banned_ips.append({
                        'ip': ip,
                        'jail': jail
                    })
                    
            except Exception as e:
                logger.error(f"Error processing jail {jail}: {str(e)}")
                continue
        
        logger.info(f"Total banned IPs found: {len(banned_ips)}")
        return banned_ips
