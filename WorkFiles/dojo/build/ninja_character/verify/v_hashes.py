import json, hashlib, os, subprocess, sys
P = json.load(open('build/provenance.json'))
DL = r'C:\Users\Cody\Documents\Unreal Projects\DojoLab'
DG = r'C:\Users\Cody\Documents\Unreal Projects\DemoGame_1'
def h(p):
    m = hashlib.sha256()
    with open(p, 'rb') as f:
        for b in iter(lambda: f.read(1 << 20), b''): m.update(b)
    return m.hexdigest()
out = {'cpp': [], 'content_mismatch': [], 'content_src_mismatch': [], 'new': [], 'changed': []}
for e in P['cpp']:
    a, b = h(e['dst']), h(e['src'])
    out['cpp'].append([e['rel'], a == e['sha256'], b == e['sha256']])
changed_pk = {'/Game/Ninja/Blueprints/BP_NinjaGasp', '/Game/Ninja/Input/IMC_NinjaGasp'}
n = 0; srcmatch = 0; dstmatch = 0; overrides = []
for e in P['content']:
    n += 1
    a = h(e['dst']) if os.path.exists(e['dst']) else None
    if a == e['sha256']: dstmatch += 1
    else: out['content_mismatch'].append([e['package'], a, e['sha256'], e.get('from')])
    if os.path.exists(e['src']):
        b = h(e['src'])
        if b == e['sha256']: srcmatch += 1
        else: out['content_src_mismatch'].append([e['package'], e.get('from'), b[:12], e['sha256'][:12]])
out['content_n'] = n; out['content_dst_match'] = dstmatch; out['content_src_match'] = srcmatch
for e in P['new_files']:
    p = os.path.join(DL, e['file'])
    out['new'].append([e['file'], os.path.exists(p) and h(p) == e['sha256']])
for e in P['changed_files']:
    p = os.path.join(DL, e['file'])
    out['changed'].append([e['file'], h(p) == e['sha256_now'], h(p)[:16]])
gm = os.path.join(DL, 'Content/Dojo/Blueprints/GM_Dojo.uasset'); out['gm_dojo_unchanged'] = h(gm) == P['gm_dojo_sha256']
# all DojoLab Source files listed?
src_files = []
for r, ds, fs in os.walk(os.path.join(DL, 'Source')):
    for f in fs: src_files.append(os.path.relpath(os.path.join(r, f), DL).replace(os.sep, '/'))
listed = {e['rel'] for e in P['cpp']} | {e['file'] for e in P['new_files']}
out['source_unlisted'] = sorted(set(src_files) - listed)
# DemoGame_1 HEAD
out['dg_head'] = subprocess.run(['git', '--no-optional-locks', '-C', DG, 'rev-parse', 'HEAD'], capture_output=True, text=True).stdout.strip()
out['dg_branch'] = subprocess.run(['git', '--no-optional-locks', '-C', DG, 'rev-parse', '--abbrev-ref', 'HEAD'], capture_output=True, text=True).stdout.strip()
out['prov_head'] = P['demogame1']['head']
json.dump(out, open('verify/hashes.json', 'w'), indent=1)
print('cpp dst ok', sum(x[1] for x in out['cpp']), '/', len(out['cpp']), ' src ok', sum(x[2] for x in out['cpp']))
print('content', n, 'dst match', dstmatch, 'src match', srcmatch)
print('content dst mismatches', [(x[0], x[3]) for x in out['content_mismatch']])
print('content src mismatches', out['content_src_mismatch'][:10], len(out['content_src_mismatch']))
print('new', out['new']); print('changed', out['changed']); print('gm_dojo', out['gm_dojo_unchanged'])
print('unlisted source', out['source_unlisted'][:20])
print('heads', out['dg_branch'], out['dg_head'], out['prov_head'])
