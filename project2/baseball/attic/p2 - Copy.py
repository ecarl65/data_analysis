# Imports
from __future__ import division, print_function
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns

# Read input files
batting = pd.read_csv('Batting.csv')
master = pd.read_csv('Master.csv')

# Make the master be indexed by the player id, after verifying that they are truly unique
masterLen = len(master)
uniqIdLen = len(master.playerID.unique())
if masterLen == uniqIdLen:
    print("Master now indexed by playerID")
    masterNew = master.set_index('playerID')
else:
    print("Could not index master by player ID")


# Compute batting average
batting['AV'] = batting['H'] / (batting['AB'] + 1e-15)

# Create table with entries from last 20 years
batting_recent = batting[batting.yearID > 1994]
batting_recent.describe()

# Determine average for people with high at bats
# batting[batting['AB'] > 25].AV.hist(bins=25)

# Find maximum HRs
maxhridx = batting_recent['HR'].idxmax()
maxHr = batting_recent['HR'].max()
batting_recent.loc[maxhridx]
maxHrPlayerFirst = master.loc[master['playerID'] == batting_recent.loc[maxhridx].playerID].nameFirst.values[0]
maxHrPlayerLast = master.loc[master['playerID'] == batting_recent.loc[maxhridx].playerID].nameLast.values[0]
maxHrYear = batting_recent.loc[maxhridx].yearID
print("Player with max HR: {0} {1} in {2} with {3}".format(maxHrPlayerFirst, maxHrPlayerLast, maxHrYear, maxHr))

# Determine quantiles
# bins = np.arange(0.0, 1.0, 20)
bins = np.linspace(0.0, 0.5, num=25, endpoint=True)
year_quantile = []
num_quantiles = 5
increment = 1.0 / num_quantiles
batting_ab = batting[batting.AB > 25]
# plt.figure()
# for x in xrange(num_quantiles):
#     year_start = batting_ab['yearID'].quantile(increment * x)
#     year_stop = batting_ab['yearID'].quantile(increment * (x+1))
#     year_quantile.append((year_start, year_stop))
#     batting_quantile = batting_ab[(batting_ab.yearID > year_start) & (batting_ab.yearID <= year_stop)]
#     # batting_quantile['AB'].hist(alpha=0.5)
#     # hist, bin_edges = np.histogram(batting_quantile['AB'], bins=25, range=(0,725))
#     hist, bin_edges = np.histogram(batting_quantile['AV'], bins=bins)
#     x = (bin_edges[:-1] + bin_edges[1:]) / 2.0
#     plt.plot(x, hist / np.sum(hist), alpha=0.5)
#     plt.hold(True);
# plt.title('HR Histogram per year quantile')
# legend = ['first', 'second', 'third', 'fourth', 'fifth']
# plt.legend(legend[:num_quantiles])

# Alternate method using group by
year_quantile = [(batting_ab['yearID'].quantile(increment * x), batting_ab['yearID'].quantile(increment * (x+1))) for x in xrange(num_quantiles)]
yq = [x[0] for x in year_quantile]
yq.append(year_quantile[-1][-1])
batting_gb = batting_ab.groupby(pd.cut(batting_ab['yearID'], yq))
#print(batting_gb.AV.describe())
print(batting_gb.AV.std())
plt.figure()
batting_gb.AV.std().plot()
plt.title('Standard Deviation of Batting Average')
plt.xlabel('Year Range')
plt.ylabel('Standard Deviation')

plt.figure()
# res = batting_gb.AV.hist(bins=bins)  # Can modify res somehow to make lines?
for (group, df) in batting_gb:
    hist, bin_edges = np.histogram(df.AV, bins=bins)
    x = (bin_edges[:-1] + bin_edges[1:]) / 2.0
    plt.plot(x, hist / np.sum(hist), alpha = 0.5)
    plt.hold(True)
plt.title('Batting Average Histogram per Year Quantile')
legend = ['First', 'Second', 'Third', 'Fourth', 'Fifth', 'Sixth']
plt.legend(legend[:num_quantiles])
