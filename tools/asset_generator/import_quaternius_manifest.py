# -*- coding: utf-8 -*-
"""
把 26 个 Quaternius GLB 写入 manifest.json 和 preview.html 的内嵌 manifest
"""
import json, os, re

BUILDING_TEX = {
    '1Story': 'Light', '1Story_GableRoof': 'Light', '1Story_RoundRoof': 'Green',
    '1Story_Sign': 'Casino',
    '2Story': 'Blue', '2Story_2': 'Red', '2Story_Balcony': 'Yellow',
    '2Story_Center': 'Light2', '2Story_Columns': 'Grey', '2Story_Double': 'Dark',
    '2Story_GableRoof': 'Blue', '2Story_RoundRoof': 'Red', '2Story_Sidehouse': 'Light',
    '2Story_Sign': 'Casino', '2Story_Slim': 'DarkBlue', '2Story_Stairs': 'DarkPurple',
    '2Story_Wide': 'Light2', '2Story_Wide_2Doors': 'Dark',
    '3Story_Balcony': 'Grey', '3Story_Slim': 'DarkBlue', '3Story_Small': 'Yellow',
    '4Story': 'Dark', '4Story_Center': 'DarkPurple', '4Story_Wide_2Doors': 'Red',
    '4Story_Wide_2Doors_Roof': 'DarkPurple',
    '6Story_Stack': 'Light2',
}

CN_NAMES = {
    '1Story': '单层小屋', '1Story_GableRoof': '单层人字顶', '1Story_RoundRoof': '单层圆顶',
    '1Story_Sign': '单层招牌店',
    '2Story': '双层主楼', '2Story_2': '双层副楼', '2Story_Balcony': '双层阳台',
    '2Story_Center': '双层中央', '2Story_Columns': '双层廊柱', '2Story_Double': '双层双开',
    '2Story_GableRoof': '双层人字顶', '2Story_RoundRoof': '双层圆顶',
    '2Story_Sidehouse': '双层侧屋', '2Story_Sign': '双层招牌店',
    '2Story_Slim': '双层窄楼', '2Story_Stairs': '双层楼梯', '2Story_Wide': '双层宽楼',
    '2Story_Wide_2Doors': '双层宽门',
    '3Story_Balcony': '三层阳台', '3Story_Slim': '三层窄楼', '3Story_Small': '三层小楼',
    '4Story': '四层主楼', '4Story_Center': '四层中央', '4Story_Wide_2Doors': '四层宽门',
    '4Story_Wide_2Doors_Roof': '四层宽门带顶',
    '6Story_Stack': '六层叠楼',
}

PRIORITY = {
    **{n: 'P0' for n in ['1Story', '2Story', '2Story_GableRoof', '2Story_Wide', '3Story_Small', '4Story', '6Story_Stack']},
    **{n: 'P1' for n in ['1Story_GableRoof', '1Story_RoundRoof', '1Story_Sign', '2Story_2', '2Story_Balcony', '2Story_Center', '2Story_Columns', '2Story_Double', '2Story_RoundRoof', '2Story_Sidehouse', '2Story_Sign', '2Story_Slim', '2Story_Stairs', '2Story_Wide_2Doors', '3Story_Balcony', '3Story_Slim', '4Story_Center', '4Story_Wide_2Doors', '4Story_Wide_2Doors_Roof']},
}

HEIGHTS = {
    '1Story': 2.4, '1Story_GableRoof': 3.0, '1Story_RoundRoof': 2.6, '1Story_Sign': 2.6,
    '2Story': 4.0, '2Story_2': 4.0, '2Story_Balcony': 4.2, '2Story_Center': 4.0,
    '2Story_Columns': 4.0, '2Story_Double': 4.0, '2Story_GableRoof': 4.4, '2Story_RoundRoof': 4.4,
    '2Story_Sidehouse': 4.0, '2Story_Sign': 4.4, '2Story_Slim': 4.0, '2Story_Stairs': 4.4,
    '2Story_Wide': 4.0, '2Story_Wide_2Doors': 4.0,
    '3Story_Balcony': 6.0, '3Story_Slim': 6.0, '3Story_Small': 6.0,
    '4Story': 8.0, '4Story_Center': 8.0, '4Story_Wide_2Doors': 8.0, '4Story_Wide_2Doors_Roof': 8.0,
    '6Story_Stack': 12.0,
}

def make_entry(name, design_id):
    path = f'assets/quaternius_glb/building_quaternius_{name}.glb'
    size_kb = round(os.path.getsize(path) / 1024, 1)
    h = HEIGHTS.get(name, 3.0)
    return {
        'assetId': f'building_quaternius_{name}',
        'designId': f'QB-{design_id:02d}',
        'path': path,
        'category': 'building',
        'priority': PRIORITY.get(name, 'P1'),
        'name': f'Quaternius {CN_NAMES.get(name, name)}',
        'sizeKB': size_kb,
        'source': 'cc0_quaternius',
        'license': 'CC0',
        'attribution': 'Quaternius (Ultimate Textured Building Pack, Dec 2019)',
        'collision': {'type': 'fixed', 'shape': 'box', 'params': {'width': 2.2, 'height': h, 'depth': 2.4}},
        'loadPriority': 'lazy',
    }

entries = [make_entry(name, i+1) for i, name in enumerate(BUILDING_TEX.keys())]

# 1. manifest.json
with open('assets/manifest.json') as f:
    m = json.load(f)
m['assets'] = [a for a in m.get('assets', []) if not a.get('assetId', '').startswith('building_quaternius_')]
m['assets'].extend(entries)
with open('assets/manifest.json', 'w', encoding='utf-8') as f:
    json.dump(m, f, ensure_ascii=False, indent=2)
print(f'写入 manifest.json: +{len(entries)} 条，总计 {len(m["assets"])} 条')

# 2. preview.html 内嵌 manifest
with open('preview.html', encoding='utf-8') as f:
    html = f.read()
m_pattern = re.compile(r'(<script id="manifest-data" type="application/json">)(.*?)(</script>)', re.DOTALL)
mobj = m_pattern.search(html)
embedded = json.loads(mobj.group(2))
embedded['assets'] = [a for a in embedded.get('assets', []) if not a.get('assetId', '').startswith('building_quaternius_')]
slim = [{'assetId': e['assetId'], 'path': e['path'], 'category': e['category'],
         'priority': e['priority'], 'name': e['name'], 'designId': e['designId'],
         'source': e['source']} for e in entries]
embedded['assets'].extend(slim)
new_json = json.dumps(embedded, ensure_ascii=False, indent=2)
new_html = html[:mobj.start(2)] + new_json + html[mobj.end(2):]
with open('preview.html', 'w', encoding='utf-8') as f:
    f.write(new_html)
print(f'更新 preview.html 内嵌 manifest: {len(embedded["assets"])} 条')
