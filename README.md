# 🎵 Spotify Smart Downloader

A powerful, cross-platform Spotify downloader that allows you to download tracks, albums, and playlists directly to your device with metadata and album art.

![Status](https://img.shields.io/badge/Status-Active-brightgreen)
![Version](https://img.shields.io/badge/Version-1.0.0-blue)
![Platform](https://img.shields.io/badge/Platforms-macOS%20%7C%20Windows-lightgrey)

## ✨ Features

- **High-Quality Downloads**: Automatically searches for the best available audio source.
- **Full Metadata**: Includes artist, album, year, and high-resolution album art.
- **Queue Management**: Efficiently handle multiple downloads simultaneously.
- **Cross-Platform**: Built with Flutter and Python for a seamless experience on macOS and Windows.
- **Smart Scraper**: Uses an advanced Selenium-based scraper to ensure reliable downloads.

## 🛠️ Prerequisites

> [!IMPORTANT]
> **Google Chrome is REQUIRED.**
> The downloader uses a web-based scraper that requires a local installation of Google Chrome to function correctly. Please ensure it is installed before running the application.

- **Python 3.8+** (for the backend)
- **Flutter SDK** (for the frontend/UI)
- **FFmpeg** (automatically bundled in releases, but needed for development)

## 🚀 Getting Started

### Development Mode

1. **Clone the Repository**
   ```bash
   git clone https://github.com/skhahehe/spotify-downloader.git
   cd spotify-downloader
   ```

2. **Windows Run**
   Double-click `run.bat` or execute it in CMD:
   ```cmd
   run.bat
   ```

3. **macOS/Linux Run**
   Execute the shell script:
   ```bash
   chmod +x run.sh
   ./run.sh
   ```

### Building for Production

#### Windows
To create a standalone portable Windows package, run:
```cmd
python scripts/build_for_windows.py
```
The output will be located in the `releases/` directory.

#### macOS
To create a macOS App Bundle, run:
```bash
python3 scripts/build_for_macos.py
```

## 📁 Project Structure

- `backend/`: Python-based download engine and scraper service.
- `frontend/`: Flutter-based desktop application.
- `scripts/`: Build and packaging utilities.
- `bin/`: Platform-specific binaries (FFmpeg, etc.).
- `runtimes/`: Portable Python runtimes for zero-dependency releases.

## 🤝 Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

## 📄 License

This project is for educational purposes only. Please respect the terms of service of the platforms used.
