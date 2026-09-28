import pickle, sys
sys.path.insert(0, ".")
import wd_cutdiag as CD, wd_score as SC
wd = pickle.load(open(SC.OUT + "/" + sys.argv[1] + "_wd.pkl", "rb"))
print("weaves:", len(wd.weaves))
for row in CD.diag(wd):
    print(row)
