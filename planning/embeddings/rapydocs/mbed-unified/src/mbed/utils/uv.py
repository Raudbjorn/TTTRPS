"""
UV Package Manager integration
Provides 3-5x faster package installation than pip
"""

import subprocess
import sys
import shutil
import logging
from pathlib import Path
from typing import List, Optional, Dict, Any

logger = logging.getLogger(__name__)

class UVManager:
    """Manages UV package operations"""
    
    def __init__(self, venv_path: Optional[Path] = None):
        """
        Initialize UV manager
        
        Args:
            venv_path: Path to virtual environment (default: .venv)
        """
        self.venv_path = venv_path or Path(".venv")
        self.uv_binary = self._find_uv()
        
        if not self.uv_binary:
            self._install_uv()
    
    def _find_uv(self) -> Optional[str]:
        """Find UV binary"""
        uv_path = shutil.which("uv")
        if uv_path:
            logger.debug(f"Found UV at: {uv_path}")
            return uv_path
        return None
    
    def _install_uv(self):
        """Install UV if not present"""
        logger.info("UV not found, installing...")
        try:
            # Install UV using pip (bootstrap) with timeout
            subprocess.run(
                [sys.executable, "-m", "pip", "install", "uv"],
                check=True,
                capture_output=True,
                text=True,
                timeout=60  # 60 second timeout for installation
            )
            
            # Validate UV was installed correctly
            self.uv_binary = self._find_uv()
            if not self.uv_binary:
                raise RuntimeError("UV binary not found after installation")
            
            # Verify UV works by checking version
            version_check = subprocess.run(
                [self.uv_binary, "--version"],
                capture_output=True,
                text=True,
                timeout=5
            )
            
            if version_check.returncode != 0:
                raise RuntimeError(f"UV validation failed: {version_check.stderr}")
            
            logger.info(f"✅ UV installed successfully: {version_check.stdout.strip()}")
            
        except subprocess.TimeoutExpired:
            logger.error("UV installation timed out after 60 seconds")
            raise RuntimeError("UV installation timed out")
        except subprocess.CalledProcessError as e:
            logger.error(f"Failed to install UV: {e.stderr if hasattr(e, 'stderr') else str(e)}")
            raise RuntimeError(f"UV installation failed: {e}")
        except Exception as e:
            logger.error(f"Unexpected error during UV installation: {e}")
            raise
    
    def create_venv(self, python_version: Optional[str] = None) -> bool:
        """
        Create UV-managed virtual environment
        
        Args:
            python_version: Specific Python version (e.g., "3.11")
        
        Returns:
            True if successful
        """
        cmd = [self.uv_binary, "venv", str(self.venv_path)]
        
        if python_version:
            cmd.extend(["--python", python_version])
        
        try:
            result = subprocess.run(
                cmd,
                check=True,
                capture_output=True,
                text=True
            )
            logger.info(f"✅ Created virtual environment at {self.venv_path}")
            return True
        except subprocess.CalledProcessError as e:
            logger.error(f"Failed to create venv: {e.stderr}")
            return False
    
    def install_dependencies(self, 
                           requirements: Optional[List[str]] = None,
                           requirements_file: Optional[Path] = None,
                           extras: Optional[List[str]] = None,
                           editable: bool = False) -> bool:
        """
        Install packages using UV (3-5x faster than pip)
        
        Args:
            requirements: List of package specs
            requirements_file: Path to requirements file
            extras: Optional extras to install (e.g., ["cuda", "dev"])
            editable: Install in editable mode
        
        Returns:
            True if successful
        """
        cmd = [self.uv_binary, "pip", "install"]
        
        # Add packages
        if requirements:
            cmd.extend(requirements)
        
        # Add requirements file
        if requirements_file:
            cmd.extend(["-r", str(requirements_file)])
        
        # Add extras for editable install
        if editable:
            package_spec = "."
            if extras:
                package_spec = f".[{','.join(extras)}]"
            cmd.extend(["-e", package_spec])
        
        try:
            logger.info(f"Installing packages with UV...")
            result = subprocess.run(
                cmd,
                check=True,
                capture_output=True,
                text=True,
                timeout=300  # 5 minute timeout for package installation
            )
            
            # Log what was installed
            if result.stdout:
                installed = [line for line in result.stdout.split('\n') 
                           if 'Installing' in line or 'Installed' in line]
                for line in installed[:5]:  # Show first 5
                    logger.debug(line)
            
            logger.info("✅ Dependencies installed successfully")
            return True
            
        except subprocess.CalledProcessError as e:
            logger.error(f"Failed to install dependencies: {e.stderr}")
            return False
    
    def sync_dependencies(self, pyproject_path: Path = Path("pyproject.toml")) -> bool:
        """
        Sync dependencies from pyproject.toml
        
        Args:
            pyproject_path: Path to pyproject.toml
        
        Returns:
            True if successful
        """
        if not pyproject_path.exists():
            logger.warning(f"pyproject.toml not found at {pyproject_path}")
            return False
        
        try:
            cmd = [self.uv_binary, "pip", "sync", str(pyproject_path)]
            result = subprocess.run(
                cmd,
                check=True,
                capture_output=True,
                text=True
            )
            logger.info("✅ Dependencies synced from pyproject.toml")
            return True
        except subprocess.CalledProcessError as e:
            logger.error(f"Failed to sync dependencies: {e.stderr}")
            return False
    
    def list_installed(self) -> List[str]:
        """
        List installed packages
        
        Returns:
            List of installed package names with versions
        """
        try:
            result = subprocess.run(
                [self.uv_binary, "pip", "list"],
                check=True,
                capture_output=True,
                text=True
            )
            
            packages = []
            for line in result.stdout.strip().split('\n')[2:]:  # Skip header
                if line.strip():
                    packages.append(line.strip())
            
            return packages
            
        except subprocess.CalledProcessError:
            return []
    
    def check_package(self, package_name: str) -> bool:
        """
        Check if a package is installed
        
        Args:
            package_name: Name of package to check
        
        Returns:
            True if installed
        """
        installed = self.list_installed()
        return any(package_name.lower() in pkg.lower() for pkg in installed)
    
    def install_hardware_extras(self, hardware: str) -> bool:
        """
        Install hardware-specific extras
        
        Args:
            hardware: Hardware type (cuda, openvino, mps)
        
        Returns:
            True if successful
        """
        hardware_map = {
            'cuda': ['torch>=2.0', 'faiss-gpu>=1.7', 'nvidia-ml-py>=12.0'],
            'openvino': ['openvino>=2024.0', 'openvino-dev>=2024.0'],
            'mps': ['torch>=2.0', 'coremltools>=7.0'],
            'cpu': []  # No special requirements for CPU
        }
        
        packages = hardware_map.get(hardware, [])
        if not packages:
            logger.info(f"No special packages needed for {hardware}")
            return True
        
        logger.info(f"Installing {hardware} support packages...")
        return self.install_dependencies(requirements=packages)
    
    def run_script(self, script_name: str, args: Optional[List[str]] = None) -> subprocess.CompletedProcess:
        """
        Run a script using UV
        
        Args:
            script_name: Name of script to run
            args: Additional arguments
        
        Returns:
            Completed process result
        """
        cmd = [self.uv_binary, "run", script_name]
        if args:
            cmd.extend(args)
        
        return subprocess.run(cmd, capture_output=True, text=True)
    
    def get_info(self) -> Dict[str, Any]:
        """
        Get UV and environment information
        
        Returns:
            Dictionary with UV info
        """
        info = {
            'uv_binary': self.uv_binary,
            'venv_path': str(self.venv_path),
            'venv_exists': self.venv_path.exists()
        }
        
        # Get UV version
        try:
            result = subprocess.run(
                [self.uv_binary, "--version"],
                capture_output=True,
                text=True
            )
            if result.returncode == 0:
                info['uv_version'] = result.stdout.strip()
        except:
            pass
        
        # Count installed packages
        packages = self.list_installed()
        info['package_count'] = len(packages)
        
        return info

# Convenience functions
_manager: Optional[UVManager] = None

def get_uv_manager() -> UVManager:
    """Get or create global UV manager instance"""
    global _manager
    if _manager is None:
        _manager = UVManager()
    return _manager

def ensure_dependencies(packages: List[str]) -> bool:
    """
    Ensure packages are installed
    
    Args:
        packages: List of package specs
    
    Returns:
        True if all packages are available
    """
    manager = get_uv_manager()
    
    # Check if packages are installed
    missing = []
    for package in packages:
        # Extract package name (handle specs like "torch>=2.0")
        pkg_name = package.split('>=')[0].split('==')[0].split('<')[0].split('>')[0]
        if not manager.check_package(pkg_name):
            missing.append(package)
    
    if missing:
        logger.info(f"Installing missing packages: {missing}")
        return manager.install_dependencies(requirements=missing)
    
    return True

def setup_environment(hardware: Optional[str] = None) -> bool:
    """
    Setup complete environment for mbed
    
    Args:
        hardware: Optional hardware type to install extras for
    
    Returns:
        True if successful
    """
    manager = get_uv_manager()
    
    # Create venv if needed
    if not manager.venv_path.exists():
        if not manager.create_venv():
            return False
    
    # Install base dependencies
    if not manager.install_dependencies(editable=True):
        return False
    
    # Install hardware extras if specified
    if hardware and hardware != 'cpu':
        if not manager.install_hardware_extras(hardware):
            logger.warning(f"Failed to install {hardware} extras, continuing with CPU support")
    
    return True