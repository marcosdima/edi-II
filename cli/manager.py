import shutil
import subprocess

from .config import Colors


class DockerManager:
    """Manages Docker Compose container lifecycle and inspection."""

    @staticmethod
    def _check_docker() -> bool:
        """Verifies if docker and docker-compose are available."""
        if not shutil.which("docker"):
            print(Colors.err("'docker' command not found. Ensure Docker is installed and in PATH."))
            return False
        return True

    @classmethod
    def run_compose_cmd(
        cls,
        args: list[str],
        capture_output: bool = False,
    ) -> subprocess.CompletedProcess[str]:
        """Runs a docker compose command."""
        if not cls._check_docker():
            return subprocess.CompletedProcess(args, 1, "", "docker not found")

        cmd = ["docker", "compose", *args]
        return subprocess.run(
            cmd,
            text=True,
            capture_output=capture_output,
            check=False,
        )

    @classmethod
    def status(cls) -> int:
        """Displays status of the container stack."""
        print(Colors.header("Container Stack Status"))
        proc = cls.run_compose_cmd(["ps"])
        return proc.returncode

    @classmethod
    def start(cls, build: bool = False) -> int:
        """Starts containers in detached mode, optionally rebuilding images."""
        action = "Starting containers (with rebuild)..." if build else "Starting containers..."
        print(Colors.info(action))
        args = ["up", "-d"]
        if build:
            args.append("--build")
        proc = cls.run_compose_cmd(args)
        if proc.returncode == 0:
            print(Colors.ok("Containers started successfully."))
            cls.status()
        else:
            print(Colors.err("Failed to start containers."))
        return proc.returncode

    @classmethod
    def stop(cls) -> int:
        """Stops and removes active containers."""
        print(Colors.info("Stopping container stack..."))
        proc = cls.run_compose_cmd(["down"])
        if proc.returncode == 0:
            print(Colors.ok("Containers stopped."))
        else:
            print(Colors.err("Failed to stop containers."))
        return proc.returncode

    @classmethod
    def restart(cls, service: str | None = None) -> int:
        """Restarts a specific container or all containers."""
        target = service if service else "all containers"
        print(Colors.info(f"Restarting {target}..."))
        args = ["restart"]
        if service:
            args.append(service)
        proc = cls.run_compose_cmd(args)
        if proc.returncode == 0:
            print(Colors.ok(f"Restarted {target}."))
            cls.status()
        else:
            print(Colors.err(f"Failed to restart {target}."))
        return proc.returncode

    @classmethod
    def logs(
        cls,
        service: str | None = None,
        tail: int = 50,
        follow: bool = False,
    ) -> int:
        """Views logs from containers."""
        target = service if service else "all services"
        print(Colors.header(f"Recent Logs ({target})"))
        args = ["logs", f"--tail={tail}"]
        if follow:
            args.append("-f")
        if service:
            args.append(service)

        try:
            proc = cls.run_compose_cmd(args)
            return proc.returncode
        except KeyboardInterrupt:
            print("\n" + Colors.info("Stopped viewing logs."))
            return 0
