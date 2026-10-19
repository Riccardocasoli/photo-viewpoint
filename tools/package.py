"""Build an installable ZIP. --release checks public maintainer information."""
import argparse,ast,configparser,json,zipfile
from pathlib import Path

root=Path(__file__).resolve().parents[1]
parser=argparse.ArgumentParser()
parser.add_argument('--release',action='store_true')
parser.add_argument('--email')
parser.add_argument('--repository')
parser.add_argument('--homepage')
args=parser.parse_args()
metadata=configparser.ConfigParser()
# QGIS metadata keys are case-sensitive. Preserve their documented spelling.
metadata.optionxform=str
metadata.read(root/'metadata.txt', encoding='utf-8')
section=metadata['general']
if args.email:section['email']=args.email
if args.repository:
    section['repository']=args.repository.rstrip('/')
    section['tracker']=args.repository.rstrip('/')+'/issues'
if args.homepage:section['homepage']=args.homepage
if args.release:
    for key in ('email','repository','homepage'):
        value=section.get(key,'')
        if not value or (key=='email' and '@' not in value) or (key!='email' and not value.startswith('https://')):
            parser.error('Provide real maintainer metadata: '+key)
    if not (root/'LICENSE').is_file():parser.error('LICENSE is missing')
for path in root.glob('*.py'):ast.parse(path.read_text())
json.loads((root/'i18n/en.json').read_text())
output=root/'dist';output.mkdir(exist_ok=True)
archive=output/('prese_fotografiche_v'+section['version']+'.zip')
with zipfile.ZipFile(archive,'w',zipfile.ZIP_DEFLATED) as z:
    for path in sorted(root.rglob('*')):
        relative=path.relative_to(root)
        if not path.is_file() or any(part in ('dist','__pycache__','.git') for part in relative.parts):continue
        if args.release and ('.github' in relative.parts or 'tools' in relative.parts
                            or path.name.startswith(('test_', 'smoke_test_'))):continue
        if relative.as_posix()=='metadata.txt':
            import io
            text=io.StringIO();metadata.write(text);z.writestr('prese_fotografiche/metadata.txt',text.getvalue())
        else:z.write(path,'prese_fotografiche/'+relative.as_posix())
print(archive)
