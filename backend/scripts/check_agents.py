"""
Check if autonomous agents are running
"""
import subprocess
import sys
import os

def check_agents_running():
    """Check if autonomous agent system is running"""
    try:
        # Use pgrep to find the process
        result = subprocess.run(
            ['pgrep', '-f', 'run_autonomous_agents.py'],
            capture_output=True,
            text=True
        )
        
        if result.returncode == 0:
            pids = result.stdout.strip().split('\n')
            if pids and pids[0]:
                return True, int(pids[0])
        
        return False, None
    except Exception:
        # Fallback: check for process using ps
        try:
            result = subprocess.run(
                ['ps', 'aux'],
                capture_output=True,
                text=True
            )
            for line in result.stdout.split('\n'):
                if 'run_autonomous_agents.py' in line and 'python' in line.lower():
                    parts = line.split()
                    if parts:
                        return True, int(parts[1])  # PID is second column
        except Exception:
            pass
        
        return False, None

if __name__ == "__main__":
    running, pid = check_agents_running()
    
    if running:
        print(f"✅ Autonomous agents are running (PID: {pid})")
        print("\nTo view logs (if running in background):")
        print("  tail -f backend/agents.log")
        print("\nTo stop:")
        print(f"  kill {pid}")
        sys.exit(0)
    else:
        print("❌ Autonomous agents are NOT running")
        print("\nTo start them:")
        print("  cd backend")
        print("  source venv/bin/activate")
        print("  python scripts/run_autonomous_agents.py")
        print("\nOr start in background:")
        print("  python scripts/start_agents_background.py")
        sys.exit(1)

