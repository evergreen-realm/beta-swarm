import os
import subprocess

def search_file(name_patterns, search_roots=None):
    if search_roots is None:
        search_roots = [
            os.path.expanduser("~"),
            "C:\\Program Files",
            "C:\\ProgramData",
        ]
    results = []
    patterns = [p.replace("*", "").lower() for p in name_patterns]
    
    for root_dir in search_roots:
        if not os.path.exists(root_dir):
            continue
        try:
            for dirpath, _, filenames in os.walk(root_dir):
                # Skip massive system folders
                if "Windows" in dirpath or "AppData\\Local\\Microsoft" in dirpath:
                    continue
                    
                lower_dir = os.path.basename(dirpath).lower()
                for pat in patterns:
                    if pat in lower_dir:
                        results.append(dirpath)
                        break
                for f in filenames:
                    lower_f = f.lower()
                    for pat in patterns:
                        if pat in lower_f:
                            results.append(os.path.join(dirpath, f))
                            break
                
                if len(results) > 20:
                    return results
        except:
            pass
    return results

def check_command(cmd):
    try:
        result = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=10)
        return result.stdout.strip() if result.returncode == 0 else f"NOT FOUND (exit {result.returncode})"
    except Exception as e:
        return f"ERROR: {e}"

print("=" * 60)
print("BETA SWARM — PC TOOL AUDIT")
print("=" * 60)

print("\\n--- 1. OpenClaw ---")
print("Folders:", search_file(["openclaw"])[:10])
print("pip:", check_command("pip list 2>nul | findstr -i openclaw"))

print("\\n--- 2. Hermes ---")
print("Folders:", search_file(["hermes", "nous"])[:10])
print("pip:", check_command("pip list 2>nul | findstr -i hermes"))
print("LM Studio models:", search_file(["hermes"], [os.path.expanduser("~\\.lmstudio\\models")])[:5])

print("\\n--- 3. Whisper ---")
print("Files:", search_file(["whisper", "ggml-base.bin", "ggml-"])[:10])
print("pip:", check_command("pip list 2>nul | findstr -i whisper"))
print("winget:", check_command("winget list 2>nul | findstr -i whisper"))

print("\\n--- 4. Git CLI ---")
print("where git:", check_command("where git"))
print("git version:", check_command("git --version"))

print("\\n--- 5. Playwright ---")
print("where playwright:", check_command("where playwright"))
print("pip show:", check_command("pip show playwright 2>nul | findstr Location"))
print("browser cache:", search_file(["chromium"], [os.path.expanduser("~\\AppData\\Local\\ms-playwright")])[:5])

print("\\n--- 6. Selenium ---")
print("pip show:", check_command("pip show selenium 2>nul | findstr Location"))
print("chromedriver:", check_command("where chromedriver"))

print("\\n--- 7. Aider ---")
print("where aider:", check_command("where aider"))
print("pip show:", check_command("pip show aider-chat 2>nul | findstr Location"))

print("\\n--- 8. Goose ---")
print("where goose:", check_command("where goose"))
print("folders:", search_file(["goose"])[:5])

print("\\n--- 9. BitNet ---")
print("pip show:", check_command("pip show bitnet 2>nul | findstr Location"))

print("\\n--- 10. EXO ---")
print("folders:", search_file(["exo"])[:5])
print("pip show:", check_command("pip show exo 2>nul | findstr Location"))

print("\\n--- PATH CHECK ---")
print("PATH contains Git:", "Git" in os.environ.get("PATH", ""))
print("PATH contains Python:", "Python" in os.environ.get("PATH", ""))
