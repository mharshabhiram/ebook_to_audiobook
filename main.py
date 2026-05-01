import os
import asyncio
import threading
import time
import tempfile
import customtkinter as ctk
from tkinter import filedialog, messagebox
import pygame

# Logic Imports
import fitz  # PyMuPDF
from ebooklib import epub
import ebooklib
from bs4 import BeautifulSoup
import ollama
import edge_tts


class ScrollableApp(ctk.CTk):
    """Base class that adds a full-window scrollable canvas."""

    def __init__(self):
        super().__init__()

        # Outer canvas + scrollbar (fills the whole window)
        self._canvas = ctk.CTkCanvas(self, highlightthickness=0)
        self._scrollbar = ctk.CTkScrollbar(self, orientation="vertical", command=self._canvas.yview)
        self._canvas.configure(yscrollcommand=self._scrollbar.set)

        self._scrollbar.pack(side="right", fill="y")
        self._canvas.pack(side="left", fill="both", expand=True)

        # Inner frame — all widgets go here
        self.inner = ctk.CTkFrame(self._canvas, fg_color="transparent")
        self._window_id = self._canvas.create_window((0, 0), window=self.inner, anchor="nw")

        # Resize inner frame width when window resizes
        self._canvas.bind("<Configure>", self._on_canvas_resize)
        self.inner.bind("<Configure>", self._on_inner_resize)

        # Mouse-wheel scrolling (Windows/Linux/macOS)
        self.bind_all("<MouseWheel>", self._on_mousewheel)        # Windows
        self.bind_all("<Button-4>",   self._on_mousewheel_up)     # Linux
        self.bind_all("<Button-5>",   self._on_mousewheel_down)   # Linux

    def _on_canvas_resize(self, event):
        self._canvas.itemconfig(self._window_id, width=event.width)

    def _on_inner_resize(self, event):
        self._canvas.configure(scrollregion=self._canvas.bbox("all"))

    def _on_mousewheel(self, event):
        self._canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")

    def _on_mousewheel_up(self, event):
        self._canvas.yview_scroll(-1, "units")

    def _on_mousewheel_down(self, event):
        self._canvas.yview_scroll(1, "units")


class AudioBookApp(ScrollableApp):
    def __init__(self):
        super().__init__()

        self.title("AI eBook to Audio Pro")
        self.geometry("800x750")
        self.minsize(500, 400)
        ctk.set_appearance_mode("dark")
        pygame.mixer.init()

        # Variables
        self.file_path = ""
        self.output_dir = os.path.expanduser("~")
        self.is_processing = False
        self.should_cancel = False
        self.start_time = 0
        self.chapters = []

        self.voices = {
            "Andrew (US-M)": "en-US-AndrewNeural",
            "Emma (US-F)": "en-US-EmmaNeural",
            "Ava (US-F)": "en-US-AvaNeural",
            "Brian (US-M)": "en-US-BrianNeural",
            "Sonia (UK-F)": "en-GB-SoniaNeural",
            "Ryan (UK-M)": "en-GB-RyanNeural",
            "Libby (UK-F)": "en-GB-LibbyNeural",
            "Thomas (UK-M)": "en-GB-ThomasNeural",
            "Liam (CA-M)": "en-CA-LiamNeural",
            "Clara (CA-F)": "en-CA-ClaraNeural",
            "Natasha (AU-F)": "en-AU-NatashaNeural",
            "William (AU-M)": "en-AU-WilliamNeural",
            "Emily (IE-F)": "en-IE-EmilyNeural",
            "Connor (IE-M)": "en-IE-ConnorNeural",
            "Mitchell (NZ-M)": "en-NZ-MitchellNeural",
            "Molly (NZ-F)": "en-NZ-MollyNeural",
            "Leah (ZA-F)": "en-ZA-LeahNeural",
            "Luke (ZA-M)": "en-ZA-LukeNeural",
            "Prabhat (IN-M)": "en-IN-PrabhatNeural",
            "Neerja (IN-F)": "en-IN-NeerjaNeural",
            "Yan (HK-F)": "en-HK-YanNeural",
            "Sam (HK-M)": "en-HK-SamNeural"
        }

        # All widgets are children of self.inner (the scrollable frame)
        f = self.inner
        f.grid_columnconfigure(0, weight=1)

        # Title
        ctk.CTkLabel(f, text="AI eBook to Audio Pro", font=("Arial", 24, "bold")).grid(
            row=0, column=0, pady=15)

        # File Selection
        self.file_button = ctk.CTkButton(f, text="Select EPUB or PDF", command=self.select_file)
        self.file_button.grid(row=1, column=0, pady=5)

        self.file_label = ctk.CTkLabel(f, text="No file selected", font=("Arial", 12), text_color="gray")
        self.file_label.grid(row=2, column=0, pady=5)

        # Chapter Info
        info_frame = ctk.CTkFrame(f)
        info_frame.grid(row=3, column=0, pady=10, padx=20, sticky="ew")
        info_frame.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(info_frame, text="Document Analysis (Chapters & Word Count)",
                     font=("Arial", 12, "bold")).grid(row=0, column=0, pady=5)

        self.chapter_box = ctk.CTkTextbox(info_frame, height=150, font=("Courier", 12))
        self.chapter_box.grid(row=1, column=0, padx=10, pady=10, sticky="ew")
        self.chapter_box.insert("0.0", "Select a file to see chapter details...")

        # Conversion Mode
        mode_frame = ctk.CTkFrame(f)
        mode_frame.grid(row=4, column=0, pady=10, padx=20, sticky="ew")
        mode_frame.grid_columnconfigure((0, 1), weight=1)

        ctk.CTkLabel(mode_frame, text="Conversion Mode:", font=("Arial", 12, "bold")).grid(
            row=0, column=0, columnspan=2, pady=(10, 5))

        self.conversion_mode = ctk.StringVar(value="whole")

        ctk.CTkRadioButton(mode_frame, text="Whole Book  (single MP3)",
                           variable=self.conversion_mode, value="whole",
                           command=self.on_mode_change).grid(row=1, column=0, padx=20, pady=(0, 10))

        ctk.CTkRadioButton(mode_frame, text="By Chapter  (one MP3 per chapter)",
                           variable=self.conversion_mode, value="chapter",
                           command=self.on_mode_change).grid(row=1, column=1, padx=20, pady=(0, 10))

        # Chapter selector (hidden until chapter mode selected)
        self.chapter_select_frame = ctk.CTkFrame(f)
        self.chapter_select_frame.grid(row=5, column=0, pady=5, padx=20, sticky="ew")
        self.chapter_select_frame.grid_columnconfigure(1, weight=1)
        self.chapter_select_frame.grid_remove()

        ctk.CTkLabel(self.chapter_select_frame, text="Chapter:").grid(row=0, column=0, padx=10, pady=10)
        self.chapter_var = ctk.StringVar(value="All Chapters")
        self.chapter_menu = ctk.CTkOptionMenu(self.chapter_select_frame, values=["All Chapters"],
                                              variable=self.chapter_var)
        self.chapter_menu.grid(row=0, column=1, padx=10, pady=10, sticky="ew")

        # Output Directory
        out_frame = ctk.CTkFrame(f)
        out_frame.grid(row=6, column=0, pady=10, padx=20, sticky="ew")
        out_frame.grid_columnconfigure(1, weight=1)

        ctk.CTkLabel(out_frame, text="Save To:").grid(row=0, column=0, padx=10, pady=10)
        self.out_dir_label = ctk.CTkLabel(out_frame, text=self.output_dir, font=("Arial", 11),
                                          text_color="gray", anchor="w")
        self.out_dir_label.grid(row=0, column=1, padx=10, pady=10, sticky="ew")
        ctk.CTkButton(out_frame, text="Browse", width=80,
                      command=self.select_output_dir).grid(row=0, column=2, padx=10, pady=10)

        # Voice Selection
        voice_frame = ctk.CTkFrame(f)
        voice_frame.grid(row=7, column=0, pady=10, padx=20, sticky="ew")
        voice_frame.grid_columnconfigure(1, weight=1)

        ctk.CTkLabel(voice_frame, text="Voice:").grid(row=0, column=0, padx=10, pady=10)
        self.voice_var = ctk.StringVar(value="Andrew (US-M)")
        ctk.CTkOptionMenu(voice_frame, values=list(self.voices.keys()),
                          variable=self.voice_var).grid(row=0, column=1, padx=10, pady=10, sticky="ew")
        self.preview_button = ctk.CTkButton(voice_frame, text="▶ Preview", width=80,
                                            fg_color="#555", command=self.preview_voice)
        self.preview_button.grid(row=0, column=2, padx=10, pady=10)

        # Speed Control
        speed_frame = ctk.CTkFrame(f)
        speed_frame.grid(row=8, column=0, pady=10, padx=20, sticky="ew")
        speed_frame.grid_columnconfigure(1, weight=1)

        ctk.CTkLabel(speed_frame, text="Speed:").grid(row=0, column=0, padx=10, pady=10)
        self.speed_slider = ctk.CTkSlider(speed_frame, from_=0.5, to=2.0, number_of_steps=15,
                                          command=self.update_speed_label)
        self.speed_slider.set(1.0)
        self.speed_slider.grid(row=0, column=1, padx=10, pady=10, sticky="ew")
        self.speed_label = ctk.CTkLabel(speed_frame, text="1.0x", width=40)
        self.speed_label.grid(row=0, column=2, padx=10, pady=10)

        # Action Buttons
        button_frame = ctk.CTkFrame(f, fg_color="transparent")
        button_frame.grid(row=9, column=0, pady=20)

        self.convert_button = ctk.CTkButton(button_frame, text="Start Conversion",
                                            command=self.start_thread, fg_color="green",
                                            font=("Arial", 14, "bold"))
        self.convert_button.pack(side="left", padx=10)

        self.cancel_button = ctk.CTkButton(button_frame, text="Cancel",
                                           command=self.cancel_conversion,
                                           fg_color="#991b1b", hover_color="#7f1d1d", state="disabled")
        self.cancel_button.pack(side="left", padx=10)

        # Progress
        self.progress_bar = ctk.CTkProgressBar(f, width=450)
        self.progress_bar.set(0)
        self.progress_bar.grid(row=10, column=0, pady=10)

        self.stats_label = ctk.CTkLabel(f, text="Elapsed: 0s | Remaining: --", font=("Arial", 11))
        self.stats_label.grid(row=11, column=0, pady=5)

        self.status_label = ctk.CTkLabel(f, text="", font=("Arial", 11), text_color="gray")
        self.status_label.grid(row=12, column=0, pady=(2, 20))

    # -------------------------------------------------------------------------
    # Mode / UI helpers
    # -------------------------------------------------------------------------

    def on_mode_change(self):
        if self.conversion_mode.get() == "chapter":
            self.chapter_select_frame.grid()
        else:
            self.chapter_select_frame.grid_remove()

    def select_output_dir(self):
        chosen = filedialog.askdirectory(initialdir=self.output_dir, title="Select Output Folder")
        if chosen:
            self.output_dir = chosen
            display = chosen if len(chosen) <= 60 else "..." + chosen[-57:]
            self.out_dir_label.configure(text=display, text_color="white")

    def update_speed_label(self, value):
        self.speed_label.configure(text=f"{value:.1f}x")

    def get_speed_string(self):
        val = self.speed_slider.get()
        percent = int((val - 1.0) * 100)
        return f"{'+' if percent >= 0 else ''}{percent}%"

    def safe_filename(self, name: str) -> str:
        return "".join(c for c in name if c.isalnum() or c in " _-").strip() or "chapter"

    # -------------------------------------------------------------------------
    # Document analysis
    # -------------------------------------------------------------------------

    def analyze_document(self):
        self.chapter_box.delete("0.0", "end")
        self.chapter_box.insert("0.0", "Analyzing document… please wait.\n")
        self.chapters = []

        analysis_text = ""
        total_words = 0

        try:
            if self.file_path.endswith(".pdf"):
                doc = fitz.open(self.file_path)
                toc = doc.get_toc()

                if not toc:
                    text = "".join([page.get_text() for page in doc])
                    total_words = len(text.split())
                    analysis_text = f"Full Document (No ToC): {total_words} words"
                    self.chapters = [("Full Document", text)]
                else:
                    for i, entry in enumerate(toc):
                        level, title, page_num = entry
                        start_page = page_num - 1
                        end_page = toc[i + 1][2] - 1 if i + 1 < len(toc) else doc.page_count
                        chapter_text = "".join(doc[p].get_text() for p in range(start_page, end_page))
                        count = len(chapter_text.split())
                        total_words += count
                        analysis_text += f"[{level}] {title[:40]:.<40} {count} words\n"
                        self.chapters.append((title, chapter_text))

            elif self.file_path.endswith(".epub"):
                book = epub.read_epub(self.file_path)
                for item in book.get_items_of_type(ebooklib.ITEM_DOCUMENT):
                    soup = BeautifulSoup(item.get_content(), 'html.parser')
                    title_tag = soup.find(['h1', 'h2', 'h3', 'title'])
                    name = title_tag.get_text().strip() if title_tag else item.get_name()
                    text = soup.get_text()
                    count = len(text.split())
                    if count > 20:
                        total_words += count
                        analysis_text += f"{name[:45]:.<45} {count} words\n"
                        self.chapters.append((name, text))

            self.chapter_box.delete("0.0", "end")
            self.chapter_box.insert("0.0", f"TOTAL WORD COUNT: {total_words}\n" + "-" * 50 + "\n" + analysis_text)

            chapter_names = ["All Chapters"] + [ch[0] for ch in self.chapters]
            self.chapter_menu.configure(values=chapter_names)
            self.chapter_var.set("All Chapters")

        except Exception as e:
            self.chapter_box.insert("end", f"\nError analyzing: {e}")

    # -------------------------------------------------------------------------
    # File selection
    # -------------------------------------------------------------------------

    def select_file(self):
        self.file_path = filedialog.askopenfilename(filetypes=[("eBook Files", "*.pdf *.epub")])
        if self.file_path:
            self.file_label.configure(text=os.path.basename(self.file_path), text_color="white")
            threading.Thread(target=self.analyze_document, daemon=True).start()

    # -------------------------------------------------------------------------
    # Voice preview
    # -------------------------------------------------------------------------

    def preview_voice(self):
        text = "This is a preview of the selected voice and speed."
        voice_key = self.voices[self.voice_var.get()]
        speed = self.get_speed_string()

        async def play_sample():
            self.preview_button.configure(state="disabled", text="...")
            pygame.mixer.music.stop()
            pygame.mixer.music.unload()

            tmp = tempfile.NamedTemporaryFile(suffix=".mp3", delete=False)
            tmp_path = tmp.name
            tmp.close()

            try:
                communicate = edge_tts.Communicate(text, voice_key, rate=speed)
                await communicate.save(tmp_path)
                pygame.mixer.music.load(tmp_path)
                pygame.mixer.music.play()
                while pygame.mixer.music.get_busy():
                    await asyncio.sleep(0.1)
            except Exception as e:
                print(f"Preview error: {e}")
            finally:
                pygame.mixer.music.unload()
                try:
                    os.remove(tmp_path)
                except Exception:
                    pass
                self.preview_button.configure(state="normal", text="▶ Preview")

        threading.Thread(target=lambda: asyncio.run(play_sample()), daemon=True).start()

    # -------------------------------------------------------------------------
    # Conversion
    # -------------------------------------------------------------------------

    def cancel_conversion(self):
        if self.is_processing:
            self.should_cancel = True
            self.cancel_button.configure(text="Cancelling…", state="disabled")

    async def convert_chapter(self, title: str, text: str, out_path: str, voice_id: str, speed: str):
        chunks = [text[i:i + 2000] for i in range(0, len(text), 2000)]
        cleaned_parts = []

        for chunk in chunks:
            if self.should_cancel:
                return
            prompt = (
                "Clean the following text for natural narration. "
                "Remove headers, page numbers, and fix formatting. "
                "Return only the cleaned text:\n\n" + chunk
            )
            response = ollama.chat(model='mistral', messages=[{'role': 'user', 'content': prompt}])
            cleaned_parts.append(response['message']['content'])

        full_clean = " ".join(cleaned_parts)
        tts_chunks = [full_clean[i:i + 4000] for i in range(0, len(full_clean), 4000)]

        audio_bytes = bytearray()
        for tts_chunk in tts_chunks:
            if self.should_cancel:
                return
            tmp = tempfile.NamedTemporaryFile(suffix=".mp3", delete=False)
            tmp_path = tmp.name
            tmp.close()
            communicate = edge_tts.Communicate(tts_chunk, voice_id, rate=speed)
            await communicate.save(tmp_path)
            with open(tmp_path, "rb") as f:
                audio_bytes.extend(f.read())
            os.remove(tmp_path)

        with open(out_path, "wb") as f:
            f.write(audio_bytes)

    async def run_conversion(self):
        if not self.file_path:
            messagebox.showerror("Error", "Please select a file first!")
            return
        if not self.chapters:
            messagebox.showerror("Error", "No chapters found. Please re-select the file.")
            return

        self.is_processing = True
        self.should_cancel = False
        self.convert_button.configure(state="disabled", text="Processing…")
        self.cancel_button.configure(state="normal", text="Cancel")
        self.start_time = time.time()

        speed = self.get_speed_string()
        voice_id = self.voices[self.voice_var.get()]
        mode = self.conversion_mode.get()

        try:
            if mode == "whole":
                self.status_label.configure(text="Mode: Whole Book")
                full_text = "\n\n".join(text for _, text in self.chapters)
                book_name = self.safe_filename(os.path.splitext(os.path.basename(self.file_path))[0])
                out_path = os.path.join(self.output_dir, f"{book_name}.mp3")

                self.progress_bar.set(0)
                self.status_label.configure(text="Converting entire book…")
                await self.convert_chapter("Full Book", full_text, out_path, voice_id, speed)

                if not self.should_cancel:
                    self.progress_bar.set(1)
                    elapsed = int(time.time() - self.start_time)
                    self.stats_label.configure(text=f"Elapsed: {elapsed}s | Done")
                    messagebox.showinfo("Success", f"Audiobook saved to:\n{out_path}")

            else:
                selected = self.chapter_var.get()
                chapters_to_convert = (
                    self.chapters if selected == "All Chapters"
                    else [(t, txt) for t, txt in self.chapters if t == selected]
                )
                total = len(chapters_to_convert)
                book_name = self.safe_filename(os.path.splitext(os.path.basename(self.file_path))[0])

                for idx, (title, text) in enumerate(chapters_to_convert):
                    if self.should_cancel:
                        break
                    safe_title = self.safe_filename(title)
                    out_path = os.path.join(self.output_dir, f"{book_name} - {idx + 1:02d} - {safe_title}.mp3")
                    self.status_label.configure(text=f"Chapter {idx + 1}/{total}: {title[:50]}")
                    await self.convert_chapter(title, text, out_path, voice_id, speed)

                    elapsed = time.time() - self.start_time
                    avg = elapsed / (idx + 1)
                    remaining = avg * (total - (idx + 1))
                    self.progress_bar.set((idx + 1) / total)
                    self.stats_label.configure(text=f"Elapsed: {int(elapsed)}s | Remaining: {int(remaining)}s")
                    self.update_idletasks()

                if not self.should_cancel:
                    messagebox.showinfo("Success", f"All chapters saved to:\n{self.output_dir}")
                else:
                    messagebox.showwarning("Cancelled", "Conversion was stopped.")

        except Exception as e:
            messagebox.showerror("Error", str(e))
        finally:
            self.is_processing = False
            self.convert_button.configure(state="normal", text="Start Conversion")
            self.cancel_button.configure(state="disabled", text="Cancel")
            self.progress_bar.set(0)
            self.status_label.configure(text="")

    def start_thread(self):
        threading.Thread(target=lambda: asyncio.run(self.run_conversion()), daemon=True).start()


if __name__ == "__main__":
    app = AudioBookApp()
    app.mainloop()
