# Raspberry Pi RGB LED Matrix Control

This project provides a Python framework for controlling RGB LED matrices with a Raspberry Pi using the excellent [rpi-rgb-led-matrix](https://github.com/hzeller/rpi-rgb-led-matrix) library.

## Features

- Simple interface for controlling RGB matrices
- Text rendering with multiple fonts
- Scrolling text animation
- Clock display
- Image and GIF display
- API integration
- Animation framework for creating custom animations

## Hardware Requirements

- Raspberry Pi (Zero 2W or newer recommended)
- Adafruit RGB Matrix HAT or compatible hardware
- RGB LED Matrix panel (32x32, 64x32, 64x64, etc.)
- 5V power supply with sufficient current for your matrix
- Micro SD card with Raspberry Pi OS

## Software Requirements

- Raspberry Pi OS (Buster or newer)
- Python 3.6+
- Required system packages and Python libraries (see Installation)

## Installation

### 1. System Packages

First, install the required system packages:

```bash
sudo apt-get update
sudo apt-get install -y python3-dev python3-pillow python3-pip libgraphicsmagick++-dev libwebp-dev git