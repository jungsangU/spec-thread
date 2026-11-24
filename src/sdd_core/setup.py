"""User-facing install/update flow over official Spec Kit and existing Core APIs."""
import argparse
from contextlib import redirect_stderr
from importlib.metadata import version
import io
import json
import os
from pathlib import Path
import shlex
import subprocess
import sys

from . import __version__
from .baseline import scaffold, read_records, validate
from .version_sync import (PROJECT, RUNNER, apply_sync, install_skills, json_bytes,
                           plan_sync, read_marker, require_project, write_file)

SETUP = '.specify/spec-thread-install.json'
SPEC_KIT = '1.4.0'
IGNORED = {'.git', '.specify', '.agents', '.claude', '.codex', '.venv', 'venv', 'node_modules',
           '__pycache__', '.pytest_cache', '.mypy_cache', 'build', 'dist', '.next', 'coverage'}


def official(root, *args, capture=False):
    result = subprocess.run([sys.executable, '-c', 'import sys; from specify_cli import main; sys.exit(main())',
                             *args], cwd=root, capture_output=True, text=True)
    if capture:
        try:
            return json.loads(result.stdout)
        except ValueError:
            pass
    if result.returncode:
        raise ValueError('Spec Kit 단계에서 중단했습니다. 사용자 수정 파일을 강제로 덮어쓰지 않습니다.\n' +
                         (result.stderr + result.stdout)[-4000:])
    return json.loads(result.stdout) if capture else result.stdout


def official_state(root):
    return official(root, 'integration', 'status', '--json', capture=True)


def input_files(root):
    return sorted(path.relative_to(root).as_posix() for path in root.rglob('*')
                  if path.is_file() and not path.is_symlink()
                  and not IGNORED.intersection(path.relative_to(root).parts)
                  and path.suffix not in ('.pyc', '.log')
                  and path.name not in ('.DS_Store', '.coverage', 'coverage.xml', 'junit.xml')
                  and not (path.relative_to(root).as_posix() in ('monitor', 'monitor.cmd')
                           and 'SpecThread managed Monitor launcher' in path.read_bytes()[:100].decode(errors='ignore')))


def select_quality(root, saved, check, ask):
    features = read_records(root, 'features.yaml', 'features')
    active = [row for row in features if row.get('status', 'active') == 'active']
    command = shlex.split(check) if check else saved.get('check')
    if command is None and active:
        suggestion = ''
        package = root / 'package.json'
        if package.is_file() and json.loads(package.read_text()).get('scripts', {}).get('test'):
            suggestion = 'npm test'
        answer = ask('기존 앱을 확인할 테스트·빌드 명령' + (f' [{suggestion}]' if suggestion else '') + ': ').strip()
        command = shlex.split(answer or suggestion)
        if not command:
            raise ValueError('활성 Feature가 있는 업데이트에는 실제 프로젝트 검사 명령이 필요합니다')
    if command:
        paths = input_files(root)
        if not paths:
            raise ValueError('프로젝트 검사 입력 파일을 찾지 못했습니다')
        return command, [{'features': [], 'paths': paths, 'command': command}]
    paths = ['.specify/baseline/' + name for name in (
        'project.md', 'architecture.md', 'decisions.md', 'features.yaml', 'source-map.yaml', 'work-items.yaml')]
    return None, [{'features': [], 'paths': paths, 'command': [sys.executable, str(root / RUNNER),
                                                            '--root', str(root), 'validate']}]


def setup(root, action, agent, *, yes=False, check=None, ask=input, emit=print):
    root = root.resolve(strict=True)
    marker = read_marker(root, PROJECT)
    saved = read_marker(root, SETUP) or {}
    if action == 'install' and marker is not None:
        raise ValueError('이미 설치됐습니다. update 명령을 사용하세요')
    if action == 'update' and marker is None and not (root / '.specify/baseline').exists():
        raise ValueError('설치 기록이 없습니다. install 명령을 사용하세요')
    if marker and marker.get('agent') != agent:
        raise ValueError('업데이트 중에는 기존 프로젝트의 에이전트를 변경하지 않습니다')
    if version('specify-cli') != SPEC_KIT:
        raise ValueError('이 배포본의 전용 Spec Kit 1.4.0 환경으로 실행하세요')
    if agent not in ('codex', 'claude'):
        raise ValueError('Codex 또는 Claude Code를 선택하세요')
    had_baseline = (root / '.specify/baseline').exists()
    before = official_state(root) if (root / '.specify').is_dir() else None
    if before is None and any(root.glob('.agents/skills/speckit-*')):
        raise ValueError('설치 기록 없는 기존 Spec Kit Skill이 있습니다. 덮어쓰지 않습니다')
    if before is None and any(root.glob('.claude/skills/speckit-*')):
        raise ValueError('설치 기록 없는 기존 Spec Kit Skill이 있습니다. 덮어쓰지 않습니다')
    installed = before.get('installed_integrations', []) if before else []
    other = set(installed) - {agent}
    if other:
        raise ValueError('다른 Spec Kit 에이전트가 이미 등록돼 있습니다: ' + ', '.join(sorted(other)))
    if before and (before.get('modified_managed_files', 0) or before.get('invalid_manifest_paths', 0)):
        raise ValueError('사용자가 수정한 Spec Kit 파일이 있습니다. 원본과 변경을 확인한 뒤 같은 명령으로 다시 시도하세요')
    # Inspect known Core customizations before any official write during an update.
    from_version = None
    if action == 'update' and marker is None:
        from_version = ask('기존 설치의 Core 버전(확인한 값): ').strip()
        if from_version != '0.1.0':
            raise ValueError('표식 없는 설치는 확인한 0.1.0만 지원합니다. 출발 버전을 추정하지 않습니다')
    # Core preview needs an existing Baseline. New installs are scaffolded later.
    command = None
    quality = None
    if had_baseline:
        command, quality = select_quality(root, saved, check, ask)
        config = {'agent': agent, 'quality': quality}
        if from_version:
            config['from_version'] = from_version
        plan_sync(root, config)  # Read-only preflight: fail early on custom skills/schema.
    emit(f'{"신규 설치" if action == "install" else "업데이트"}: Spec Kit {SPEC_KIT} · SpecThread {__version__} · {agent}')
    emit('공식 Skill·SpecThread Skill·버전 기록을 준비하고 검사합니다. 앱 코드와 기존 명세·이력은 보존합니다.')
    if not yes:
        while True:
            answer = ask('적용할까요? y: 적용 / c: 앱 검사 명령 변경 / N: 취소 [N]: ').strip().lower()
            if answer == 'c':
                check = ask('새 테스트·빌드 명령: ').strip()
                if not check:
                    raise ValueError('새 검사 명령을 입력하세요')
                if had_baseline:
                    command, quality = select_quality(root, {}, check, ask)
                    config['quality'] = quality
                    plan_sync(root, config)
                continue
            if answer not in ('y', 'yes'):
                return {'status': 'cancelled'}
            break
    emit('1/3  Spec Kit 프로젝트 연동 확인')
    if before is None:
        official(root, 'init', '--here', '--force', '--integration', agent,
                 '--ignore-agent-tools', '--non-interactive', '--script', 'ps' if os.name == 'nt' else 'sh')
    elif agent not in installed:
        official(root, 'integration', 'install', agent)
    elif action == 'update':
        official(root, 'integration', 'upgrade', agent)
    state = official_state(root)
    if agent not in state.get('installed_integrations', []) or state.get('missing_managed_files', 0):
        raise ValueError('공식 Spec Kit Skill 설치를 확인할 수 없습니다')
    emit('2/3  SpecThread Skill·실행 환경 연결')
    if not had_baseline:
        install_skills(root, agent)
        scaffold(root)
        command, quality = select_quality(root, saved, check, ask)
    config = {'agent': agent, 'quality': quality}
    if from_version:
        config['from_version'] = from_version
    # Recompute after official setup. No human JSON plan or hash copy/paste is required.
    plan, outputs, features = plan_sync(root, config)
    # Preserve the selected real check even on failure; retries must not silently
    # downgrade an app quality failure to an empty-Baseline structural check.
    write_file(root, SETUP, json_bytes({'agent': agent, 'check': command}))
    emit('3/3  버전·구조·기존 프로젝트 검사')
    log = io.StringIO()
    with redirect_stderr(log):
        result = apply_sync(root, plan, outputs, features)
    if result['quality'] != 'passed':
        raise ValueError('업데이트 품질 검사를 통과하지 못했습니다.\n' + log.getvalue()[-4000:])
    validate(root)
    require_project(root, agent)
    final = official_state(root)
    if final.get('status') == 'error' or final.get('missing_managed_files', 0) or final.get('modified_managed_files', 0):
        raise ValueError('공식 설치 확인에서 문제가 남아 있습니다. 성공으로 기록하지 않습니다')
    write_file(root, SETUP, json_bytes({'agent': agent, 'core_version': __version__,
                                       'spec_kit_version': SPEC_KIT, 'check': command}))
    emit('완료했습니다. 사용하는 AI의 새 세션을 이 프로젝트에서 열어 주세요.')
    emit(('Codex: $sdd-init' if agent == 'codex' else 'Claude Code: /sdd-init') + ' 으로 프로젝트 분석을 시작할 수 있습니다.')
    return {'status': 'complete', 'agent': agent, 'core_version': __version__,
            'spec_kit_version': SPEC_KIT, 'runner': RUNNER}


def main(argv=None):
    parser = argparse.ArgumentParser(description='SpecThread install/update')
    parser.add_argument('command', choices=['install', 'update'])
    parser.add_argument('--project', type=Path, default=Path.cwd())
    parser.add_argument('--agent', choices=['codex', 'claude'], required=True)
    parser.add_argument('--yes', action='store_true')
    parser.add_argument('--check')
    args = parser.parse_args(argv)
    try:
        setup(args.project, args.command, args.agent, yes=args.yes, check=args.check)
    except (OSError, ValueError, KeyError, TypeError, EOFError, KeyboardInterrupt) as error:
        print(f'설치·업데이트를 완료하지 못했습니다: {error}\n실패 단계의 변경을 확인하세요. 자동 원복은 하지 않습니다.', file=sys.stderr)
        return 1
    return 0


if __name__ == '__main__':
    sys.exit(main())
