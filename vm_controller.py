#!/usr/bin/env python3
"""
Cloud Hypervisor Micro VM Controller
Programmatic interface for managing Cloud Hypervisor VMs
"""

import json
import os
import subprocess
import time
import requests
import requests_unixsocket
from pathlib import Path
import logging

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class CloudHypervisorVM:
    def __init__(self, vm_name="micro-vm", config_path=None):
        self.vm_name = vm_name
        self.config_path = config_path or f"/tmp/{vm_name}-config.json"
        self.api_socket = f"/tmp/{vm_name}-api.sock"
        self.process = None
        self.session = requests_unixsocket.Session()
        
        # Default configuration
        self.config = {
            "kernel": "./vmlinux",
            "disk": [{"path": "./rootfs.img"}],
            "cmdline": "console=hvc0 root=/dev/vda rw init=/init",
            "cpus": "boot=2",
            "memory": "size=256M",
            "serial": "tty",
            "console": "off",
            "api-socket": self.api_socket
        }
    
    def update_config(self, **kwargs):
        """Update VM configuration"""
        self.config.update(kwargs)
        logger.info(f"Updated configuration: {kwargs}")
    
    def save_config(self):
        """Save configuration to file"""
        with open(self.config_path, 'w') as f:
            json.dump(self.config, f, indent=2)
        logger.info(f"Configuration saved to {self.config_path}")
    
    def load_config(self):
        """Load configuration from file"""
        if Path(self.config_path).exists():
            with open(self.config_path, 'r') as f:
                self.config = json.load(f)
            logger.info(f"Configuration loaded from {self.config_path}")
        else:
            logger.warning(f"Config file {self.config_path} not found, using defaults")
    
    def build_command(self):
        """Build cloud-hypervisor command from configuration"""
        cmd = ["cloud-hypervisor"]
        
        for key, value in self.config.items():
            if key == "disk" and isinstance(value, list):
                for disk in value:
                    if isinstance(disk, dict):
                        disk_str = ",".join([f"{k}={v}" for k, v in disk.items()])
                        cmd.extend([f"--{key}", disk_str])
                    else:
                        cmd.extend([f"--{key}", str(disk)])
            else:
                cmd.extend([f"--{key}", str(value)])
        
        return cmd
    
    def start(self):
        """Start the VM"""
        if self.process and self.process.poll() is None:
            logger.warning("VM is already running")
            return
        
        # Clean up old socket
        if os.path.exists(self.api_socket):
            os.remove(self.api_socket)
        
        cmd = self.build_command()
        logger.info(f"Starting VM with command: {' '.join(cmd)}")
        
        try:
            self.process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True
            )
            
            # Wait for API socket to be available
            timeout = 10
            start_time = time.time()
            while not os.path.exists(self.api_socket) and time.time() - start_time < timeout:
                time.sleep(0.1)
            
            if os.path.exists(self.api_socket):
                logger.info(f"VM started successfully with PID: {self.process.pid}")
                return True
            else:
                logger.error("VM failed to start - API socket not available")
                return False
                
        except Exception as e:
            logger.error(f"Failed to start VM: {e}")
            return False
    
    def stop(self):
        """Stop the VM"""
        if self.process:
            try:
                self.api_request("PUT", "/api/v1/vm.shutdown")
                self.process.wait(timeout=10)
                logger.info("VM stopped gracefully")
            except:
                logger.warning("Graceful shutdown failed, forcing termination")
                self.process.terminate()
                self.process.wait()
            finally:
                self.process = None
    
    def pause(self):
        """Pause the VM"""
        return self.api_request("PUT", "/api/v1/vm.pause")
    
    def resume(self):
        """Resume the VM"""
        return self.api_request("PUT", "/api/v1/vm.resume")
    
    def reboot(self):
        """Reboot the VM"""
        return self.api_request("PUT", "/api/v1/vm.reboot")
    
    def get_info(self):
        """Get VM information"""
        return self.api_request("GET", "/api/v1/vm.info")
    
    def ping(self):
        """Ping the VMM"""
        return self.api_request("GET", "/api/v1/vmm.ping")
    
    def api_request(self, method, endpoint, data=None):
        """Make API request to Cloud Hypervisor"""
        if not os.path.exists(self.api_socket):
            logger.error("API socket not available")
            return None
        
        url = f"http+unix://{self.api_socket.replace('/', '%2F')}{endpoint}"
        
        try:
            if method == "GET":
                response = self.session.get(url)
            elif method == "PUT":
                response = self.session.put(url, json=data)
            elif method == "POST":
                response = self.session.post(url, json=data)
            else:
                logger.error(f"Unsupported method: {method}")
                return None
            
            if response.status_code == 200:
                try:
                    return response.json()
                except:
                    return response.text
            else:
                logger.error(f"API request failed: {response.status_code} - {response.text}")
                return None
                
        except Exception as e:
            logger.error(f"API request error: {e}")
            return None
    
    def is_running(self):
        """Check if VM is running"""
        if not self.process:
            return False
        
        if self.process.poll() is not None:
            return False
        
        # Also check via API
        ping_result = self.ping()
        return ping_result is not None
    
    def get_logs(self):
        """Get VM logs"""
        if self.process:
            stdout, stderr = self.process.communicate(timeout=1)
            return {"stdout": stdout, "stderr": stderr}
        return None

def main():
    """Example usage"""
    vm = CloudHypervisorVM("test-vm")
    
    # Configure VM
    vm.update_config(
        memory="size=512M",
        cpus="boot=2,max=4"
    )
    
    # Start VM
    if vm.start():
        print("VM started successfully")
        
        # Wait a moment
        time.sleep(2)
        
        # Check status
        if vm.is_running():
            print("VM is running")
            
            # Get info
            info = vm.get_info()
            if info:
                print(f"VM info: {json.dumps(info, indent=2)}")
            
            # Pause and resume
            print("Pausing VM...")
            vm.pause()
            time.sleep(2)
            
            print("Resuming VM...")
            vm.resume()
            time.sleep(2)
        
        # Stop VM
        print("Stopping VM...")
        vm.stop()
    else:
        print("Failed to start VM")

if __name__ == "__main__":
    main()