import platform


def platform_name() -> str:
    system = platform.system()
    return system or "unknown"
