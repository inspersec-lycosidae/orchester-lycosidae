from fastapi import HTTPException
import re
import socket

def sanitize_container_name(name: str) -> str:
    """
    Sanitize a string to be safe as a Docker container name.

    Replaces all characters that are not letters, numbers, hyphens, or underscores with underscores.
    
    Args:
        name (str): The original container name.
    
    Returns:
        str: A sanitized container name suitable for Docker.
    
    Raises:
        HTTPException: If the name is empty.
    """
    if not name:
        raise HTTPException(status_code=400, detail="Container name cannot be empty")
    return re.sub(r'[^a-zA-Z0-9_-]', '_', name)


def validate_time_alive(time_alive: int, max_seconds: int = 15552000) -> int:
    """
    Validate that time_alive is a positive integer within an allowed range.

    Ensures the value is greater than 0 and does not exceed max_seconds (default 6 months).
    
    Args:
        time_alive (int): The requested lifetime in seconds.
        max_seconds (int, optional): Maximum allowed lifetime in seconds. Defaults to 15552000 (6 months).
    
    Returns:
        int: The validated time_alive value.
    
    Raises:
        HTTPException: If time_alive is not a positive integer or exceeds max_seconds.
    """
    if not isinstance(time_alive, int) or time_alive < 0 or time_alive > max_seconds:
        raise HTTPException(
            status_code=400, 
            detail=f"time_alive must be between 1 and {max_seconds} seconds"
        )
    return time_alive

def find_free_port(start: int = 50000, end: int = 60000) -> int:
    """
    Find a free TCP port on the local machine within the given range.
    
    Args:
        start (int): Starting port number to check (inclusive). Default is 50000.
        end (int): Ending port number to check (exclusive). Default is 60000.
    
    Returns:
        int: A free port number.
    
    Raises:
        RuntimeError: If no free port is found in the given range.
    """
    for port in range(start, end):
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            if s.connect_ex(("0.0.0.0", port)) != 0:  # port is free
                return port
    raise RuntimeError(f"No free ports available in range {start}-{end}")