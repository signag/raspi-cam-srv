#!/bin/bash
set -e

############################################
# raspiCamSrv Installer + systemd setup
############################################
echo
echo "=========================================="
echo "=== raspiCamSrv Automated Installer    ==="
echo "=========================================="

USER_NAME="$USER"
INSTALL_ROOT="$HOME/prg"
REPO_URL="https://github.com/signag/raspi-cam-srv.git"
SERVICE_PORT=5000
HOSTNAME="$(hostname)"
IS_LITE=false

##############################################
# Detect OS version and check for full version
##############################################
OS_CODENAME=$(grep VERSION_CODENAME /etc/os-release | cut -d= -f2)

if dpkg -l | grep -q raspberrypi-ui-mods || \
   dpkg -l | grep -q lxsession || \
   [ -d /usr/share/xsessions ]; then
    OS_VARIANT="full"
else
    OS_VARIANT="lite"
    IS_LITE=true
fi
echo
echo "Detected OS codename: $OS_CODENAME $OS_VARIANT"
echo "Hostname            : $HOSTNAME"

if [ "$OS_VARIANT" == "lite" ]; then
    echo "It seems that the lite variant of $OS_CODENAME is installed."
    echo "It is strongly recommended to install the full version of $OS_CODENAME!"
    echo "With the installed lite version, there may be issues running raspiCamSrv!"
    read -rp "Do you want to continue with the installation, nevertheless? [y/N]: " INSTALL_CHOICE
    INSTALL_CHOICE=${INSTALL_CHOICE,,}   # normalize to lowercase
    if [[ "$INSTALL_CHOICE" == "y" ]]; then
        DO_INSTALL=true
    else
        echo
        echo "======================================="
        echo "=== raspiCamSrv not installed       ==="
        echo "======================================="
        exit 1
    fi
fi

############################################
# Ask user about audio recording
############################################
echo
echo "Running as user: $USER_NAME"
echo "Installing at  : $INSTALL_ROOT"
echo
read -rp "Do you need to record audio along with videos? [y/N]: " AUDIO_CHOICE
echo

AUDIO_CHOICE=${AUDIO_CHOICE,,}   # normalize to lowercase

if [[ "$AUDIO_CHOICE" == "y" ]]; then
    ENABLE_AUDIO=true
else
    ENABLE_AUDIO=false
fi

############################################
# Ask user about imx500 Camera support
############################################
echo
read -rp "Do you intend to use the Raspberry Pi AI Camera (imx500)? [y/N]: " AI_CHOICE
echo

AI_CHOICE=${AI_CHOICE,,}   # normalize to lowercase

if [[ "$AI_CHOICE" == "y" ]]; then
    ENABLE_AI=true
else
    ENABLE_AI=false
fi

############################################
# Check that ffmpeg is installed
############################################
echo
echo "Step 3: Checking ffmpeg ..."
if command -v ffmpeg >/dev/null 2>&1; then
    echo "ffmpeg is installed"
else
    echo "Installing ffmpeg"
    sudo apt install -y ffmpeg    
fi

############################################
# Create root directory
############################################
echo
echo "Step 4: Creating root directory ..."
if [ -d "$INSTALL_ROOT" ]; then
    echo "Root directory exists already: $INSTALL_ROOT"
else
    mkdir -p "$INSTALL_ROOT"
    echo "Created: $INSTALL_ROOT"
fi
cd "$INSTALL_ROOT"

############################################
# Check that git is installed
############################################
echo
echo "Step 5: Checking git ..."
if command -v git >/dev/null 2>&1; then
    echo "git is installed"
else
    echo "Installing git ..."
    sudo apt install -y git
fi

############################################
# Clone repository
############################################
echo
if [ ! -d "raspi-cam-srv" ]; then
    echo "Step 6: Cloning raspi-cam-srv ..."
    git clone --branch main --single-branch --depth 1 "$REPO_URL"
else
    echo "Step 6: Repository already exists — updating ..."
    cd raspi-cam-srv
    git pull origin main
    cd ..
fi

############################################
# Python virtual environment
############################################
echo
echo "Step 7: Creating virtual environment ..."
cd raspi-cam-srv
if [ -d ".venv" ]; then
    echo "Virtual environment exists already"
else
    python3 -m venv --system-site-packages .venv
    echo "Created: .venv"
fi

############################################
# Activate virtual environment
############################################
echo
echo "Step 8: Activating virtual environment ..."
source .venv/bin/activate
echo "Virtual environment activated"
echo "$PS1"

############################################
# Check that Picamera2 is installed
############################################
echo
echo "Step 9: Checking Picamera2 ..."
if python3 -c "import picamera2" 2>/dev/null; then
    echo "Picamera2 is installed"
else
    echo
    echo "Installing Picamera2 ..."
    if [[ "$OS_CODENAME" == "bullseye" ]]; then
        sudo apt install -y python3-picamera2 --no-install-recommends
    fi
    if [[ "$OS_CODENAME" == "bookworm" ]]; then
        sudo apt install -y python3-picamera2 --no-install-recommends
    fi
    if [[ "$OS_CODENAME" == "trixie" ]]; then
        sudo apt install -y python3-libcamera python3-picamera2 --no-install-recommends
    fi
fi

############################################
# Install Flask
############################################
echo
echo "Step 10: Installing Flask ..."
pip install --ignore-installed "Flask>=3,<4"

############################################
# Optional installations
############################################
echo 
echo "Step 11.1: Installing OpenCV ..."
if [ "$OS_CODENAME" != "bullseye" ]; then
    sudo apt-get install -y python3-opencv
else
    echo "OpenCV not installed"
fi

echo 
echo "Step 11.2: Installing numpy ..."
pip install --ignore-installed numpy

echo 
echo "Step 11.3: Installing matplotlib ..."
if [ "$OS_CODENAME" != "bullseye" ]; then
    if [ "$OS_CODENAME" == "bookworm" ]; then
        pip install --ignore-installed "matplotlib<3.8"
    else
        pip install --ignore-installed matplotlib
    fi
else
    echo "matplotlib not installed for bullseye system"
fi

echo 
echo "Step 11.4: Installing flask-jwt-extended ..."
pip install --ignore-installed flask-jwt-extended

if [ "$IS_LITE" = true ]; then
    echo 
    echo "Step 11.5: Installing psutil ..."
    pip install --ignore-installed psutil
fi

if [ "$ENABLE_AI" = true ]; then
    echo 
    PACKAGE="imx500-all"
    echo "Step 11.6: Installing $PACKAGE ..."

    if dpkg -s "$PACKAGE" >/dev/null 2>&1; then
        echo "Package '$PACKAGE' is already installed."
    else
        echo "Package '$PACKAGE' is not installed. Installing..."
        sudo apt update
        sudo apt install -y "$PACKAGE"
    fi
fi

if [ "$ENABLE_AI" = true ]; then
    echo 
    echo "Step 11.7: Installing munkres ..."
    pip install --break-system-packages munkres
fi

############################################
# Initialize database
############################################
echo
echo "Step 12: Initializing database ..."
if [ -f "$INSTALL_ROOT/raspi-cam-srv/instance/raspiCamSrv.sqlite" ]; then
    echo "Existing database found. Initialization skipped."
    echo "If you need to reset the database, activate the virtual environment and run"
    echo "python3 -m flask --app raspiCamSrv init-db"
else
    python3 -m flask --app raspiCamSrv init-db
fi

############################################
# Leaving venv
############################################
echo
deactivate
echo "Virtual environment deactivated"
echo "$PS1"

############################################
# Checking port
############################################
echo
echo "Step 13: Checking Flask service port ..."

SERVICE_FILE_SYS="/etc/systemd/system/raspiCamSrv.service"
SERVICE_FILE_USR="$HOME/.config/systemd/user/raspiCamSrv.service"
if [[ -f "$SERVICE_FILE_SYS" || -f "$SERVICE_FILE_USR" ]]; then
    echo "Service already configured. Port search skipped."
else
    ok=false
    while [ "$ok" != true ]; do
        echo "Trying port $SERVICE_PORT ..."
        if ss -tulpn | grep -q ":$SERVICE_PORT\b"; then
            SERVICE_PORT=$((SERVICE_PORT + 1))
        else
            ok=true
        fi
    done
fi
echo "Using port $SERVICE_PORT"

############################################
# Systemd System Unit
############################################
echo
if [[ "$ENABLE_AUDIO" == false ]]; then
    echo "Installing service as system unit ..."

    SERVICE_FILE="/etc/systemd/system/raspiCamSrv.service"

    if [ -f "$SERVICE_FILE" ]; then
        echo "Service file exists already: $SERVICE_FILE"
        echo "Skipping service installation."
    else
        sudo tee "$SERVICE_FILE" >/dev/null <<EOF
[Unit]
Description=raspiCamSrv
After=network.target

[Service]
ExecStart=$INSTALL_ROOT/raspi-cam-srv/.venv/bin/python -m flask --app raspiCamSrv run --port=$SERVICE_PORT --host=0.0.0.0
Environment="PATH=$INSTALL_ROOT/raspi-cam-srv/.venv/bin:/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin"
WorkingDirectory=$INSTALL_ROOT/raspi-cam-srv
StandardOutput=inherit
StandardError=inherit
Restart=always
User=$USER_NAME

[Install]
WantedBy=multi-user.target
EOF

        sudo systemctl daemon-reload
        sudo systemctl enable raspiCamSrv.service
        sudo systemctl start raspiCamSrv.service

        echo "System service installed and started."
    fi
fi
if [[ "$ENABLE_AUDIO" == true ]]; then
    echo "Installing service as user unit ..."

    mkdir -p "$HOME/.config/systemd/user"
    SERVICE_FILE="$HOME/.config/systemd/user/raspiCamSrv.service"

    if [ -f "$SERVICE_FILE" ]; then
        echo "Service file exists already: $SERVICE_FILE"
        echo "Skipping service installation."
    else
        tee "$SERVICE_FILE" >/dev/null <<EOF
[Unit]
Description=raspiCamSrv
After=network.target

[Service]
ExecStart=$INSTALL_ROOT/raspi-cam-srv/.venv/bin/python -m flask --app raspiCamSrv run --port=$SERVICE_PORT --host=0.0.0.0
Environment="PATH=$INSTALL_ROOT/raspi-cam-srv/.venv/bin:/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin"
WorkingDirectory=$INSTALL_ROOT/raspi-cam-srv
StandardOutput=inherit
StandardError=inherit
Restart=always

[Install]
WantedBy=default.target
EOF
        systemctl --user daemon-reload

        # Enable lingering so the user service can run without login
        sudo loginctl enable-linger "$USER_NAME"

        systemctl --user enable raspiCamSrv.service
        systemctl --user start raspiCamSrv.service

        echo "User service installed and started."
    fi
fi

############################################
# Finish
############################################
echo
echo "=========================================="
echo "=== raspiCamSrv installation completed ==="
echo "===                                    ==="
echo "=== Access via http://$HOSTNAME:$SERVICE_PORT"
echo "=========================================="
