#!/bin/bash
set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

log_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

log_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

log_warn() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Function to cleanup on exit
cleanup() {
    log_info "Cleaning up..."
    # Remove any temporary files if needed
}

trap cleanup EXIT

log_info "Setting up Cloud Hypervisor Micro VM..."

# Check if Cloud Hypervisor is installed
if ! command -v cloud-hypervisor &> /dev/null; then
    log_error "Cloud Hypervisor not found. Please install it first."
    exit 1
fi

CH_VERSION=$(cloud-hypervisor --version | cut -d' ' -f2)
log_info "Cloud Hypervisor found: cloud-hypervisor v${CH_VERSION}"

# Create working directory
WORK_DIR="$(pwd)/cloud-hypervisor-setup"
mkdir -p "$WORK_DIR"
cd "$WORK_DIR"

# Function to download and build kernel
build_kernel() {
    log_info "Building custom kernel with PVH support..."
    
    # Install dependencies
    log_info "Installing build dependencies..."
    apt-get update
    apt-get install -y build-essential libncurses-dev bison flex libssl-dev libelf-dev bc

    # Clone the kernel
    if [ ! -d "linux-cloud-hypervisor" ]; then
        log_info "Cloning Cloud Hypervisor kernel..."
        git clone --depth=1 https://github.com/cloud-hypervisor/linux.git linux-cloud-hypervisor
    fi

    cd linux-cloud-hypervisor

    # Configure kernel
    log_info "Configuring kernel..."
    make defconfig
    
    # Enable PVH support
    scripts/config --enable CONFIG_PVH
    scripts/config --enable CONFIG_KVM_GUEST
    scripts/config --enable CONFIG_PARAVIRT
    
    # Build kernel
    log_info "Building kernel (this may take a while)..."
    make bzImage -j$(nproc)
    
    # Copy the kernel to our working directory
    cp arch/x86/boot/bzImage ../vmlinux.bin
    log_success "Kernel built successfully: vmlinux.bin"
    
    cd ..
}

# Function to try downloading a working kernel
try_download_kernel() {
    log_info "Attempting to download a working kernel..."
    
    # Try multiple sources for a working kernel
    KERNEL_URLS=(
        "https://github.com/cloud-hypervisor/linux/releases/download/ch-6.2/vmlinux.bin"
        "https://github.com/firecracker-microvm/firecracker/releases/download/v1.4.1/vmlinux.bin"
    )
    
    for url in "${KERNEL_URLS[@]}"; do
        log_info "Trying to download from: $url"
        if wget -O vmlinux.bin "$url" 2>/dev/null; then
            log_success "Successfully downloaded kernel from $url"
            return 0
        else
            log_warn "Failed to download from $url"
        fi
    done
    
    return 1
}

# Try to download a working kernel first, otherwise build one
if ! try_download_kernel; then
    log_warn "Could not download a pre-built kernel. Building one instead..."
    build_kernel
fi

# Create a minimal rootfs if it doesn't exist
if [ ! -f "rootfs.img" ]; then
    log_info "Creating minimal rootfs..."
    
    # Create a simple rootfs with busybox
    mkdir -p rootfs_tmp
    cd rootfs_tmp
    
    # Download busybox static binary
    wget -O busybox https://busybox.net/downloads/binaries/1.35.0-x86_64-linux-musl/busybox
    chmod +x busybox
    
    # Create basic filesystem structure
    mkdir -p bin sbin etc proc sys dev
    
    # Install busybox and create symlinks
    cp busybox bin/
    for cmd in $(./busybox --list); do
        ln -sf busybox bin/$cmd 2>/dev/null || true
    done
    
    # Create init script
    cat > init << 'EOF'
#!/bin/busybox sh
/bin/busybox --install -s
mount -t proc none /proc
mount -t sysfs none /sys
mount -t devtmpfs none /dev
echo "Cloud Hypervisor VM is running!"
echo "Type 'poweroff' to shutdown the VM"
/bin/sh
EOF
    chmod +x init
    
    # Create the rootfs image
    find . | cpio -o -H newc | gzip > ../rootfs.img
    cd ..
    rm -rf rootfs_tmp
    
    log_success "Created minimal rootfs: rootfs.img"
fi

# Create a startup script
cat > start_vm.sh << 'EOF'
#!/bin/bash
echo "Starting Cloud Hypervisor VM..."
cloud-hypervisor \
    --kernel ./vmlinux.bin \
    --initramfs ./rootfs.img \
    --cmdline "console=ttyS0 reboot=k panic=1" \
    --cpus boot=1 \
    --memory size=512M \
    --serial tty \
    --console off
EOF

chmod +x start_vm.sh

log_success "Cloud Hypervisor setup complete!"
log_info "Files created in: $WORK_DIR"
log_info "- vmlinux.bin: Kernel image"
log_info "- rootfs.img: Root filesystem"
log_info "- start_vm.sh: Script to start the VM"
echo
log_info "To start the VM, run:"
echo "  cd $WORK_DIR"
echo "  ./start_vm.sh"
echo
log_info "In the VM, you can:"
echo "  - Run basic commands (ls, ps, etc.)"
echo "  - Type 'poweroff' to shutdown"
echo "  - Press Ctrl+C to exit"