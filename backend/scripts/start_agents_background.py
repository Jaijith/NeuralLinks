"""
Start autonomous agents in the background
"""
import subprocess
import sys
import os
import time
from pathlib import Path

# Get backend directory
backend_dir = Path(__file__).parent.parent
script_path = backend_dir / "scripts" / "run_autonomous_agents.py"
log_path = backend_dir / "agents.log"

def start_agents_background():
    """Start agents in background"""
    print("🚀 Starting autonomous agents in background...")
    
    # Check if already running
    try:
        result = subprocess.run(
            ["pgrep", "-f", "run_autonomous_agents.py"],
            capture_output=True,
            text=True
        )
        if result.returncode == 0 and result.stdout.strip():
            print("⚠️  Agents are already running!")
            print(f"   PID: {result.stdout.strip()}")
            return
    except:
        pass
    
    # Start in background using nohup
    venv_python = backend_dir / "venv" / "bin" / "python"
    if not venv_python.exists():
        print("❌ Virtual environment not found!")
        print(f"   Expected: {venv_python}")
        sys.exit(1)
    
    # Change to backend directory and run with nohup
    os.chdir(backend_dir)
    
    # Use nohup to run in background
    with open(log_path, 'w') as log_file:
        process = subprocess.Popen(
            ["nohup", str(venv_python), str(script_path)],
            stdout=log_file,
            stderr=subprocess.STDOUT,
            cwd=str(backend_dir),
            preexec_fn=os.setsid  # Create new process group
        )
    
    # Wait a moment to check if it started
    time.sleep(3)
    
    # Check if process is still running
    try:
        process.poll()
        if process.returncode is None:
            print(f"✅ Agents started in background (PID: {process.pid})")
            print(f"📝 Logs: {log_path}")
            print("\nTo check status:")
            print("  python scripts/check_agents.py")
            print("\nTo view logs:")
            print(f"  tail -f {log_path}")
            print("\nTo stop:")
            print(f"  kill {process.pid}")
        else:
            print("❌ Failed to start agents. Check logs:")
            print(f"  cat {log_path}")
    except Exception as e:
        print(f"⚠️  Started but couldn't verify: {e}")
        print(f"📝 Check logs: {log_path}")

if __name__ == "__main__":
    start_agents_background()

