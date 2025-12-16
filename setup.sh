#!/bin/bash
set -e

# Install unixODBC
sudo apt update
sudo apt install -y unixodbc unixodbc-dev curl

# Import Microsoft GPG key
curl -sSL https://packages.microsoft.com/keys/microsoft.asc | sudo gpg --dearmor -o /etc/apt/trusted.gpg.d/microsoft.gpg

# Add MS repo
sudo tee /etc/apt/sources.list.d/mssql-release.list << 'EOF'
deb [arch=amd64 signed-by=/etc/apt/trusted.gpg.d/microsoft.gpg] https://packages.microsoft.com/ubuntu/24.04/prod/ noble main
EOF

sudo apt update
sudo ACCEPT_EULA=Y apt install -y msodbcsql18

echo "All system dependencies installed!"
