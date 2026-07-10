# 📚 AI eBook to Audio Pro

Transform your EPUB and PDF eBooks into natural-sounding audiobooks
using AI.

AI eBook to Audio Pro is a desktop application built with Python and
CustomTkinter that combines:

-   📖 eBook parsing
-   🤖 AI-powered text cleaning using Ollama
-   🎙️ Microsoft Edge Neural Text-to-Speech
-   🎵 MP3 audiobook generation

The application supports converting an entire book into one audiobook or
exporting every chapter as separate MP3 files.

------------------------------------------------------------------------

# Features

-   📚 Supports EPUB and PDF files
-   🤖 AI text cleanup using Ollama (Mistral)
-   🎙️ 20+ Microsoft Edge Neural Voices
-   ⚡ Adjustable narration speed
-   🎧 Voice preview before conversion
-   📁 Choose custom output directory
-   📖 Chapter detection
-   📊 Word count analysis
-   📀 Export:
    -   Entire book → Single MP3
    -   Chapter-wise → Separate MP3 files
-   📈 Live progress bar
-   ⏱ Estimated remaining time
-   ❌ Cancel conversion anytime
-   🌙 Modern Dark UI (CustomTkinter)

------------------------------------------------------------------------

# Tech Stack

-   **GUI:** CustomTkinter, Tkinter
-   **AI:** Ollama (Mistral)
-   **Text Extraction:** PyMuPDF, ebooklib, BeautifulSoup4
-   **Text-to-Speech:** edge-tts
-   **Audio:** pygame
-   **Concurrency:** asyncio, threading

------------------------------------------------------------------------

# Installation

``` bash
git clone https://github.com/yourusername/ebook-to-audiobook.git
cd ebook-to-audiobook
```

Create a virtual environment:

**Windows**

``` bash
python -m venv venv
venv\Scripts\activate
```

**Linux/macOS**

``` bash
python3 -m venv venv
source venv/bin/activate
```

Install dependencies:

``` bash
pip install customtkinter pygame pymupdf ebooklib beautifulsoup4 edge-tts ollama
```

Install Ollama from https://ollama.com

Then:

``` bash
ollama pull mistral
ollama serve
```

Run:

``` bash
python ebook_to_audiobook.py
```

------------------------------------------------------------------------

# Usage

1.  Select an EPUB or PDF.
2.  Review detected chapters and word counts.
3.  Choose **Whole Book** or **By Chapter** mode.
4.  Select a voice and playback speed.
5.  Preview the voice.
6.  Start conversion.

The application cleans the extracted text using the Mistral model
running locally through Ollama and converts it into high-quality speech
using Microsoft Edge Neural TTS.

------------------------------------------------------------------------

# Project Structure

``` text
ebook-to-audiobook/
├── ebook_to_audiobook.py
├── README.md
├── requirements.txt
└── screenshots/
```

------------------------------------------------------------------------

# Requirements

-   Python 3.10+
-   Ollama installed
-   Mistral model downloaded
-   Internet connection for Edge TTS

------------------------------------------------------------------------

# Future Improvements

-   M4B audiobook export
-   Metadata editor
-   Cover art embedding
-   Batch conversion
-   Resume interrupted conversions
-   Drag-and-drop support

------------------------------------------------------------------------

# Author

**Harshabhiram Manik**

If you find this project useful, consider giving it a ⭐ on GitHub.
