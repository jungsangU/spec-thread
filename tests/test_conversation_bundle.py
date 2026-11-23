import hashlib
from importlib.resources import files
import json
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

import yaml

from sdd_core.version_sync import ACTIVE, bundle, install_skills, require_skills, skill_marker


class ConversationBundleTest(unittest.TestCase):
    def test_both_agents_receive_self_contained_shared_protocol_in_three_native_skills(self):
        shared = files('sdd_core').joinpath('skills/_conversation.md').read_bytes()
        expected = bundle()
        for agent, folder in [('codex', '.agents'), ('claude', '.claude')]:
            with self.subTest(agent=agent), TemporaryDirectory() as temporary:
                root = Path(temporary)
                (root / '.specify').mkdir()
                install_skills(root, agent)
                installed = root / folder / 'skills'
                self.assertEqual(sorted(p.name for p in installed.iterdir() if p.is_dir()), sorted(ACTIVE))
                marker = json.loads((root / skill_marker(agent)).read_text())
                for name in ACTIVE:
                    content = (installed / name / 'SKILL.md').read_bytes()
                    self.assertEqual(content, expected[name])
                    self.assertEqual(content.count(shared), 1)
                    frontmatter = yaml.safe_load(content.decode().split('---', 2)[1])
                    self.assertEqual(frontmatter['name'], name)
                    self.assertEqual(marker['skills'][name], hashlib.sha256(content).hexdigest())
                require_skills(root, agent)

    def test_editing_installed_conversation_does_not_bypass_skill_integrity(self):
        with TemporaryDirectory() as temporary:
            root = Path(temporary)
            (root / '.specify').mkdir()
            install_skills(root, 'codex')
            path = root / '.agents/skills/sdd-init/SKILL.md'
            path.write_bytes(path.read_bytes() + b'\nuser change\n')
            with self.assertRaises(ValueError):
                require_skills(root, 'codex')
