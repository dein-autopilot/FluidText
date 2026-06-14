import PyInstaller.__main__
import os
import shutil
import sys
import site

# Define paths (absolute)
base_dir = os.path.dirname(os.path.abspath(__file__))
execution_dir = os.path.join(base_dir, "execution")
dist_dir = os.path.join(base_dir, "dist")
build_dir = os.path.join(base_dir, "build")

# Ensure execution dir is in path
sys.path.insert(0, execution_dir)

# Clean previous builds
if os.path.exists(dist_dir):
    try:
        shutil.rmtree(dist_dir)
    except Exception as e:
        print(f"Warning: Could not remove dist_dir: {e}")

if os.path.exists(build_dir):
    try:
        shutil.rmtree(build_dir)
    except Exception as e:
        print(f"Warning: Could not remove build_dir: {e}")

print(f"Starting PyInstaller Build in {execution_dir}...")

# Change directory to execution_dir to ensure imports work correctly
os.chdir(execution_dir)

PyInstaller.__main__.run([
    'main.py',  # Relative to CWD (execution_dir)
    '--name=FluidText',
    '--onedir',
    '--noconsole',
    '--noupx',
    '--clean',
    
    # Path configuration
    f'--paths={execution_dir}',
    f'--distpath={dist_dir}',
    f'--workpath={build_dir}',
    f'--specpath={base_dir}',
    
    # Local Modules (Force inclusion)
    '--hidden-import=gui_dashboard',
    '--hidden-import=gui_overlay',
    f'--icon={os.path.join(execution_dir, "assets", "icon.ico")}',
    '--hidden-import=transcriber',
    '--hidden-import=audio_capture',
    '--hidden-import=injector',
    '--hidden-import=settings_manager',
    '--hidden-import=utils',
    '--hidden-import=generate_logo',
    
    # Dependencies
    '--hidden-import=customtkinter',
    '--hidden-import=faster_whisper',
    '--hidden-import=huggingface_hub',
    '--hidden-import=huggingface_hub.utils',
    '--hidden-import=huggingface_hub.file_download',
    '--hidden-import=tqdm',
    '--hidden-import=tqdm.auto',
    '--hidden-import=keyboard',
    '--hidden-import=appdirs',
    '--hidden-import=pystray',
    '--hidden-import=PIL',
    '--hidden-import=PIL._tkinter_finder',
    # Platform abstraction layer (Windows adapters; mac adapters are unused here)
    '--hidden-import=platform_support',
    '--hidden-import=platform_support.hotkey_windows',
    '--hidden-import=platform_support.autostart_windows',
    '--hidden-import=sounddevice',
    '--hidden-import=certifi',
    '--hidden-import=requests',
    '--hidden-import=urllib3',
    '--hidden-import=filelock',
    '--hidden-import=fsspec',
    '--hidden-import=packaging',
    '--hidden-import=packaging.version',
    '--hidden-import=packaging.requirements',
    
    # Asset Collection
    '--collect-all=customtkinter',
    '--collect-all=faster_whisper',
    '--collect-all=huggingface_hub',
    '--collect-all=pystray',
    '--collect-data=certifi',
    f'--add-data={os.path.join(execution_dir, "assets")}' + os.pathsep + 'assets',
])

print("\n------------------------------------------------")
print("Post-Build: Copying NVIDIA DLLs manually...")

# IMPORTANT: Must match the --name argument above
target_dir = os.path.join(dist_dir, "FluidText", "_internal")

if not os.path.exists(target_dir):
    print(f"[WARN] Target dir {target_dir} does not exist. Creating...")
    os.makedirs(target_dir, exist_ok=True)

copied_count = 0
found_nvidia = False

# We search for ANY dll inside nvidia package
for site_pkg in site.getsitepackages():
    nvidia_base = os.path.join(site_pkg, "nvidia")
    if os.path.exists(nvidia_base):
        print(f"Scanning NVIDIA package at: {nvidia_base}")
        for root, dirs, files in os.walk(nvidia_base):
            for file in files:
                if file.endswith(".dll"):
                    full_src = os.path.join(root, file)
                    try:
                        shutil.copy2(full_src, target_dir)
                        print(f"  [COPY] {file}")
                        copied_count += 1
                    except Exception as e:
                        print(f"  [ERROR] Failed to copy {file}: {e}")
        found_nvidia = True
        break

if not found_nvidia:
    print("[ERROR] Could not find nvidia package in site-packages!")

print("\n------------------------------------------------")
print("Post-Build: Copying source files to guarantees imports...")
source_files = [f for f in os.listdir(execution_dir) if f.endswith('.py') and f != 'main.py']
for f in source_files:
    src = os.path.join(execution_dir, f)
    dst = os.path.join(target_dir, f)
    shutil.copy2(src, dst)
    print(f"  [COPY Source] {f}")

# Copy the platform_support package as well (it's a subdir, not caught above)
ps_src = os.path.join(execution_dir, "platform_support")
if os.path.isdir(ps_src):
    ps_dst = os.path.join(target_dir, "platform_support")
    shutil.copytree(ps_src, ps_dst, dirs_exist_ok=True,
                    ignore=shutil.ignore_patterns("__pycache__"))
    print("  [COPY Source] platform_support/")

print("\n------------------------------------------------")
print(f"Build Finished! Executable is at: {dist_dir}\\FluidText\\FluidText.exe")
print("------------------------------------------------")
