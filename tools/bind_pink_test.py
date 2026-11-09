"""Bind the existing test update in Cemu's title cache before launch."""
from pathlib import Path
import json,shutil,time,xml.etree.ElementTree as E,hashlib,subprocess
root=Path(r'C:/Users/evant/Documents/Codex/2026-10-25/files-mentioned-by-the-user-handoff/work')
build=root/'pink_drift_p2';test=root/'bcp_r4_test';app=Path(r'C:/Users/evant/AppData/Roaming/Cemu')
processes=json.loads(subprocess.check_output(['powershell','-NoProfile','-Command',"@(Get-Process Xapfish -ErrorAction SilentlyContinue | Select-Object -ExpandProperty Id) | ConvertTo-Json -Compress"],text=True) or '[]')
assert not processes,'Close Cemu first'
# Wait for the previous owned session cleanup to finish before rebinding.
previous=json.loads((test/'debug_process.json').read_text())['pid']
for _ in range(20):
 try:
  if json.loads((test/'cleanup_report.json').read_text()).get('test_pid')==previous:break
 except (FileNotFoundError,json.JSONDecodeError):pass
 time.sleep(.25)
else:raise RuntimeError('Previous session cleanup has not finished')
for row in json.loads((build/'install.json').read_text()):assert hashlib.sha256(Path(row['path']).read_bytes()).hexdigest()==row['sha256']
cache=app/'title_list_cache.xml';shutil.copy2(cache,build/'title_cache_before_pink.xml');tree=E.parse(cache);count=0
for item in tree.getroot().findall('title'):
 if item.get('titleId','').lower()=='0005000e1010ed00':
  item.find('path').text=str(test/'mlc/usr/title/0005000e/1010ed00');count+=1
assert count==1,('Expected one update entry',count)
tree.write(cache,encoding='utf-8',xml_declaration=True)
print('Prototype update path bound; launch debug_sandbox.py next')
