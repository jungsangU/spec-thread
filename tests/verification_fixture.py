"""Explicit policy/procedure observations for isolated lifecycle fixtures."""
from pathlib import Path
from sdd_core.records import read_document, write_document
from sdd_core.verification import RISKS, empty_registry, profile_preview, apply_profile, record_step


def prepare(root, identifier):
    catalog = empty_registry()
    catalog.update(status='configured', reason='Fixture has only Work Item-specific checks', basis=['basis.md'])
    write_document(root, 'verification.yaml', catalog)
    plan = {'profile': 'standard', 'reason': 'Isolated existing-contract fixture',
            'risks': {key: False for key in RISKS}, 'basis': ['basis.md'],
            'findings': [{'assessment': 'SAFE', 'evidence': 'Concrete fixture source and specs'}]}
    apply_profile(root, identifier, profile_preview(root, identifier, plan))
    for feature in read_document(root, 'features.yaml')['features']:
        path = Path(root) / feature['spec_path'] / 'tasks.md'
        if not path.exists():
            path.write_text('- [x] T001 Verify fixture implementation\n', encoding='utf-8')
    for step, refs in [('plan', ['specs/a/plan.md']), ('tasks', ['specs/a/tasks.md']), ('implement', ['app.py'])]:
        record_step(root, identifier, step, {'status': 'done', 'conclusion': 'Observed isolated fixture artifact', 'evidence': refs})
