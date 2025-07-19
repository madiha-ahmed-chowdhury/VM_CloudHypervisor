# Cloud Hypervisor Micro VM Setup

This repository contains tools for setting up and managing lightweight virtual machines using Cloud Hypervisor, a modern VMM (Virtual Machine Monitor) designed for cloud workloads and microVMs.

## Overview

The setup includes three main components:

- **`cloud_hypervisor_setup.sh`** - Automated setup script that handles everything from installation checks to VM launch
- **`vm_config.json`** - JSON configuration file for declarative VM setup
- **`vm_controller.py`** - Python API wrapper for programmatic VM management

## What is Cloud Hypervisor?

Cloud Hypervisor is a lightweight, security-focused VMM that creates "microVMs" - minimal virtual machines optimized for:
- Fast boot times (typically under 100ms)
- Low memory overhead
- Container-like resource efficiency
- Cloud-native workloads

## Prerequisites

### System Requirements
- Linux host system with KVM support
- Root or sudo access (for some operations)
- Internet connection (for downloading kernel)

### Dependencies
```bash
# Install Cloud Hypervisor
cargo install --git https://github.com/cloud-hypervisor/cloud-hypervisor.git
# OR download from releases:
# https://github.com/cloud-hypervisor/cloud-hypervisor/releases

# For Python controller (optional)
pip install requests requests-unixsocket

# System tools
sudo apt-get install wget curl cpio gzip
```

## Quick Start - Method 1: Bash Script (Recommended)

The easiest way to get started is using the automated setup script:

```bash
# Make the script executable
chmod +x cloud_hypervisor_setup.sh

# Launch the VM (this will handle everything automatically)
./cloud_hypervisor_setup.sh
```

### What the Script Does Automatically:

1. **Checks Dependencies** - Verifies Cloud Hypervisor is installed
2. **Downloads Kernel** - Fetches a PVH-compatible kernel if not present
3. **Creates Root Filesystem** - Builds a minimal 1GB ext4 rootfs with busybox
4. **Launches VM** - Starts the microVM with optimized settings
5. **Provides API Examples** - Shows how to interact with the running VM

### Script Configuration

You can modify these variables at the top of the script:
```bash
MEMORY_SIZE="256M"    # RAM allocation
VCPUS="2"             # Number of virtual CPUs
DISK_SIZE="1G"        # Root filesystem size
```

## Method 2: JSON Configuration

For more complex setups, use the JSON configuration approach:

```bash
# Edit vm_config.json to customize your VM
# Then launch with:
cloud-hypervisor --config vm_config.json
```

The JSON config supports advanced features like:
- Network configuration with TAP interfaces
- Memory ballooning
- vSocket communication
- Multiple disk attachments

## Method 3: Python Controller

For programmatic control and automation:

```python
from vm_controller import CloudHypervisorVM

# Create and configure VM
vm = CloudHypervisorVM("my-vm")
vm.update_config(
    memory="size=512M",
    cpus="boot=4"
)

# Start VM
if vm.start():
    print("VM started!")
    
    # Manage VM lifecycle
    vm.pause()
    vm.resume()
    vm.stop()
```

## VM Management

Once your VM is running, you can interact with it through the API:

### Basic Operations
```bash
# Check VM status
curl -s --unix-socket /tmp/cloud-hypervisor-micro-vm-api.sock \
     http://localhost/api/v1/vmm.ping

# Shutdown VM
curl -s -X PUT --unix-socket /tmp/cloud-hypervisor-micro-vm-api.sock \
     http://localhost/api/v1/vm.shutdown

# Pause VM
curl -s -X PUT --unix-socket /tmp/cloud-hypervisor-micro-vm-api.sock \
     http://localhost/api/v1/vm.pause

# Resume VM
curl -s -X PUT --unix-socket /tmp/cloud-hypervisor-micro-vm-api.sock \
     http://localhost/api/v1/vm.resume
```

### Serial Console Access

The VM's serial console output appears directly in your terminal when using the script. For background operation, redirect to a log file:

```bash
./cloud_hypervisor_setup.sh > vm.log 2>&1 &
```

## Code Architecture

### cloud_hypervisor_setup.sh
This bash script provides a complete automated setup flow:

- **Dependency Checking** - Validates Cloud Hypervisor installation
- **Asset Management** - Downloads kernel and creates filesystem images
- **VM Lifecycle** - Handles startup, monitoring, and cleanup
- **Error Handling** - Comprehensive logging and error recovery
- **API Integration** - Demonstrates REST API usage for VM control

Key functions:
- `check_cloud_hypervisor()` - Validates installation
- `download_kernel()` - Fetches PVH-compatible kernel
- `create_rootfs()` - Builds minimal Linux root filesystem
- `launch_vm()` - Starts VM with optimized parameters

### vm_config.json
Declarative configuration supporting:

- **Resource Allocation** - CPU, memory, and balloon configuration
- **Storage** - Disk images with direct I/O support
- **Networking** - TAP interface with IP configuration
- **Communication** - vSocket and API socket setup
- **I/O** - Serial and console configuration

### vm_controller.py
Python wrapper providing:

- **Object-Oriented Interface** - Clean API for VM management
- **Configuration Management** - Dynamic config loading/saving
- **Lifecycle Control** - Start, stop, pause, resume operations
- **API Communication** - Unix socket-based REST API client
- **Error Handling** - Comprehensive exception management

Key classes and methods:
- `CloudHypervisorVM` - Main VM management class
- `start()/stop()` - VM lifecycle control
- `api_request()` - REST API communication
- `get_info()/ping()` - Status monitoring

## Customization

### Custom Kernel
To use your own kernel, ensure it has:
- `CONFIG_PVH=y` - PVH boot protocol support
- Required drivers for your use case

### Custom Root Filesystem
Replace the generated rootfs with your own:
```bash
# Create custom rootfs
dd if=/dev/zero of=custom-rootfs.img bs=1M count=2048
mkfs.ext4 custom-rootfs.img
# Mount and populate as needed

# Update configuration
DISK_PATH="./custom-rootfs.img"
```

### Network Configuration
For networking, the JSON config includes TAP interface setup. You'll need:
```bash
# Create TAP interface
sudo ip tuntap add tap0 mode tap
sudo ip addr add 192.168.1.1/24 dev tap0
sudo ip link set tap0 up
```

## Troubleshooting

### Common Issues

**VM fails to start:**
- Check KVM support: `ls -la /dev/kvm`
- Verify kernel compatibility
- Ensure sufficient disk space

**API socket not available:**
- Check if VM process is running
- Verify socket path permissions
- Look for port conflicts

**Boot hangs:**
- Check kernel command line parameters
- Verify root filesystem integrity
- Review serial console output

### Debug Mode
Enable verbose logging:
```bash
# For bash script
bash -x ./cloud_hypervisor_setup.sh

# For Python controller
import logging
logging.basicConfig(level=logging.DEBUG)
```

## Performance Notes

MicroVMs created with these tools typically achieve:
- **Boot time**: 50-200ms
- **Memory overhead**: ~10-20MB base
- **Startup latency**: Under 1 second for simple workloads

For production use, consider:
- Pre-built kernel images
- Optimized root filesystems
- Resource limits appropriate to workload
- Monitoring and logging setup

## Further Reading

- [Cloud Hypervisor Documentation](https://github.com/cloud-hypervisor/cloud-hypervisor)
- [PVH Boot Protocol](https://xenbits.xen.org/docs/unstable/misc/pvh.html)
- [KVM Documentation](https://www.kernel.org/doc/Documentation/virtual/kvm/)
- [MicroVM Best Practices](https://firecracker-microvm.github.io/)

## License

These scripts are provided as examples for educational and development purposes. Check individual tool licenses for production use.