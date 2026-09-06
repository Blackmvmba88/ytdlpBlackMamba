"""Export only reviewed source roots; never include user data or old nested copies."""
from pathlib import Path
from zipfile import ZipFile, ZIP_DEFLATED
root = Path(__file__).resolve().parents[1]
roots = ['apps', 'shared', 'bin', 'config', 'tests', 'docs', 'packaging', '.github']
files = ['README.md', 'requirements.txt', 'requirements-lock.txt', '.gitignore', 'launcher.py']
out = root / 'dist/MambaFlow-0.2.0-source.zip'
out.parent.mkdir(exist_ok=True)
with ZipFile(out, 'w', ZIP_DEFLATED) as archive:
    for name in files:
        archive.write(root / name, 'MambaFlow/' + name)
    for name in roots:
        for path in (root / name).rglob('*'):
            if path.is_file() and '__pycache__' not in path.parts and path.suffix not in {'.pyc'} and path.name not in {'cookies.txt', '.DS_Store'}:
                archive.write(path, 'MambaFlow/' + path.relative_to(root).as_posix())
print(out)
