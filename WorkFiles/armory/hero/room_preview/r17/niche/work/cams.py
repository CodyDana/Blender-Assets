import json,sys
D=sys.argv[1]
d=json.load(open(D+'/layout.json'))
d['cameras'] += [{'name':'CN_WestNiche','loc':[3.1,16.9,1.9],'look_at':[1.05,19.6,1.45],'lens_mm':30},
 {'name':'CN_EastNiche','loc':[8.9,16.9,1.9],'look_at':[10.95,19.6,1.45],'lens_mm':30}]
json.dump(d,open(D+'/layout_cams.json','w'),indent=1)
