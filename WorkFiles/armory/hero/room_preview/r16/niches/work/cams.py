import json,sys
D=sys.argv[1]
d=json.load(open(D+'/layout.json'))
d['cameras'] += [{'name':'CN_WestNiche','loc':[4.9,16.9,2.1],'look_at':[1.0,19.5,1.8],'lens_mm':30},
 {'name':'CN_EastNiche','loc':[7.1,16.9,2.1],'look_at':[11.0,19.5,1.8],'lens_mm':30}]
json.dump(d,open(D+'/layout_cams.json','w'),indent=1)
