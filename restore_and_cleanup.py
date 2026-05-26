import os
import shutil

SRC = r"C:/Users/Admin/Desktop/tools/Beta swarnv2"
DST = r"C:/Users/Admin/Documents/Beta Swarnv2"

def main():
    print("==========================================")
    print("STARTING RESTORATION AND CLEANUP LIFECYCLE")
    print("==========================================")
    
    # 1. Restore missing files
    restored_count = 0
    for root, dirs, files in os.walk(SRC):
        rel_path = os.path.relpath(root, SRC)
        if rel_path == "." or rel_path.startswith(".git") or rel_path.startswith("backup"):
            continue
            
        target_dir = os.path.join(DST, rel_path)
        os.makedirs(target_dir, exist_ok=True)
        
        for f in files:
            src_file = os.path.join(root, f)
            dst_file = os.path.join(target_dir, f)
            if not os.path.exists(dst_file):
                try:
                    shutil.copy2(src_file, dst_file)
                    restored_count += 1
                except Exception as e:
                    print(f"Error copying {src_file}: {e}")
                    
    print(f"Restored {restored_count} files/directories from backup.")

    # 2. Delete specified test folders
    DIRS_TO_DELETE = [
        "projects/IoTAnalyticsFINAL",
        "projects/IoTAnalyticsPERFECT",
        "projects/IoTAnalyticsV2",
        "projects/IoTAnalyticsV3",
        "projects/IoTAnalyticsV4",
        "projects/IoTAnalyticsV5",
        "projects/IoTAnalyticsV6",
        "projects/IoTAnalyticsV7",
        "projects/IoTAnalyticsV8",
        "projects/IoTAnalyticsV9",
        "projects/IoTAnalyticsV10",
        "projects/SuperSwarmV2",
        "projects/new_project",
        "gumloop_results",
        "js-code-sandbox",
        "deploy/backup_deploy"
    ]
    
    deleted_dirs_count = 0
    for d in DIRS_TO_DELETE:
        path = os.path.join(DST, d)
        if os.path.exists(path):
            if d == "projects/new_project":
                # Only delete if empty
                try:
                    if not os.listdir(path):
                        shutil.rmtree(path, ignore_errors=True)
                        print("Deleted empty projects/new_project")
                        deleted_dirs_count += 1
                except Exception:
                    pass
            else:
                shutil.rmtree(path, ignore_errors=True)
                print(f"Deleted directory: {d}")
                deleted_dirs_count += 1

    # 3. Delete pycache and pyc recursively
    deleted_pycache_count = 0
    deleted_pyc_count = 0
    for root, dirs, files in os.walk(DST):
        if "backup" in root: # Skip local backup folder
            continue
        if "__pycache__" in dirs:
            pycache_path = os.path.join(root, "__pycache__")
            shutil.rmtree(pycache_path, ignore_errors=True)
            deleted_pycache_count += 1
        for f in files:
            if f.endswith(".pyc"):
                try:
                    os.remove(os.path.join(root, f))
                    deleted_pyc_count += 1
                except Exception:
                    pass
    print(f"Deleted {deleted_pycache_count} pycache directories and {deleted_pyc_count} pyc files.")

    # 4. Rename kuzudb_manager.py to sqlite_brain.py and update class name
    old_kuzu = os.path.join(DST, "beta_swarm/brain/kuzudb_manager.py")
    new_sqlite = os.path.join(DST, "beta_swarm/brain/sqlite_brain.py")
    
    if os.path.exists(old_kuzu):
        try:
            with open(old_kuzu, "r", encoding="utf-8") as f:
                content = f.read()
            
            # Replace KuzuBrain with SQLiteBrain
            content = content.replace("class KuzuBrain:", "class SQLiteBrain:")
            # Add alias for backward compatibility
            content += "\n\nKuzuBrain = SQLiteBrain\n"
            
            with open(new_sqlite, "w", encoding="utf-8") as f:
                f.write(content)
            
            os.remove(old_kuzu)
            print("Renamed kuzudb_manager.py -> sqlite_brain.py and changed class name to SQLiteBrain")
        except Exception as e:
            print(f"Error renaming kuzudb_manager.py: {e}")
    elif os.path.exists(new_sqlite):
        try:
            with open(new_sqlite, "r", encoding="utf-8") as f:
                content = f.read()
            if "class KuzuBrain" in content:
                content = content.replace("class KuzuBrain:", "class SQLiteBrain:")
                content += "\n\nKuzuBrain = SQLiteBrain\n"
                with open(new_sqlite, "w", encoding="utf-8") as f:
                    f.write(content)
                print("Updated class name to SQLiteBrain in sqlite_brain.py")
        except Exception as e:
            print(f"Error updating sqlite_brain.py: {e}")

    # 5. Move b5_obsidian.py to obsidian_manager.py
    obsidian_old = os.path.join(DST, "beta_swarm/agents/brain/b5_obsidian.py")
    obsidian_new = os.path.join(DST, "beta_swarm/brain/obsidian_manager.py")
    if os.path.exists(obsidian_old):
        try:
            if os.path.exists(obsidian_new):
                os.remove(obsidian_old)
                print("Deleted obsolete b5_obsidian.py (obsidian_manager.py already exists)")
            else:
                shutil.move(obsidian_old, obsidian_new)
                print("Moved b5_obsidian.py -> brain/obsidian_manager.py")
        except Exception as e:
            print(f"Error moving b5_obsidian.py: {e}")

    # 6. Remove backup folder in project workspace (the one copied to DST/backup)
    project_backup_dir = os.path.join(DST, "backup")
    if os.path.exists(project_backup_dir):
        try:
            shutil.rmtree(project_backup_dir, ignore_errors=True)
            print("Removed backup folder in project workspace.")
        except Exception as e:
            print(f"Error removing backup folder: {e}")

    print("==========================================")
    print("LIFECYCLE RESTORATION & CLEANUP COMPLETE  ")
    print("==========================================")

if __name__ == "__main__":
    main()
