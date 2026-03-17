import os
import platform
import subprocess
import getpass
import logging

logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')
logger = logging.getLogger(__name__)

def setup_windows_task():
    """Sets up a Windows Scheduled Task for weight updates."""
    # Absolute path to the python executable and the script
    script_dir = os.path.dirname(os.path.abspath(__file__))
    workspace_dir = os.path.abspath(os.path.join(script_dir, '..', '..'))
    update_script = os.path.join(script_dir, "update_weights.py")
    
    # Needs to run in the workspace dir to find configs and modules
    action = f"powershell.exe -WindowStyle Hidden -Command \"set PYTHONPATH={workspace_dir}; python {update_script}\""
    
    task_name = "OpenClaw_Dynamic_Weights_Update"
    
    logger.info(f"Setting up Windows Scheduled Task: {task_name}")
    logger.info(f"Command: {action}")
    
    # Create the task using schtasks
    # Runs daily at 00:00 (Midnight)
    try:
        # First try to delete it if it exists
        subprocess.run(
            ["schtasks", "/delete", "/tn", task_name, "/f"], 
            capture_output=True, text=True
        )
        
        # Then create the new task
        result = subprocess.run([
            "schtasks", "/create",
            "/tn", task_name,
            "/tr", action,
            "/sc", "daily",
            "/st", "00:00",
            "/ru", getpass.getuser()
        ], capture_output=True, text=True, check=True)
        
        logger.info("Successfully created scheduled task.")
        logger.info(result.stdout)
        
    except subprocess.CalledProcessError as e:
        logger.error(f"Failed to create scheduled task: {e}")
        logger.error(f"Output: {e.output}")

def setup_linux_cron():
    """Sets up a Linux Cronjob for weight updates."""
    script_dir = os.path.dirname(os.path.abspath(__file__))
    workspace_dir = os.path.abspath(os.path.join(script_dir, '..', '..'))
    update_script = os.path.join(script_dir, "update_weights.py")
    
    # Run daily at midnight
    cron_job = f"0 0 * * * cd {workspace_dir} && PYTHONPATH={workspace_dir} python {update_script} >> {workspace_dir}/logs/weight_update.log 2>&1"
    
    logger.info("To setup the cronjob on Linux/macOS, run:")
    logger.info(f"(crontab -l 2>/dev/null; echo \"{cron_job}\") | crontab -")
    
    try:
        import crontab
        cron = crontab.CronTab(user=True)
        # Check if job exists
        existing_jobs = list(cron.find_command(update_script))
        
        if existing_jobs:
            logger.info("Cron job already exists. Updating it...")
            cron.remove_all(command=update_script)
            
        job = cron.new(command=f"cd {workspace_dir} && PYTHONPATH={workspace_dir} python {update_script} >> {workspace_dir}/logs/weight_update.log 2>&1")
        job.setall('0 0 * * *')
        cron.write()
        logger.info("Successfully installed cron job.")
    except ImportError:
        logger.info("Python 'python-crontab' package not found. Generating a script to do it manually...")
        with open(os.path.join(script_dir, "install_cron.sh"), "w") as f:
            f.write("#!/bin/bash\n")
            f.write(f"(crontab -l 2>/dev/null; echo \"{cron_job}\") | crontab -\n")
            f.write("echo 'Cron job installed.'\n")
        # make it executable
        os.chmod(os.path.join(script_dir, "install_cron.sh"), 0o755)
        logger.info("Run ./install_cron.sh to install.")

if __name__ == "__main__":
    system = platform.system()
    if system == "Windows":
        setup_windows_task()
    else:
        setup_linux_cron()
