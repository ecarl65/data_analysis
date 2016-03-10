# Investigate the MLB datasets to answer two questions.
#
# Question 1: Is there a difference in home run hitting ability
# between shortstops and first basemen?
#
# Question 2: Is there a reduced spread in batting averages
# over time. This indirectly is used to answer the question of
# why there are no longer hitters batting .400.
#


# Imports
from __future__ import division, print_function
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.mlab as mlab
# import seaborn as sns
from scipy.stats import norm, t, ttest_ind
import pdb

# Variables
num_bins = 25       # Number of bins for histograms
num_quantiles = 12  # Number of year quantiles for batting averages
min_at_bats = 25    # Minimum number of at bats to use data in averages
alpha = 0.05        # Significance level of test

# Show example Gaussian pdf
# This higlights that when there is a smaller percentage of the total 
# that means the extent on the x-axis of the histogram extends smaller 
# than when the percentage is higher
x = np.linspace(-10, 10, 1e3)
y = mlab.normpdf(x, 0, 1)
fig, ax = plt.subplots(1, 1, figsize=(11,4))
ax.plot(x, y, color='blue')
ax.fill_between(x[550:], 0, y[550:], facecolor='blue', alpha=0.5)
ax.fill_between(x[600:], 0, y[600:], facecolor='red', alpha=0.5)
ax.set_title('Example Gaussian PDF')
ax.set_xlabel('Skill Level (unitless)')
ax.set_ylabel('Probability Density')
plt.tight_layout()
plt.savefig('images/example_gaussian.png')

# Read input files
batting = pd.read_csv('Batting.csv')
appearances = pd.read_csv('Appearances.csv')
population = pd.read_csv('population.csv', index_col=0).sort_index()
teams = pd.read_csv('Teams.csv')

# Add new column for player position
# Group by new position indicator
batting_recent = batting[batting.yearID > 2004]
appearances_position = appearances.groupby('playerID').sum()
appearances_position['POS'] = 'Other'
appearances_position.loc[appearances_position['G_1b'] > 
                          appearances_position['G_ss'], 'POS'] = 'First Basemen'
appearances_position.loc[appearances_position['G_1b'] < 
                          appearances_position['G_ss'], 'POS'] = 'Shortstop'

# Merge tables and group by position
merged_batting_position = pd.merge(batting_recent, appearances_position, how='left', 
                                   left_on='playerID', right_index=True)
batting_position = merged_batting_position.groupby('POS')

# batting_position.AV.hist()
fig, ax = plt.subplots(figsize=(11,4))
ax.hold(True)
bins = np.arange(0, 80, 5)
x = (bins[:-1] + bins[1:]) / 2.0
leg = []
for (group, df) in batting_position:
    leg.append(group)
    hist, bin_edges = np.histogram(df.HR, bins=bins, density=True)
    ax.plot(x, hist)
ax.legend(leg)
ax.set_title('Histogram of Home Runs by Position')
ax.set_xlabel('# of HR''s')
ax.set_ylabel('Normalized Histogram')
plt.tight_layout()
plt.savefig('images/hr_pos.eps')

print(batting_position['HR'].describe())

# Compute statistical values
# Compute cohen's D, t-statistic, t-critical, p-value, dof, means and stdevs
# Two sample, independent, unpaired t-test
batting_position_count = batting_position['HR'].count()
batting_position_stats = batting_position['HR'].aggregate([np.mean, np.std]) 
n1 = batting_position_count['First Basemen']
n2 = batting_position_count['Shortstop']
dof = (n1 - 1) + (n2 - 1)
mean_delta = batting_position_stats['mean']['First Basemen'] - \
             batting_position_stats['mean']['Shortstop']
s1 = batting_position_stats['std']['First Basemen']
s2 = batting_position_stats['std']['Shortstop']
standard_error = np.sqrt(s1**2 / n1 + s2**2 / n2)
t_statistic = mean_delta / standard_error
t_critical = -t.ppf(alpha, dof)  # Assuming firstbase HR > shortstop, invert cdf
rv = t(dof)
p_value = rv.cdf(-t_statistic)
print("mean delta: {0}".format(mean_delta))
print("standard error: {0}".format(standard_error))
print("degrees of freedom: {0}".format(dof))
print("t-critical (alpha={0}): {1}".format(alpha, t_critical))
print("t-statistic: {0}".format(t_statistic))
print("one tailed probability = p = {0:3g}".format(p_value))

# Cohen's d
s = np.sqrt(((n1 - 1) * s1**2 + (n2 - 1) * s2**2) / (n1 + n2 - 2))
cohens_d = mean_delta / s
print("Cohen's D: {0}".format(cohens_d))

# scipy.stats independent samples t-test
homeruns_firstbase = merged_batting_position[merged_batting_position.POS == 'First Basemen'].HR
homeruns_shortstop = merged_batting_position[merged_batting_position.POS == 'Shortstop'].HR
# homeruns_firstbase = np.array(homeruns_firstbase[~homeruns_firstbase.isnull()])
# homeruns_shortstop = np.array(homeruns_shortstop[~homeruns_shortstop.isnull()])
print(ttest_ind(homeruns_firstbase, homeruns_shortstop))

# Compute batting average
batting['AV'] = batting['H'] / (batting['AB'] + 1e-15)

# Determine year quantiles
increment = 1.0 / num_quantiles
batting_at_bats = batting[batting.AB > min_at_bats]
year_quantile = [(batting_at_bats['yearID'].quantile(increment * x), 
                  batting_at_bats['yearID'].quantile(increment * (x+1))) 
                  for x in xrange(num_quantiles)]
year_quantile_vector = [x[0] for x in year_quantile]
year_quantile_vector.append(year_quantile[-1][-1])

# Group by year quantiles
batting_years = batting_at_bats.groupby(pd.cut(batting_at_bats['yearID'], 
                                              year_quantile_vector))


# Plot histograms for batting average for quantiles
#fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(9,6))
fig, ax = plt.subplots(figsize=(11, 5))
ax.hold(True)
bins = np.linspace(0.0, 0.5, num=num_bins, endpoint=True)
x = (bins[:-1] + bins[1:]) / 2.0
# res = batting_years.AV.hist(bins=bins)  # Won't make lines
for (group, df) in batting_years:
    hist, bin_edges = np.histogram(df.AV, bins=bins, density=True)
    ax.plot(x, hist)
ax.set_title('Batting Average Histogram per Year Quantile')
legend = ['Quantile 1', 'Quantile 2', 'Quantile 3', 'Quantile 4', 'Quantile 5', 'Quantile 6']
ax.legend(legend[:num_quantiles])
ax.set_xlabel('Batting Average')
ax.set_ylabel('Normalized Histogram')
plt.tight_layout()
plt.savefig('images/ave_hist.eps')

# Plot standard deviation for batting average over year quantiles
fig, ax = plt.subplots(2, 1, figsize=(9, 6))
batting_years.AV.std().plot(ax=ax[0])
ax[0].set_title('Standard Deviation of Batting Average')
ax[0].set_xlabel('Year Range')
ax[0].set_ylabel('Standard Deviation')

# Plot standard deviation for batting average over year quantiles
batting_years.AV.mean().plot(ax=ax[1])
ax[1].set_title('Mean of Batting Average')
ax[1].set_xlabel('Year Range')
ax[1].set_ylabel('Mean')
plt.tight_layout()
plt.savefig('images/ave_std_mean.eps')

# Compute number of teams, and number of players
# Show with population statistics, along with as percentage of total
teams_year = teams.groupby('yearID')
teams_count = teams_year.teamID.count()
players_count = teams_count * 25
players_count.name = 'numPlayers'
fig, ax = plt.subplots(2, 1, figsize=(9,6))
ax[0].plot(players_count, 'b')
ax[0].set_ylabel('Number of Players', color='b')
ax[0].set_xlabel('Year')
for tl in ax[0].get_yticklabels():
    tl.set_color('b')

# Show population on same plot
population_millions = population * 1e-6
axyy = ax[0].twinx()
axyy.plot(population_millions, 'g')
ax[0].set_title('US Population vs Number of MLB Players')
axyy.set_xlabel('Year')
axyy.set_ylabel('US Population (millions)', color='g')
for tl in axyy.get_yticklabels():
    tl.set_color('g')

# Compute as percent of populationulation
ratio = players_count / population.population * 100.0
ax[1].plot(ratio)
ax[1].set_title('MLB Players as % of US Population')
ax[1].set_xlabel('Year')
ax[1].set_ylabel('% MLB Players')
plt.tight_layout()
plt.savefig('images/pop_players.eps')


plt.show()
