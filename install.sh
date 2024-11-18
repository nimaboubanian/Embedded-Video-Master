#!/bin/bash

set -e

# Parse command-line arguments
KEEP_SCRIPT=false
while [[ "$#" -gt 0 ]]; do
    case $1 in
        -k|--keep) KEEP_SCRIPT=true ;;  # Set KEEP_SCRIPT to true if -k or --keep is passed
        *) echo "Unknown parameter passed: $1"; exit 1 ;;
    esac
    shift
done

echo "Starting installation..."

# Create virtual environment with Python 3.10
echo "Creating virtual environment with Python 3.10..."
python3.10 -m venv .venv

# Activate virtual environment
source .venv/bin/activate

# Upgrade pip
echo "Upgrading pip..."
pip install --upgrade pip

# Install Python packages
echo "Installing Python packages..."
pip install -r .src/requirements.txt

# Create run.sh script
echo "Creating run.sh script..."
cat << 'EOF' > run.sh
#!/bin/bash

# Activate the virtual environment
source .venv/bin/activate

# Run the main script
python .src/main.py

# Deactivate the virtual environment (optional)
deactivate
EOF

# Make run.sh executable
chmod +x run.sh

# Display the completion message
echo ""
echo -e "\033[32mInstallation completed successfully.\033[0m"
echo ""
echo -e "\033[33mYou can now run \033[1m\033[34m./run.sh\033[0m\033[33m to start the program.\033[0m"
echo ""

# Check the KEEP_SCRIPT flag
if [ "$KEEP_SCRIPT" = true ]; then
    echo "The --keep flag is set. Skipping removal of install.sh."
else
    echo "Cleaning up installation files..."
    rm -- "$0"
fi
