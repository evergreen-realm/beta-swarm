import sys
import os
import importlib.machinery
import types
import inspect
import dis

workspace = r"c:\Users\Admin\Documents\Beta Swarnv2"
sys.path.insert(0, workspace)

pyc_dir_api = r"c:\Users\Admin\Documents\Beta Swarnv2\beta_swarm\tools\api_stack\__pycache__"
pyc_dir_sentry = r"c:\Users\Admin\Documents\Beta Swarnv2\beta_swarm\sentry\__pycache__"
pyc_dir_web = r"c:\Users\Admin\Documents\Beta Swarnv2\beta_swarm\tools\web\__pycache__"
pyc_path_base = r"c:\Users\Admin\Documents\Beta Swarnv2\beta_swarm\agents\__pycache__\base.cpython-311.pyc"
pyc_path_s2 = r"c:\Users\Admin\Documents\Beta Swarnv2\beta_swarm\agents\stage\__pycache__\s2_research.cpython-311.pyc"

def load_and_register(name, pyc_path):
    loader = importlib.machinery.SourcelessFileLoader(name, pyc_path)
    mod = loader.load_module()
    sys.modules[name] = mod
    return mod

try:
    # 1. Setup api_stack package
    api_stack_pkg = types.ModuleType("beta_swarm.tools.api_stack")
    api_stack_pkg.__path__ = [r"c:\Users\Admin\Documents\Beta Swarnv2\beta_swarm\tools\api_stack"]
    sys.modules["beta_swarm.tools.api_stack"] = api_stack_pkg
    load_and_register("beta_swarm.tools.api_stack", os.path.join(pyc_dir_api, "__init__.cpython-311.pyc"))
    load_and_register("beta_swarm.tools.api_stack.config", os.path.join(pyc_dir_api, "config.cpython-311.pyc"))
    load_and_register("beta_swarm.tools.api_stack.api_router", os.path.join(pyc_dir_api, "api_router.cpython-311.pyc"))
    load_and_register("beta_swarm.tools.api_stack.router", os.path.join(pyc_dir_api, "router.cpython-311.pyc"))

    # 2. Setup sentry package
    sentry_pkg = types.ModuleType("beta_swarm.sentry")
    sentry_pkg.__path__ = [r"c:\Users\Admin\Documents\Beta Swarnv2\beta_swarm\sentry"]
    sys.modules["beta_swarm.sentry"] = sentry_pkg
    load_and_register("beta_swarm.sentry", os.path.join(pyc_dir_sentry, "__init__.cpython-311.pyc"))
    load_and_register("beta_swarm.sentry.bugsink_client", os.path.join(pyc_dir_sentry, "bugsink_client.cpython-311.pyc"))

    # 3. Setup web tools package and direct tools module
    tools_pkg = types.ModuleType("beta_swarm.tools")
    tools_pkg.__path__ = [r"c:\Users\Admin\Documents\Beta Swarnv2\beta_swarm\tools"]
    sys.modules["beta_swarm.tools"] = tools_pkg
    
    web_pkg = types.ModuleType("beta_swarm.tools.web")
    web_pkg.__path__ = [r"c:\Users\Admin\Documents\Beta Swarnv2\beta_swarm\tools\web"]
    sys.modules["beta_swarm.tools.web"] = web_pkg
    load_and_register("beta_swarm.tools.web", os.path.join(pyc_dir_web, "__init__.cpython-311.pyc"))
    
    # Map browser_tool directly to beta_swarm.tools.browser_tool
    load_and_register("beta_swarm.tools.browser_tool", os.path.join(pyc_dir_web, "browser_tool.cpython-311.pyc"))

    # 4. Setup agents package
    agents_pkg = types.ModuleType("beta_swarm.agents")
    agents_pkg.__path__ = [r"c:\Users\Admin\Documents\Beta Swarnv2\beta_swarm\agents"]
    sys.modules["beta_swarm.agents"] = agents_pkg
    load_and_register("beta_swarm.agents.base", pyc_path_base)

    # 5. Load s2_research pyc
    stage_pkg = types.ModuleType("beta_swarm.agents.stage")
    stage_pkg.__path__ = [r"c:\Users\Admin\Documents\Beta Swarnv2\beta_swarm\agents\stage"]
    sys.modules["beta_swarm.agents.stage"] = stage_pkg
    s2_mod = load_and_register("beta_swarm.agents.stage.s2_research", pyc_path_s2)
    
    print("SUCCESS loading s2_research.pyc!")
    print("Attributes inside s2_research module:", dir(s2_mod))
    
    # Get the research agent class
    classes = [c for c in dir(s2_mod) if "Research" in c or "Agent" in c]
    print("Identified class names:", classes)
    
    for cls_name in classes:
        cls = getattr(s2_mod, cls_name)
        print(f"\nDetails for class {cls_name}:")
        for name, member in inspect.getmembers(cls):
            if not name.startswith("__"):
                try:
                    sig = inspect.signature(member)
                    print(f"  {name}{sig}")
                except Exception:
                    print(f"  {name}: {type(member)}")
                    
        # Let's disassemble the methods and save it to a text file
        print(f"\n--- Disassembling {cls_name} methods ---")
        out_dis_path = os.path.join(workspace, "s2_research_disassembly.txt")
        with open(out_dis_path, "w", encoding="utf-8") as f_out:
            for name, member in inspect.getmembers(cls):
                if not name.startswith("__") and inspect.isfunction(member):
                    f_out.write(f"\nDisassembly of {name}:\n")
                    # Capture stdout of dis.dis
                    import io
                    old_stdout = sys.stdout
                    sys.stdout = io.StringIO()
                    try:
                        dis.dis(member)
                        f_out.write(sys.stdout.getvalue())
                    except Exception as ex:
                        f_out.write(str(ex) + "\n")
                    finally:
                        sys.stdout = old_stdout
                    f_out.write("="*50 + "\n")
        print("DISASSEMBLY SAVED SUCCESSFULLY to s2_research_disassembly.txt")
                
except Exception as e:
    print("FAILED")
    print(e)
