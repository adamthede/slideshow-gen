# test-fixtures

Tiny synthetic JPEG fixtures for the Epic 1 sidecar smoke test (`useSidecar` + `start_scan` + frozen sidecar end-to-end).

Image files are **gitignored** — generate them locally with:

```bash
source ../../.venv/bin/activate
python -c "
from PIL import Image
for i, c in enumerate(['red','green','blue','yellow','magenta']):
    Image.new('RGB',(1200,900),color=c).save(
        f'2026-05-23 12-0{i}-00 - fixture.jpg', quality=80
    )
"
```

These are deliberately tiny solid-color JPEGs — the goal is to exercise the IPC pipeline, not test rendering. Real-world image fixtures are not committed because:

1. Binary churn in git.
2. License risk on any photos with identifiable subjects.
3. The pipeline doesn't care about image content during `--estimate-only`.
