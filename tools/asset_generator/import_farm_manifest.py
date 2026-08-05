# -*- coding: utf-8 -*-
"""7 个农场动物 → manifest + preview.html"""
import json, os, re

FARM = [
    ('Cow',    '牛(白)',       'P0', [0xE8, 0xE8, 0xE8]),
    ('Horse',  '马(棕)',       'P0', [0x8B, 0x4A, 0x2B]),
    ('Llama',  '羊驼(米)',     'P1', [0xF5, 0xE6, 0xD3]),
    ('Pig',    '猪(粉)',       'P1', [0xF0, 0xAA, 0xC0]),
    ('Pug',    '哈巴狗(棕)',   'P1', [0xC8, 0xA0, 0x6A]),
    ('Sheep',  '羊(白)',       'P1', [0xF0, 0xEC, 0xE0]),
    ('Zebra',  '斑马',         'P1', [0xF5, 0xF5, 0xF5]),
]

with open('assets/manifest.json') as f:
    m = json.load(f)
m['assets'] = [a for a in m.get('assets', []) if not a.get('assetId', '').startswith('quaternius_farm_')]
for i, (name, cn, pri, color) in enumerate(FARM):
    path = f'assets/quaternius_farm_animals_glb/quaternius_{name}.glb'
    if not os.path.exists(path): continue
    size_kb = round(os.path.getsize(path) / 1024, 1)
    m['assets'].append({
        'assetId': f'quaternius_farm_{name}',
        'designId': f'QFA-{i+1:02d}',
        'path': path,
        'category': 'animal',
        'priority': pri,
        'name': f'Quaternius {cn}',
        'sizeKB': size_kb,
        'source': 'cc0_quaternius',
        'license': 'CC0',
        'attribution': 'Quaternius (Farm Animals Pack)',
        'color': list(color),
        'collision': {'type': 'dynamic', 'shape': 'sphere', 'params': {'radius': 0.5}},
        'loadPriority': 'lazy',
    })
with open('assets/manifest.json', 'w', encoding='utf-8') as f:
    json.dump(m, f, ensure_ascii=False, indent=2)
print(f'manifest.json: 总计 {len(m["assets"])} 条')

# preview.html
with open('preview.html', encoding='utf-8') as f:
    html = f.read()
m_pattern = re.compile(r'(<script id="manifest-data" type="application/json">)(.*?)(</script>)', re.DOTALL)
mobj = m_pattern.search(html)
embedded = json.loads(mobj.group(2))
embedded['assets'] = [a for a in embedded.get('assets', []) if not a.get('assetId', '').startswith('quaternius_farm_')]
slim = [{
    'assetId': f'quaternius_farm_{n}',
    'path': f'assets/quaternius_farm_animals_glb/quaternius_{n}.glb',
    'category': 'animal', 'priority': pri,
    'name': f'Quaternius {cn}',
    'designId': f'QFA-{i+1:02d}',
    'source': 'cc0_quaternius',
} for i, (n, cn, pri, _) in enumerate(FARM)]
embedded['assets'].extend(slim)
new_json = json.dumps(embedded, ensure_ascii=False, indent=2)
new_html = html[:mobj.start(2)] + new_json + html[mobj.end(2):]
with open('preview.html', 'w', encoding='utf-8') as f:
    f.write(new_html)
print(f'preview.html: {len(embedded["assets"])} 条')
