import subprocess


class CheckFailure(ValueError):
    def __init__(self, result):
        self.result = result
        super().__init__(f"검증 실패 ({result['exit_code']}): {result['command'][0]}")


def check_commands(checks):
    if not isinstance(checks, list) or not checks:
        raise ValueError("실행할 필수 검증 명령이 필요합니다")
    for command in checks:
        if not isinstance(command, list) or not command or any(
            not isinstance(argument, str) or not argument for argument in command
        ):
            raise ValueError("검증 명령은 비어 있지 않은 인자 배열이어야 합니다")


def run_checks(root, checks):
    check_commands(checks)
    results = []
    for command in checks:
        process = subprocess.run(command, cwd=root, capture_output=True, text=True, errors="replace")
        result = {"command": command, "exit_code": process.returncode,
                  "stdout": process.stdout, "stderr": process.stderr}
        results.append(result)
        if process.returncode:
            raise CheckFailure(result)
    return results
