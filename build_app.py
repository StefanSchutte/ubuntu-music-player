import PyInstaller.__main__
import os
import shutil

# Create dist directory if it doesn't exist
if not os.path.exists('dist'):
    os.makedirs('dist')

# Create the executable using PyInstaller with modified options
PyInstaller.__main__.run([
    'main.py',
    '--name=UbuntuMusicPlayer',
    '--onefile',
    '--windowed',
    '--add-data=share/icons:share/icons',
    '--hidden-import=gi',
    '--hidden-import=gi.repository.Gtk',
    '--hidden-import=gi.repository.Gst',
    '--hidden-import=gi.repository.GLib',
    '--hidden-import=gi.repository.GObject',
    '--hidden-import=gi.repository.GdkPixbuf',
])

# Create application directory structure
dist_dir = 'dist'
app_dir = os.path.join(dist_dir, 'UbuntuMusicPlayerApp')
if os.path.exists(app_dir):
    shutil.rmtree(app_dir)
os.makedirs(app_dir)

# Copy the executable
shutil.copy2(os.path.join(dist_dir, 'UbuntuMusicPlayer'), app_dir)

# Copy desktop file and icon
os.makedirs(os.path.join(app_dir, 'share/applications'), exist_ok=True)
os.makedirs(os.path.join(app_dir, 'share/icons/hicolor/256x256/apps'), exist_ok=True)

shutil.copy2('share/applications/ubuntu-music-player.desktop',
            os.path.join(app_dir, 'share/applications'))
shutil.copy2('share/icons/hicolor/256x256/apps/ubuntu-music-player.png',
            os.path.join(app_dir, 'share/icons/hicolor/256x256/apps'))

# Create install script with updated paths
with open(os.path.join(app_dir, 'install.sh'), 'w') as f:
    f.write('''#!/bin/bash
# Install required dependencies
sudo apt-get install -y python3-gi python3-gi-cairo gir1.2-gtk-3.0 gir1.2-gstreamer-1.0

# Create necessary directories
sudo mkdir -p /opt/ubuntu-music-player
# Copy application files
sudo cp UbuntuMusicPlayer /opt/ubuntu-music-player/
sudo chmod +x /opt/ubuntu-music-player/UbuntuMusicPlayer
# Create launcher script
echo '#!/bin/bash
/opt/ubuntu-music-player/UbuntuMusicPlayer "$@"' | sudo tee /usr/local/bin/ubuntu-music-player
sudo chmod +x /usr/local/bin/ubuntu-music-player
# Install desktop file and icon
sudo cp share/applications/ubuntu-music-player.desktop /usr/share/applications/
sudo cp share/icons/hicolor/256x256/apps/ubuntu-music-player.png /usr/share/icons/hicolor/256x256/apps/
sudo sed -i 's|Exec=.*|Exec=/usr/local/bin/ubuntu-music-player|g' /usr/share/applications/ubuntu-music-player.desktop
sudo gtk-update-icon-cache /usr/share/icons/hicolor/
sudo update-desktop-database
''')

# Make install script executable
os.chmod(os.path.join(app_dir, 'install.sh'), 0o755)

# Create uninstall script
with open(os.path.join(app_dir, 'uninstall.sh'), 'w') as f:
    f.write('''#!/bin/bash
sudo rm -rf /opt/ubuntu-music-player
sudo rm /usr/local/bin/ubuntu-music-player
sudo rm /usr/share/applications/ubuntu-music-player.desktop
sudo rm /usr/share/icons/hicolor/256x256/apps/ubuntu-music-player.png
sudo gtk-update-icon-cache /usr/share/icons/hicolor/
sudo update-desktop-database
''')

# Make uninstall script executable
os.chmod(os.path.join(app_dir, 'uninstall.sh'), 0o755)

# Create a README file
with open(os.path.join(app_dir, 'README.txt'), 'w') as f:
    f.write('''Ubuntu Music Player
==================

Installation:
1. Extract this archive
2. Open a terminal in this directory
3. Run: ./install.sh

To uninstall:
1. Open a terminal in this directory
2. Run: ./uninstall.sh

Requirements:
The install script will automatically install these dependencies:
- Python3-GI
- GTK 3
- GStreamer
''')

# Create zip archive
shutil.make_archive('UbuntuMusicPlayer', 'zip', dist_dir, 'UbuntuMusicPlayerApp')