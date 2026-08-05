# -*- coding: utf-8 -*-
"""把 5 动物 GLB 写入 manifest.json 和 preview.html 的内嵌 manifest"""
import json, os, re

ANIMALS = [
    ('bird', '鸟(蓝灰)', 'P1', [0x9F, 0xB8, 0xC8]),
    ('Chick', '小鸡(黄)', 'P0', [0xFF, 0xC8, 0x4A]),
    ('Fish', '鱼(橙红)', 'P1', [0xFF, 0x6B, 0x35]),
    ('Red Fox', '红狐', 'P1', [0xE6, 0x4A, 0x29]),
    ('Whale', '鲸鱼(深蓝)', 'P0', [0x4A, 0x6B, 0x8A]),
]

# 写 manifest.json
with open('assets/manifest.json') as f:
    m = json.load(f)
m['assets'] = [a for a in m.get('assets', []) if not a.get('assetId', '').startswith('quaternius_5animal_')]
for i, (name, cn, pri, color) in enumerate(ANIMALS):
    path = f'assets/quaternius_animals5_glb/quaternius_{name}.glb'
    if not os.path.exists(path):
        print(f'  跳过 {name}（GLB 不存在）'); continue
    size_kb = round(os.path.getsize(path) / 1024, 1)
    m['assets'].append({
        'assetId': f'quaternius_5animal_{name.replace(" ", "_")}',
        'designId': f'QA5-{i+1:02d}',
        'path': path,
        'category': 'animal' if name != 'Fish' else 'fish',
        'priority': pri,
        'name': f'Quaternius {cn}',
        'sizeKB': size_kb,
        'source': 'cc0_quaternius',
        'license': 'CC0',
        'attribution': 'Quaternius (Animals Pack by Quaternius, 2016)',
        'color': list(color),
        'collision': {'type': 'dynamic', 'shape': 'sphere', 'params': {'radius': 0.4}},
        'loadPriority': 'lazy',
    })
with open('assets/manifest.json', 'w', encoding='utf-8') as f:
    json.dump(m, f, ensure_ascii=False, indent=2)
print(f'写入 manifest.json: +{len(ANIMALS)} 条，总计 {len(m["assets"])} 条')

# 更新 preview.html 内嵌 manifest
with open('preview.html', encoding='utf-8') as f:
    html = f.read()
m_pattern = re.compile(r'(<script id="manifest-data" type="application/json">)(.*?)(</script>)', re.DOTALL)
mobj = m_pattern.search(html)
embedded = json.loads(mobj.group(2))
embedded['assets'] = [a for a in embedded.get('assets', []) if not a.get('assetId', '').startswith('quaternius_5animal_')]
slim = [{
    'assetId': f'quaternius_5animal_{n.replace(" ", "_")}',
    'path': f'assets/quaternius_animals5_glb/quaternius_{n}.glb',
    'category': 'animal' if n != 'Fish' else 'fish',
    'priority': pri,
    'name': f'Quaternius {cn}',
    'designId': f'QA5-{i+1:02d}',
    'source': 'cc0_quaternius',
} for i, (n, cn, pri, _) in enumerate(ANIMALS)]
embedded['assets'].extend(slim)
new_json = json.dumps(embedded, ensure_ascii=False, indent=2)
new_html = html[:mobj.start(2)] + new_json + html[mobj.end(2):]
with open('preview.html', 'w', encoding='utf-8') as f:
    f.write(new_html)
print(f'更新 preview.html 内嵌 manifest: {len(embedded["assets"])} 条')
