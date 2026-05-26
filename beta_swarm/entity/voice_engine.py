import speech_recognition as sr
import threading
import time
import os
import sys
import subprocess

sys.path.insert(0, r"C:\Users\Admin\Documents\Beta Swarnv2")

class VoiceEngine:
    def __init__(self):
        self.recognizer = sr.Recognizer()
        self.microphone = sr.Microphone()
        self.listening = True
        self.wake_words = ["hey swarm", "beta swarm", "jarvis", "swarm"]
        
        # Calibrate for ambient noise
        try:
            with self.microphone as source:
                print("Calibrating voice engine...")
                self.recognizer.adjust_for_ambient_noise(source, duration=2)
                print("Voice engine calibrated")
        except Exception as e:
            print(f"Could not calibrate microphone: {e}")
            self.listening = False
    
    def speak(self, text: str):
        """Text-to-speech using edge-tts"""
        try:
            import asyncio
            import edge_tts
            
            async def _speak():
                communicate = edge_tts.Communicate(text, "en-US-AriaNeural")
                await communicate.save("temp_voice.mp3")
            
            asyncio.run(_speak())
            os.system("start temp_voice.mp3")
        except Exception as e:
            print(f"TTS failed: {e}")
    
    def listen_loop(self):
        while self.listening:
            try:
                with self.microphone as source:
                    print("Listening...")
                    audio = self.recognizer.listen(source, timeout=5, phrase_time_limit=5)
                
                text = self.recognizer.recognize_google(audio).lower()
                print(f"Heard: {text}")
                
                # Check wake words
                if any(wake in text for wake in self.wake_words):
                    self.handle_command(text)
                    
            except sr.WaitTimeoutError:
                continue
            except sr.UnknownValueError:
                continue
            except Exception as e:
                print(f"Error: {e}")
                time.sleep(1)
    
    def handle_command(self, text: str):
        if "dashboard" in text or "open" in text:
            self.speak("Opening dashboard")
            self.open_dashboard()
        elif "galaxy" in text or "show" in text:
            self.speak("Opening galaxy view")
            self.open_galaxy()
        elif "status" in text:
            self.speak("Checking swarm status")
            self.report_status()
        elif "build" in text or "project" in text:
            self.speak("Starting new project")
            self.start_build()
        elif "deploy" in text:
            self.speak("Initiating deployment")
            self.deploy()
        elif "stop" in text or "abort" in text:
            self.speak("Stopping all agents")
            self.abort()
        else:
            self.speak("I heard you. Say dashboard, galaxy, status, build, deploy, or stop.")
    
    def open_dashboard(self):
        subprocess.Popen([
            sys.executable, "-m", "beta_swarm.entity.native_window"
        ], cwd=r"C:\Users\Admin\Documents\Beta Swarnv2")
    
    def open_galaxy(self):
        subprocess.Popen([
            sys.executable, "-m", "beta_swarm.entity.galaxy_window"
        ], cwd=r"C:\Users\Admin\Documents\Beta Swarnv2")
    
    def report_status(self):
        try:
            from beta_swarm.brain.safe_brain import SafeBrain
            brain = SafeBrain()
            agents = brain.query_agents()
            active = len([a for a in agents if a.get("status") == "active"])
            self.speak(f"Swarm status: {active} agents active out of {len(agents)} total")
        except:
            self.speak("Cannot fetch status. Database might be locked.")
    
    def start_build(self):
        import requests
        try:
            port = int(os.environ.get("PORT", 8999))
            requests.post(f"http://127.0.0.1:{port}/api/command", json={"command": "build new project"})
            self.speak("Build started. Check the dashboard for progress.")
        except:
            self.speak("Cannot reach swarm. Is the dashboard running?")
    
    def deploy(self):
        import requests
        try:
            port = int(os.environ.get("PORT", 8999))
            requests.post(f"http://127.0.0.1:{port}/api/pipeline/deploy")
            self.speak("Deployment initiated")
        except:
            self.speak("Cannot deploy. Check connection.")
    
    def abort(self):
        import requests
        try:
            port = int(os.environ.get("PORT", 8999))
            requests.post(f"http://127.0.0.1:{port}/api/pipeline/abort")
            self.speak("All agents stopped")
        except:
            self.speak("Cannot stop agents.")

def main():
    engine = VoiceEngine()
    if engine.listening:
        engine.speak("Beta Swarm voice engine active")
        engine.listen_loop()
    else:
        print("Voice Engine failed to initialize.")

if __name__ == "__main__":
    main()
