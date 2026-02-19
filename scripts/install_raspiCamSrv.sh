#!/bin/bash
set -e

############################################
# raspiCamSrv Installer + systemd setup
############################################

#!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!
# For testing. 
# Server installation is skipped, but service installation is executed
TESTING=false
#!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!

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
   [[ -d /usr/share/xsessions ]]; then
    OS_VARIANT="full"
else
    OS_VARIANT="lite"
    IS_LITE=true
fi
echo
echo "Detected OS codename: $OS_CODENAME $OS_VARIANT"
echo "Hostname            : $HOSTNAME"

if [[ "$OS_VARIANT" == "lite" ]]; then
    echo "It seems that the lite variant of $OS_CODENAME is installed."
    echo "It is strongly recommended to install the full version of $OS_CODENAME!"
    echo "With the installed lite version, there may be issues running raspiCamSrv!"
    echo
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
echo
echo "Running as user     : $USER_NAME"
echo "Installing at       : $INSTALL_ROOT"

##############################################
# Check raspiCamSrv service
##############################################
SERVICE="raspiCamSrv.service"
SERVICE_CONFIGURED=false
SERVICE_RUNNING=false
SERVICE_USER=false
SERVICE_ENABLED=false

if systemctl --user cat "$SERVICE" >/dev/null 2>&1; then
    SERVICE_USER=true
    SERVICE_CONFIGURED=true

    if systemctl --user is-enabled --quiet raspiCamSrv.service; then
        SERVICE_ENABLED=true
    fi

    if systemctl --user is-active --quiet "$SERVICE"; then
        SERVICE_RUNNING=true
    fi
fi

if [[ "$SERVICE_USER" == false ]]; then
    if systemctl cat "$SERVICE" >/dev/null 2>&1; then
        SERVICE_CONFIGURED=true

        if systemctl is-enabled --quiet "$SERVICE"; then
            SERVICE_ENABLED=true
        fi

        if systemctl is-active --quiet "$SERVICE"; then
            SERVICE_RUNNING=true
        fi
    fi
fi

if [[ "$SERVICE_RUNNING" == true ]]; then
    echo
    echo "Service '$SERVICE' is already running."
    echo
    echo "If you continue, the existing service will be stopped and replaced."
else
    if [[ "$SERVICE_CONFIGURED" == true ]]; then
        echo
        echo "Service '$SERVICE' is already configured but not running."
        echo
        echo "If you continue, the existing service will be replaced."
    fi
fi
if [[ "$SERVICE_CONFIGURED" == true ]]; then
    echo
    read -rp "Do you want to continue with the installation? [Y/n]: " CONTINUE_CHOICE
    CONTINUE_CHOICE=${CONTINUE_CHOICE,,}   # normalize to lowercase
    if [[ "$CONTINUE_CHOICE" == "n" ]]; then
        echo
        echo "======================================="
        echo "=== raspiCamSrv not installed       ==="
        echo "======================================="
        exit 1
    fi
fi

############################################
# Stop a running service before proceeding
############################################
if [[ "$SERVICE_RUNNING" == true ]]; then
    echo
    echo "Stopping running service '$SERVICE'..."
    if [[ "$SERVICE_USER" == true ]]; then
        systemctl --user stop "$SERVICE"
        if systemctl --user is-active --quiet "$SERVICE"; then
            echo
            echo "Failed to stop user service '$SERVICE'." 
            echo "Please check the service status and stop it manually before running the installer again."
            exit 1
        else
            echo
            echo "User service '$SERVICE' stopped successfully."
        fi
    else
        sudo systemctl stop "$SERVICE"
        if systemctl is-active --quiet "$SERVICE"; then
            echo
            echo "Failed to stop system service '$SERVICE'." 
            echo "Please check the service status and stop it manually before running the installer again."
            exit 1
        else
            echo
            echo "System service '$SERVICE' stopped successfully."
        fi
    fi
fi

############################################
# Ask user about defaults
############################################
echo
echo "======================"
echo "Installation Defaults:"
echo "======================"
echo "Installation Root : $INSTALL_ROOT/raspi-cam-srv"
echo "WSGI Server       : Gunicorn"
echo "Gunicorn Threads  : 6"
if [[ "$SERVICE_USER" == true ]]; then
    echo "Audio Recording   : Enabled (Installing user service)"
else
    echo "Audio Recording   : Disabled (Installing system service)"
fi
echo "AI Camera Support : Disabled"
echo
read -rp "Do you want to install with these settings? [Y/n]: " INSTALL_CHOICE
echo

INSTALL_CHOICE=${INSTALL_CHOICE,,}   # normalize to lowercase

if [[ "$INSTALL_CHOICE" == "n" ]]; then
    USE_DEFAULTS=false
else
    USE_DEFAULTS=true
fi

############################################
# Ask user about WSGI server choice
############################################
if [[ "$USE_DEFAULTS" == false ]]; then
    echo
    echo "Available WSGI servers:"
    echo "1) Gunicorn (recommended for publicly accessible systems) - default"
    echo "2) Flask built-in server (OK for testing and private networks)"
    read -rp "Choose WSGI server [1/2]: " WSGI_CHOICE
    echo

    WSGI_CHOICE=${WSGI_CHOICE,,}   # normalize to lowercase

    if [[ "$WSGI_CHOICE" == "2" ]]; then
        WSGI_SERVER="werkzeug"
    else
        WSGI_SERVER="gunicorn"
    fi
    echo "Using WSGI server: $WSGI_SERVER"
else
    WSGI_SERVER="gunicorn"
fi

############################################
# Ask user about number of threads for Gunicorn
############################################
if [[ "$WSGI_SERVER" == "gunicorn" ]]; then
    if [[ "$USE_DEFAULTS" == false ]]; then
        echo
        read -rp "How many parallel video streams do you require? [default: 6]: " THREAD_CHOICE
        echo

        THREAD_CHOICE=${THREAD_CHOICE,,}   # normalize to lowercase

        if [[ "$THREAD_CHOICE" == "" ]]; then
            THREAD_COUNT=6
        else
            if [[ "$THREAD_CHOICE" =~ ^-?[0-9]+$ ]]; then
                THREAD_COUNT=$THREAD_CHOICE
            else
                THREAD_COUNT=6
            fi
        fi
        echo "Using $THREAD_COUNT threads for Gunicorn worker process"
    else
        THREAD_COUNT=6
    fi
else
    THREAD_COUNT=1
fi

############################################
# Ask user about audio recording
############################################
if [[ "$USE_DEFAULTS" == false ]]; then
    echo
    read -rp "Do you need to record audio along with videos? [y/N]: " AUDIO_CHOICE
    echo

    AUDIO_CHOICE=${AUDIO_CHOICE,,}   # normalize to lowercase

    if [[ "$AUDIO_CHOICE" == "y" ]]; then
        ENABLE_AUDIO=true
    else
        ENABLE_AUDIO=false
    fi
    echo "Audio recording enabled: $ENABLE_AUDIO"
else
    ENABLE_AUDIO=false
fi

############################################
# Ask user about imx500 Camera support
############################################
if [[ "$OS_CODENAME" != "bullseye" ]]; then
    if [[ "$USE_DEFAULTS" == false ]]; then
        echo
        read -rp "Do you intend to use the Raspberry Pi AI Camera (imx500)? [y/N]: " AI_CHOICE
        echo

        AI_CHOICE=${AI_CHOICE,,}   # normalize to lowercase

        if [[ "$AI_CHOICE" == "y" ]]; then
            ENABLE_AI=true
        else
            ENABLE_AI=false
        fi
        echo "AI Camera support enabled: $ENABLE_AI"
    else
        ENABLE_AI=false
    fi
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
if [[ -d "$INSTALL_ROOT" ]]; then
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

#!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!
if [[ "$TESTING" == false ]]; then
echo "Skipping install sections for testing"
#!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!


############################################
# Clone repository
############################################
echo
if [[ ! -d "raspi-cam-srv" ]]; then
    echo "Step 6: Cloning raspi-cam-srv ..."
    git clone --branch main --single-branch --depth 1 "$REPO_URL"
else
    echo "Step 6: Repository already exists — updating ..."
    cd raspi-cam-srv
    git fetch origin main --depth=1
    git reset --hard origin/main
    cd ..
fi

############################################
# Python virtual environment
############################################
echo
echo "Step 7: Creating virtual environment ..."
cd raspi-cam-srv
if [[ -d ".venv" ]]; then
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
if [[ "$OS_CODENAME" != "bullseye" ]]; then
    sudo apt-get install -y python3-opencv
else
    echo "OpenCV not installed"
fi

echo 
echo "Step 11.2: Installing numpy ..."
pip install --ignore-installed numpy

echo 
echo "Step 11.3: Installing matplotlib ..."
if [[ "$OS_CODENAME" != "bullseye" ]]; then
    if [[ "$OS_CODENAME" == "bookworm" ]]; then
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

if [[ "$IS_LITE" == true ]]; then
    echo 
    echo "Step 11.5: Installing psutil ..."
    pip install --ignore-installed psutil
fi

if [[ "$ENABLE_AI" == true ]]; then
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

if [[ "$ENABLE_AI" == true ]]; then
    echo 
    echo "Step 11.7: Installing munkres ..."
    pip install --break-system-packages munkres
fi

if [[ "$WSGI_SERVER" == "gunicorn" ]]; then
    echo 
    echo "Step 11.8: Installing gunicorn ..."
    pip install --break-system-packages gunicorn
fi

############################################
# Initialize database
############################################
echo
echo "Step 12: Initializing database ..."
if [[ -f "$INSTALL_ROOT/raspi-cam-srv/instance/raspiCamSrv.sqlite" ]]; then
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

#!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!
fi
#!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!

############################################
# Checking port
############################################
echo
echo "Step 13: Checking Flask service port ..."

ok=false
while [[ "$ok" != true ]]; do
    echo "Trying port $SERVICE_PORT ..."
    if ss -tulpn | grep -q ":$SERVICE_PORT\b"; then
        SERVICE_PORT=$((SERVICE_PORT + 1))
    else
        ok=true
    fi
done
echo "Using port $SERVICE_PORT"

############################################
# Cleanup existing services
############################################
if [[ "$SERVICE_CONFIGURED" == true ]]; then
    echo
    echo "Cleaning up existing service before reinstalling ..."
fi

if [[ "$SERVICE_USER" == true ]]; then
    if [[ "$SERVICE_ENABLED" == true ]]; then
        systemctl --user disable "$SERVICE" >/dev/null 2>&1
        echo "User service '$SERVICE' disabled."
    fi
    if [[ "$SERVICE_CONFIGURED" == true ]]; then
        SERVICE_FILE="$HOME/.config/systemd/user/raspiCamSrv.service"
        rm "$SERVICE_FILE"
        echo "User service '$SERVICE' configuration removed."
    fi
fi

if [[ "$SERVICE_USER" == false ]]; then
    if [[ "$SERVICE_ENABLED" == true ]]; then
        sudo systemctl disable "$SERVICE" >/dev/null 2>&1
        echo "System service '$SERVICE' disabled."
    fi
    if [[ "$SERVICE_CONFIGURED" == true ]]; then
        SERVICE_FILE="/etc/systemd/system/raspiCamSrv.service"
        sudo rm "$SERVICE_FILE"
        echo "System service '$SERVICE' configuration removed."
    fi
fi

############################################
# Systemd System Unit No Audio / werkzeug
############################################
echo
if [[ "$ENABLE_AUDIO" == false && "$WSGI_SERVER" == "werkzeug" ]]; then
    echo
    echo "Installing '$SERVICE' as system service for WSGI Server werkzeug ..."

    SERVICE_FILE="/etc/systemd/system/raspiCamSrv.service"

    if [[ -f "$SERVICE_FILE" ]]; then
        sudo rm "$SERVICE_FILE"
        echo "Existing service file removed: $SERVICE_FILE"
    fi
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
    sudo systemctl enable raspiCamSrv.service >/dev/null 2>&1
    sudo systemctl start raspiCamSrv.service

    echo "System service '$SERVICE' installed and started."
fi

############################################
# Systemd System Unit No Audio / gunicorn
############################################
if [[ "$ENABLE_AUDIO" == false && "$WSGI_SERVER" == "gunicorn" ]]; then
    echo
    echo "Installing '$SERVICE' as system service for WSGI Server gunicorn ..."

    SERVICE_FILE="/etc/systemd/system/raspiCamSrv.service"

    if [[ -f "$SERVICE_FILE" ]]; then
        sudo rm "$SERVICE_FILE"
        echo "Existing service file removed: $SERVICE_FILE"
    fi
    sudo tee "$SERVICE_FILE" >/dev/null <<EOF
[Unit]
Description=raspiCamSrv
After=network.target

[Service]
ExecStart=$INSTALL_ROOT/raspi-cam-srv/.venv/bin/gunicorn -b 0.0.0.0:$SERVICE_PORT -w 1 -k gthread --threads $THREAD_COUNT --timeout 0 --log-level info 'raspiCamSrv:create_app()'
Environment="PATH=$INSTALL_ROOT/raspi-cam-srv/.venv/bin:/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin"
Environment="GUNICORN_THREADS=$THREAD_COUNT"
WorkingDirectory=$INSTALL_ROOT/raspi-cam-srv
StandardOutput=inherit
StandardError=inherit
Restart=always
User=$USER_NAME

[Install]
WantedBy=multi-user.target
EOF

    sudo systemctl daemon-reload
    sudo systemctl enable raspiCamSrv.service >/dev/null 2>&1
    sudo systemctl start raspiCamSrv.service

    echo "System service '$SERVICE' installed and started."
fi

############################################
# Systemd User Unit Audio / werkzeug
############################################
if [[ "$ENABLE_AUDIO" == true && "$WSGI_SERVER" == "werkzeug" ]]; then
    echo "Installing '$SERVICE' as user unit for WSGI Server werkzeug ..."

    mkdir -p "$HOME/.config/systemd/user"
    SERVICE_FILE="$HOME/.config/systemd/user/raspiCamSrv.service"

    if [[ -f "$SERVICE_FILE" ]]; then
        rm "$SERVICE_FILE"
        echo "Existing service file removed: $SERVICE_FILE"
    fi
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

    systemctl --user enable raspiCamSrv.service >/dev/null 2>&1
    systemctl --user start raspiCamSrv.service

    echo "User service installed and started."
fi

############################################
# Systemd User Unit Audio / gunicorn
############################################
if [[ "$ENABLE_AUDIO" == true && "$WSGI_SERVER" == "gunicorn" ]]; then
    echo "Installing '$SERVICE' as user unit for WSGI Server gunicorn ..."

    mkdir -p "$HOME/.config/systemd/user"
    SERVICE_FILE="$HOME/.config/systemd/user/raspiCamSrv.service"

    if [[ -f "$SERVICE_FILE" ]]; then
        rm "$SERVICE_FILE"
        echo "Existing service file removed: $SERVICE_FILE"
    fi
    tee "$SERVICE_FILE" >/dev/null <<EOF
[Unit]
Description=raspiCamSrv
After=network.target

[Service]
ExecStart=$INSTALL_ROOT/raspi-cam-srv/.venv/bin/gunicorn -b 0.0.0.0:$SERVICE_PORT -w 1 -k gthread --threads $THREAD_COUNT --timeout 0 --log-level info 'raspiCamSrv:create_app()'
Environment="PATH=$INSTALL_ROOT/raspi-cam-srv/.venv/bin:/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin"
Environment="GUNICORN_THREADS=$THREAD_COUNT"
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

    systemctl --user enable raspiCamSrv.service >/dev/null 2>&1
    systemctl --user start raspiCamSrv.service

    echo "User service installed and started."
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
