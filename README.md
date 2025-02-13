# Ubuntu Music Player

## Description
Ubuntu Music Player is a simple and elegant music player built with GTK3. It provides a clean interface with essential music playback functionalities.

## Features
* **Multiple Format Support**: Play MP3, WAV, FLAC, and other audio formats
* **Metadata Display**: Shows album art, track title, artist, and album info
* **Playlist Management**: Save and load playlists easily
* **Playback Controls**: 
  * Play/Pause/Stop functionality
  * Next/Previous track navigation
  * Shuffle and repeat options
  * Volume control with mute function
  * Seekable progress bar

## Requirements
* Python3
* GTK3
* GStreamer
* Additional dependencies:
  ```bash
  sudo apt-get install python3-gi python3-gi-cairo gir1.2-gtk-3.0 gir1.2-gstreamer-1.0 libcanberra-gtk-module
  ```

## Installation

1. **Download and Extract**
   * Download `UbuntuMusicPlayer.zip`
   * Extract the contents:
     ```bash
     unzip UbuntuMusicPlayer.zip
     ```

2. **Install**
   * Navigate to the extracted directory:
     ```bash
     cd UbuntuMusicPlayerApp
     ```
   * Run the installation script:
     ```bash
     sudo ./install.sh
     ```

## Usage

### Starting the App
* Find "Ubuntu Music Player" in your applications menu
* Or launch from terminal:
  ```bash
  ubuntu-music-player
  ```

### Basic Controls
* **Play/Pause**: Toggle playback
* **Next/Previous**: Skip between tracks
* **Stop**: Stop playback
* **Shuffle**: Randomize playlist
* **Repeat**: Loop playlist
* **Volume**: Adjust using slider
* **Mute**: Quick volume toggle

### Playlist Features
* Add files: Use "Open File" button
* Add folders: Use "Open Folder" button
* Save playlists: Click save button
* Load playlists: Click load button
* Remove tracks: Click remove button next to track
* Clear playlist: Use clear button

## Uninstallation
1. Navigate to the application directory:
   ```bash
   cd UbuntuMusicPlayerApp
   ```
2. Run the uninstall script:
   ```bash
   sudo ./uninstall.sh
   ```

## Troubleshooting

### Common Issues
1. **App Won't Launch**
   * Check if all dependencies are installed
   * Try launching from terminal to see error messages

2. **No Sound**
   * Verify system volume
   * Check if GStreamer is properly installed
   * Ensure audio file format is supported

3. **File Issues**
   * Check file permissions
   * Verify file format compatibility

## Contributing
Feel free to fork the project and submit pull requests for:
* Bug fixes
* New features
* Documentation improvements
* UI enhancements

## License
This project is released under the MIT License.