import os
import subprocess
import glob

def check_command(cmd):
    try:
        result = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=5)
        out = result.stdout.strip()
        if result.returncode == 0:
            return out if out else "FOUND (no output)"
        else:
            return "NOT FOUND"
    except Exception as e:
        return f"ERROR: {e}"

def fast_search(patterns, root_dirs):
    results = []
    for root in root_dirs:
        root = os.path.expanduser(root)
        if not os.path.exists(root):
            continue
        try:
            for pat in patterns:
                for path in glob.glob(os.path.join(root, "**", pat), recursive=True):
                    results.append(path)
                    if len(results) > 5:
                        return results
        except:
            pass
    return results

print("=" * 60)
print("BETA SWARM — PC TOOL AUDIT")
print("=" * 60)

print("\n--- 1. OpenClaw ---")
print("Folders:", fast_search(["*openclaw*"], ["~", "C:\\Program Files", "C:\\ProgramData"]))
print("pip:", check_command("pip list 2>nul | findstr -i openclaw"))
print("npm:", check_command("npm list -g 2>nul | findstr -i openclaw"))

print("\n--- 2. Hermes ---")
print("Folders:", fast_search(["*hermes*", "*nous*"], ["~", "C:\\Program Files"]))
print("pip:", check_command("pip list 2>nul | findstr -i hermes"))
print("LM Studio models:", fast_search(["*hermes*"], ["~\\.lmstudio\\models"]))

print("\n--- 3. Whisper ---")
print("Files:", fast_search(["whisper-cli.exe", "ggml-*.bin", "*whisper*"], ["~", "C:\\Program Files"]))
print("pip:", check_command("pip list 2>nul | findstr -i whisper"))
print("winget:", check_command("winget list 2>nul | findstr -i whisper"))

print("\n--- 4. Git CLI ---")
print("where git:", check_command("where git"))
print("git version:", check_command("git --version"))

print("\n--- 5. Playwright ---")
print("where playwright:", check_command("where playwright"))
print("pip show:", check_command("pip show playwright 2>nul | findstr Location"))

print("\n--- 6. Selenium ---")
print("pip show:", check_command("pip show selenium 2>nul | findstr Location"))
print("chromedriver:", check_command("where chromedriver"))

print("\n--- 7. Aider ---")
print("where aider:", check_command("where aider"))
print("pip show:", check_command("pip show aider-chat 2>nul | findstr Location"))

print("\n--- 8. Goose ---")
print("where goose:", check_command("where goose"))

print("\n--- 9. BitNet ---")
print("pip show:", check_command("pip show bitnet 2>nul | findstr Location"))

print("\n--- 10. EXO ---")
print("pip show:", check_command("pip show exo 2>nul | findstr Location"))

print("\n--- PATH CHECK ---")
print("PATH contains Git:", "Git" in os.environ.get("PATH", ""))
print("PATH contains Python:", "Python" in os.environ.get("PATH", ""))
