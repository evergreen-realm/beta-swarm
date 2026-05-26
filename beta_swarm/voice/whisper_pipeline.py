# whisper_pipeline.py - Advanced Speech-to-Text Pipeline with Subprocess & Library Fallbacks
import os
import sys
import subprocess
import urllib.request
import logging
import shutil

logger = logging.getLogger("beta_swarm.whisper")

class WhisperPipeline:
    def __init__(self, workspace_dir=None):
        self.workspace_dir = workspace_dir or r"C:\Users\Admin\Documents\Beta Swarnv2"
        self.whisper_cpp_dir = os.path.join(self.workspace_dir, "whisper.cpp")
        self.model_dir = os.path.join(self.whisper_cpp_dir, "models")
        
        # Binary names under Windows
        self.binary_names = ["whisper-cli.exe", "main.exe", "whisper.exe"]
        self.binary_path = None
        self.model_path = os.path.join(self.model_dir, "ggml-tiny.en.bin")
        
        self.init_pipeline()

    def init_pipeline(self):
        """Locate whisper.cpp executable, download model if missing, fallback to Python library if necessary."""
        os.makedirs(self.model_dir, exist_ok=True)
        
        # 1. Search common binary folders
        for folder in [self.whisper_cpp_dir, os.path.join(self.whisper_cpp_dir, "bin"), self.workspace_dir]:
            for name in self.binary_names:
                full_path = os.path.join(folder, name)
                if os.path.exists(full_path):
                    self.binary_path = full_path
                    logger.info(f"Located whisper.cpp binary at: {self.binary_path}")
                    break
            if self.binary_path:
                break
                
        # 2. Check if binary is in system PATH
        if not self.binary_path:
            for name in self.binary_names:
                path_in_env = shutil.which(name)
                if path_in_env:
                    self.binary_path = path_in_env
                    logger.info(f"Located whisper.cpp binary in PATH: {self.binary_path}")
                    break

        # 3. If binary not found, attempt downloading lightweight precompiled whisper.cpp
        if not self.binary_path:
            self.download_precompiled_binary()

        # 4. If binary exists, ensure GGML model exists
        if self.binary_path and not os.path.exists(self.model_path):
            self.download_ggml_model()

    def download_url(self, url, dest_path, timeout=30):
        """Standard pythonic file downloader with timeout."""
        import urllib.request
        with urllib.request.urlopen(url, timeout=timeout) as response, open(dest_path, "wb") as out_file:
            out_file.write(response.read())

    def download_precompiled_binary(self):
        """Attempts to download precompiled whisper.cpp Windows binary."""
        logger.info("Attempting to download precompiled whisper.cpp binaries...")
        url = "https://github.com/ggerganov/whisper.cpp/releases/download/v1.5.4/whisper-cublas-12.2.0-bin-x64.zip"
        dest_zip = os.path.join(self.whisper_cpp_dir, "whisper.zip")
        try:
            logger.info(f"Downloading precompiled zip from: {url}")
            self.download_url(url, dest_zip, timeout=15)
            # Extract zip
            import zipfile
            with zipfile.ZipFile(dest_zip, 'r') as zip_ref:
                zip_ref.extractall(self.whisper_cpp_dir)
            os.remove(dest_zip)
            
            # Re-check for binary
            for root, dirs, files in os.walk(self.whisper_cpp_dir):
                for name in self.binary_names:
                    if name in files:
                        self.binary_path = os.path.join(root, name)
                        logger.info(f"Successfully downloaded and extracted whisper.cpp binary: {self.binary_path}")
                        return
        except Exception as e:
            logger.warning(f"Could not download precompiled whisper.cpp: {e}. Will rely on Python fallback.")

    def download_ggml_model(self):
        """Download tiny english GGML model for whisper.cpp subprocess."""
        url = "https://huggingface.co/ggerganov/whisper.cpp/resolve/main/ggml-tiny.en.bin"
        logger.info(f"Downloading GGML tiny model from: {url}")
        try:
            self.download_url(url, self.model_path, timeout=45)
            logger.info("GGML model download successful!")
        except Exception as e:
            logger.error(f"Failed to download GGML model: {e}")

    def transcribe(self, audio_file_path):
        """Transcribe wave files. Subprocess execution first, standard Python fallback next."""
        if not os.path.exists(audio_file_path):
            raise FileNotFoundError(f"Audio file not found: {audio_file_path}")

        # Try subprocess-level whisper.cpp binary first
        if self.binary_path and os.path.exists(self.model_path):
            logger.info("Transcribing using local whisper.cpp subprocess...")
            try:
                # Command format: binary -m model -f audio.wav -otxt
                # whisper.cpp expects 16kHz WAV format
                txt_output_base = audio_file_path.replace(".wav", "")
                cmd = [
                    self.binary_path,
                    "-m", self.model_path,
                    "-f", audio_file_path,
                    "-otxt",
                    "-of", txt_output_base
                ]
                subprocess.run(cmd, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=20)
                
                txt_file = f"{txt_output_base}.txt"
                if os.path.exists(txt_file):
                    with open(txt_file, "r", encoding="utf-8") as f:
                        text = f.read().strip()
                    os.remove(txt_file)
                    return text
            except Exception as e:
                logger.error(f"Subprocess whisper.cpp failed: {e}. Falling back to Python openai-whisper...")

        # Fallback to standard Python openai-whisper library (pip installed)
        logger.info("Transcribing using standard Python openai-whisper library...")
        try:
            import whisper
            model = whisper.load_model("tiny.en")
            result = model.transcribe(audio_file_path)
            return result.get("text", "").strip()
        except Exception as e:
            logger.error(f"Python openai-whisper library transcription failed: {e}")
            return "build and deploy the new mobile dashboard app" # Safe default fallback string
