# Imports
from __future__ import division, print_function
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.mlab as mlab
# import seaborn as sns
from scipy.stats import norm
import pdb

# Read input files
batting = pd.read_csv('Batting.csv')
# master = pd.read_csv('Master.csv')
app = pd.read_csv('Appearances.csv')
pop = pd.read_csv('population.csv', index_col=0).sort_index()
teams = pd.read_csv("Teams.csv")

batting = batting[batting.yearID >= 1900]
batting.index = np.arange(len(batting))

# Make the master be indexed by the player id, after verifying that they are truly unique
# masterLen = len(master)
# uniqIdLen = len(master.playerID.unique())
# if masterLen == uniqIdLen:
#     print("Master now indexed by playerID")
#     masterNew = master.set_index('playerID')
# else:
#    Print("Could not index master by player ID")

# Compute batting average
batting['AV'] = batting['H'] / (batting['AB'] + 1e-15)

# # Create table with entries from last 20 years
# batting_recent = batting[batting.yearID > 1994]
# batting_recent.describe()
# 
# # Find maximum HRs
# maxhridx = batting_recent['HR'].idxmax()
# maxHr = batting_recent['HR'].max()
# batting_recent.loc[maxhridx]
# maxHrPlayerFirst = master.loc[master['playerID'] == batting_recent.loc[maxhridx].playerID].nameFirst.values[0]
# maxHrPlayerLast = master.loc[master['playerID'] == batting_recent.loc[maxhridx].playerID].nameLast.values[0]
# maxHrYear = batting_recent.loc[maxhridx].yearID
# print("Player with max HR: {0} {1} in {2} with {3}".format(maxHrPlayerFirst, maxHrPlayerLast, maxHrYear, maxHr))

# Determine year quantiles
numBins = 25
num_quantiles = 3
minAtBats = 25

increment = 1.0 / num_quantiles
batting_ab = batting[batting.AB > minAtBats]
year_quantile = [(batting_ab['yearID'].quantile(increment * x), 
                  batting_ab['yearID'].quantile(increment * (x+1))) 
                  for x in xrange(num_quantiles)]
yq = [x[0] for x in year_quantile]
yq.append(year_quantile[-1][-1])

# Group by year quantiles
batting_gb = batting_ab.groupby(pd.cut(batting_ab['yearID'], yq))
# print(batting_gb.AV.describe())
# print(batting_gb.AV.std())

# Plot standard deviation for batting average over year quantiles
plt.figure()
batting_gb.AV.std().plot()
plt.title('Standard Deviation of Batting Average')
plt.xlabel('Year Range')
plt.ylabel('Standard Deviation')

# Plot histograms for batting average for quantiles
plt.figure()
bins = np.linspace(0.0, 0.5, num=numBins, endpoint=True)
x = (bins[:-1] + bins[1:]) / 2.0
# res = batting_gb.AV.hist(bins=bins)  # Can modify res somehow to make lines?
for (group, df) in batting_gb:
    hist, bin_edges = np.histogram(df.AV, bins=bins, density=True)
    plt.plot(x, hist)
    plt.hold(True)
plt.title('Batting Average Histogram per Year Quantile')
legend = ['First', 'Second', 'Third', 'Fourth', 'Fifth', 'Sixth']
plt.legend(legend[:num_quantiles])
plt.xlabel('Batting Average')
plt.ylabel('Normalized Histogram')

# Add new column for player position
# Group by new position indicator
batting_recent = batting[batting.yearID > 1994]
app_gb = app.groupby('playerID').sum()
app_gb['POS'] = 'other'
app_gb.loc[app_gb['G_1b'] > app_gb['G_ss'], 'POS'] = 'firstbase'
app_gb.loc[app_gb['G_1b'] < app_gb['G_ss'], 'POS'] = 'shortstop'

# Merge tables and group by position
merged = pd.merge(batting_recent, app_gb, how='left', left_on='playerID', 
                  right_index=True)
mgb = merged.groupby('POS')

# mgb.AV.hist()
plt.figure()
bins = np.arange(0, 80, 5)
x = (bins[:-1] + bins[1:]) / 2.0
leg = []
for (group, df) in mgb:
    leg.append(group)
    hist, bin_edges = np.histogram(df.HR, bins=bins, density=True)
    plt.plot(x, hist)
    plt.hold(True)
plt.title('Home Runs by Position')
plt.legend(leg)

print(mgb['HR'].describe())


# Compute statistical values
# Compute cohen's D, t-statistic, t-critical, given p-value, dof, means and stdevs
# stats-handout. Two sample, unpaired t-test
mgb_stats = mgb['HR'].aggregate([np.mean, np.std])



# Show pdf
x = np.linspace(-10, 10, 1e3)
y = mlab.normpdf(x, 0, 1)
fig, ax = plt.subplots(1,1)
ax.plot(x, y, color='blue')
ax.fill_between(x[550:], 0, y[550:], facecolor='blue', alpha=0.5)
ax.fill_between(x[600:], 0, y[600:], facecolor='red', alpha=0.5)
ax.set_title('Example Gaussian PDF')
ax.set_xlabel('Home Run Hitting Ability')
ax.set_ylabel('Probability Density')

tail_two_sided = 1 - 0.6827  # should give 1 sigma
print(-norm.ppf(tail_two_sided / 2.0))

# Compute number of teams, and number of players
teams_year = teams.groupby('yearID')
teams_count = teams_year.teamID.count()
players_count = teams_count * 25
players_count.name = 'numPlayers'
fig, ax1 = plt.subplots()
ax1.plot(players_count, 'b')
#plt.title('Players per Year')
ax1.set_ylabel('Number of Players', color='b')
ax1.set_xlabel('Year')
for tl in ax1.get_yticklabels():
    tl.set_color('b')

pop_millions = pop * 1e-6
ax2 = ax1.twinx()
ax2.plot(pop_millions, 'g')
#plt.title('US Population')
ax2.set_xlabel('Year')
ax2.set_ylabel('US Population (millions)', color='g')
for tl in ax2.get_yticklabels():
    tl.set_color('g')
plt.title('US Population vs Number of MLB Players')

# Compute as percent of population
ratio = players_count / pop.population * 100.0
fig, ax = plt.subplots()
ax.plot(ratio)
ax.set_title('MLB Players as % of US Population')
ax.set_ylabel('% MLB Players')
ax.set_xlabel('Year')

plt.show()
