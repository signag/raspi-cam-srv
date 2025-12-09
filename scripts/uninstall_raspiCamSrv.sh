#!/bin/bash
set -e

############################################
# raspiCamSrv Uninstaller
############################################
echo
echo "=========================================="
echo "=== raspiCamSrv Automated Uninstaller  ==="
echo "=========================================="

USER_NAME="$USER"
INSTALL_ROOT="$HOME/prg"
INSTALL_DIR="$INSTALL_ROOT/raspi-cam-srv"
HOSTNAME="$(hostname)"

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
fi
echo
echo "Detected OS codename: $OS_CODENAME $OS_VARIANT"
echo "Hostname            : $HOSTNAME"
echo
echo "Running as user     : $USER_NAME"
echo "Uninstalling from   : $INSTALL_DIR"

############################################
# Request confirmation
############################################
echo
read -rp "raspiCamSrv will be completely removed from $HOSTNAME. Continue? [y/N]: " UNINST_CHOICE
echo

UNINST_CHOICE=${UNINST_CHOICE,,}   # normalize to lowercase

if [[ "$UNINST_CHOICE" != "y" ]]; then
    echo
    echo "======================================="
    echo "=== raspiCamSrv uninstall cancelled ==="
    echo "======================================="
    exit
fi

############################################
# Uninstalling services
############################################
echo
echo "Uninstalling services ..."

SERVICE_FILE_SYS="/etc/systemd/system/raspiCamSrv.service"
SERVICE_FILE_USR="$HOME/.config/systemd/user/raspiCamSrv.service"
if [ -f "$SERVICE_FILE_SYS" ]; then
    sudo systemctl disable raspiCamSrv.service
    echo "raspiCamSrv system unit disabled"
    sudo systemctl stop raspiCamSrv.service
    echo "raspiCamSrv system unit stopped"
    sudo rm "$SERVICE_FILE_SYS"
    echo "Service file removed $SERVICE_FILE_SYS"
    sudo systemctl daemon-reload
elif [ -f "$SERVICE_FILE_USR" ]; then
    # Disable lingering
    sudo loginctl disable-linger "$USER_NAME"
    echo "lingering disabled for user $USER_NAME"
    systemctl --user disable raspiCamSrv.service
    echo "raspiCamSrv user unit disabled"
    systemctl --user stop raspiCamSrv.service
    echo "raspiCamSrv user unit stopped"
    rm "$SERVICE_FILE_USR"
    echo "Service file removed $SERVICE_FILE_USR"
    systemctl --user daemon-reload   
else
    echo "No raspiCamSrv service files found"
fi

############################################
# Removing installation
############################################
echo
echo "Uninstalling raspiCamSrv ..."
if [ -d "$INSTALL_DIR" ]; then
    rm -fdr "$INSTALL_DIR"
    echo "$INSTALL_DIR removed"
else
    echo "$INSTALL_DIR does not exist"
fi

############################################
# Removing Install root
############################################
echo
echo "Removing empty install root ..."
if [ -d "$INSTALL_ROOT" ]; then
    if [ -d "$INSTALL_ROOT" ] && [ -z "$(find "$INSTALL_ROOT" -mindepth 1 -print -quit)" ]; then
        rm -d "$INSTALL_ROOT"
        echo "$INSTALL_ROOT removed"
    else
        echo "$INSTALL_ROOT is not empty. Not removed"
    fi
else
    echo "$INSTALL_ROOT does not exist"
fi

############################################
# Finish
############################################
echo
echo "=========================================="
echo "=== raspiCamSrv uninstall completed    ==="
echo "=========================================="
