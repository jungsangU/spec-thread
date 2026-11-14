import subprocess


def run_checks(root, checks):
    if not isinstance(checks, list) or not checks:
        raise ValueError("실행할 필수 검증 명령이 필요합니다")
    for command in checks:
        if not isinstance(command, list) or not command or any(
            not isinstance(argument, str) or not argument for argument in command
        ):
            raise ValueError("검증 명령은 비어 있지 않은 인자 배열이어야 합니다")
    for command in checks:
        result = subprocess.run(command, cwd=root)
        if result.returncode:
            raise ValueError(f"검증 실패 ({result.returncode}): {command[0]}")
