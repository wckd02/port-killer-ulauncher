import os
import signal
import logging
import psutil
import subprocess
from time import time
from typing import List, Optional, Tuple

from ulauncher.api.client.Extension import Extension
from ulauncher.api.client.EventListener import EventListener
from ulauncher.api.shared.event import KeywordQueryEvent, ItemEnterEvent
from ulauncher.api.shared.item.ExtensionResultItem import ExtensionResultItem
from ulauncher.api.shared.action.RenderResultListAction import RenderResultListAction
from ulauncher.api.shared.action.ExtensionCustomAction import ExtensionCustomAction
from ulauncher.api.shared.action.HideWindowAction import HideWindowAction

logger = logging.getLogger(__name__)
if not logger.handlers:
    # Basic logging config (ulauncher may override, but ensures we see errors)
    logging.basicConfig(level=logging.INFO)


class PortInfo:
    """Data structure for port information"""
    def __init__(self, port: int, protocol: str, pid: int, process_name: str, 
                 local_address: str, remote_address: str = ""):
        self.port = port
        self.protocol = protocol
        self.pid = pid
        self.process_name = process_name
        self.local_address = local_address
        self.remote_address = remote_address

    def __repr__(self):
        return f"PortInfo(port={self.port}, protocol={self.protocol}, pid={self.pid}, process={self.process_name})"


class PortScanner:
    """Handles port discovery and process management"""
    
    def __init__(self):
        self._cache = {}
        self._cache_time = 0
        self._cache_duration = 2  # Cache for 2 seconds
    
    def get_active_ports(self, show_system_ports: bool = False) -> List[PortInfo]:
        """Get list of active ports with process information"""
        current_time = time()
        
        # Use cache if available and fresh
        if (current_time - self._cache_time < self._cache_duration and 
            show_system_ports in self._cache):
            return self._cache[show_system_ports]
        
        ports = []
        
        try:
            # Get network connections using psutil
            connections = psutil.net_connections(kind='inet')
            
            for conn in connections:
                if conn.status == psutil.CONN_LISTEN and conn.laddr:
                    port = conn.laddr.port
                    
                    # Filter system ports if requested
                    if not show_system_ports and port < 1024:
                        continue
                    
                    try:
                        # Get process information
                        if conn.pid:
                            process = psutil.Process(conn.pid)
                            process_name = process.name()
                            
                            # Determine protocol
                            protocol = "TCP" if conn.type == 1 else "UDP"
                            
                            # Format addresses
                            local_addr = f"{conn.laddr.ip}:{conn.laddr.port}"
                            remote_addr = ""
                            if conn.raddr:
                                remote_addr = f"{conn.raddr.ip}:{conn.raddr.port}"
                            
                            port_info = PortInfo(
                                port=port,
                                protocol=protocol,
                                pid=conn.pid,
                                process_name=process_name,
                                local_address=local_addr,
                                remote_address=remote_addr
                            )
                            ports.append(port_info)
                            
                    except (psutil.NoSuchProcess, psutil.AccessDenied):
                        # Process may have died or we don't have permission
                        continue
                        
        except Exception as e:
            logger.error(f"Error scanning ports: {e}")
            # Fallback to system commands if psutil fails
            ports = self._fallback_port_scan(show_system_ports)
        
        # Cache the results
        self._cache[show_system_ports] = ports
        self._cache_time = current_time
        
        return ports
    
    def _fallback_port_scan(self, show_system_ports: bool) -> List[PortInfo]:
        """Fallback method using system commands"""
        ports = []
        
        try:
            # Try netstat first
            cmd = ["netstat", "-tulpn"]
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=5)
            
            if result.returncode == 0:
                lines = result.stdout.split('\n')
                for line in lines[2:]:  # Skip header lines
                    if 'LISTEN' in line:
                        parts = line.split()
                        if len(parts) >= 7:
                            try:
                                # Parse netstat output
                                proto = parts[0].upper()
                                local_addr = parts[3]
                                if ':' in local_addr:
                                    port = int(local_addr.split(':')[-1])
                                    
                                    if not show_system_ports and port < 1024:
                                        continue
                                    
                                    # Extract PID and process name
                                    pid_process = parts[6] if len(parts) > 6 else "0/-"
                                    if '/' in pid_process:
                                        pid_str, process_name = pid_process.split('/', 1)
                                        try:
                                            pid = int(pid_str)
                                        except ValueError:
                                            pid = 0
                                    else:
                                        pid = 0
                                        process_name = "unknown"
                                    
                                    port_info = PortInfo(
                                        port=port,
                                        protocol=proto,
                                        pid=pid,
                                        process_name=process_name,
                                        local_address=local_addr,
                                        remote_address=""
                                    )
                                    ports.append(port_info)
                                    
                            except (ValueError, IndexError):
                                continue
                                
        except (subprocess.TimeoutExpired, subprocess.SubprocessError, FileNotFoundError):
            logger.warning("Fallback port scanning failed")
        
        return ports
    
    def kill_process(self, pid: int, kill_method: str = "SIGTERM") -> Tuple[bool, str]:
        """Kill a process by PID"""
        try:
            if pid <= 0:
                return False, "Invalid process ID"
            
            # Check if process exists
            if not psutil.pid_exists(pid):
                return False, f"Process {pid} not found"
            
            process = psutil.Process(pid)
            process_name = process.name()
            
            # Determine signal to use
            sig = signal.SIGTERM if kill_method == "SIGTERM" else signal.SIGKILL
            
            # Kill the process
            os.kill(pid, sig)
            
            return True, f"Successfully killed {process_name} (PID: {pid})"
            
        except psutil.NoSuchProcess:
            return False, f"Process {pid} not found"
        except psutil.AccessDenied:
            return False, f"Permission denied to kill process {pid}"
        except ProcessLookupError:
            return False, f"Process {pid} not found"
        except PermissionError:
            return False, f"Permission denied to kill process {pid}"
        except Exception as e:
            return False, f"Error killing process {pid}: {str(e)}"


class PortQueryEventListener(EventListener):
    """Handles keyword queries for port listing"""
    
    def __init__(self):
        self.scanner = PortScanner()
    
    def on_event(self, event, extension):
        query = event.get_argument() or ""
        
        # Get preferences
        show_system_ports = extension.preferences.get('show_system_ports') == 'true'
        
        try:
            # Get active ports
            ports = self.scanner.get_active_ports(show_system_ports)
            
            # Filter ports based on query
            if query:
                filtered_ports = []
                query_lower = query.lower()
                
                for port in ports:
                    # Check if query matches port number, process name, or protocol
                    if (str(port.port) in query or 
                        query_lower in port.process_name.lower() or
                        query_lower in port.protocol.lower()):
                        filtered_ports.append(port)
                
                ports = filtered_ports
            
            # Limit results for performance
            ports = ports[:15]
            
            # Create result items
            items = []
            
            if not ports:
                items.append(ExtensionResultItem(
                    icon='images/icon.svg',
                    name='No active ports found',
                    description='No processes using network ports match your query',
                    on_enter=HideWindowAction()
                ))
            else:
                for port in ports:
                    name = f"Port {port.port}/{port.protocol} - {port.process_name} (PID: {port.pid})"
                    description = f"Local: {port.local_address} | Press Enter to kill process"
                    
                    # Simplified: directly kill process on selection
                    items.append(ExtensionResultItem(
                        icon='images/icon.svg',
                        name=name,
                        description=description,
                        on_enter=ExtensionCustomAction({
                            'action': 'kill_process',
                            'pid': port.pid,
                            'port': port.port,
                            'process_name': port.process_name
                        })
                    ))
            
            return RenderResultListAction(items)
            
        except Exception as e:
            logger.error(f"Error in port query: {e}")
            return RenderResultListAction([
                ExtensionResultItem(
                    icon='images/icon.svg',
                    name='Error scanning ports',
                    description=f'Failed to scan ports: {str(e)}',
                    on_enter=HideWindowAction()
                )
            ])


class PortKillEventListener(EventListener):
    """Handles process termination when user selects a port"""
    
    def __init__(self):
        self.scanner = PortScanner()
    
    def on_event(self, event, extension):
        try:
            data = event.get_data() or {}
            logger.info(f"PortKillEventListener received: {data}")

            action = data.get('action')
            
            if action == 'kill_process':
                pid = data.get('pid')
                port = data.get('port')
                process_name = data.get('process_name', 'unknown')
                kill_method = extension.preferences.get('kill_method', 'SIGTERM')
                
                logger.info(f"Killing process {process_name} (PID: {pid}) on port {port}")
                success, message = self.scanner.kill_process(pid, kill_method)
                
                if success:
                    result_item = ExtensionResultItem(
                        icon='images/icon.svg',
                        name=f'✓ Killed {process_name}',
                        description=f'Successfully terminated process on port {port}',
                        on_enter=HideWindowAction()
                    )
                else:
                    result_item = ExtensionResultItem(
                        icon='images/icon.svg',
                        name=f'✗ Failed to kill {process_name}',
                        description=f'Error: {message}',
                        on_enter=HideWindowAction()
                    )
                return RenderResultListAction([result_item])

            # Unknown action or no action - just hide
            logger.warning(f"No valid action found in data: {data}")
            return HideWindowAction()
            
        except Exception as e:
            logger.error(f"Error in PortKillEventListener: {e}")
            return RenderResultListAction([
                ExtensionResultItem(
                    icon='images/icon.svg',
                    name='Error occurred',
                    description=f'Error: {str(e)}',
                    on_enter=HideWindowAction()
                )
            ])


class PortKillerExtension(Extension):
    """Main extension class"""
    
    def __init__(self):
        super().__init__()
        self.subscribe(KeywordQueryEvent, PortQueryEventListener())
        self.subscribe(ItemEnterEvent, PortKillEventListener())


if __name__ == '__main__':
    PortKillerExtension().run()
