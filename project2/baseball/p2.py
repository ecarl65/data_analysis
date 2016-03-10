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
#import seaborn as sns
from scipy.stats import norm, t, ttest_ind
import pdb


# Variables
# Minimum number of at bats to use data in averages
# First order approximation to minimum requirements to rate a stat
# Used at one point by the American League
# http://www.baseball-reference.com/about/leader_glossary.shtml#min_req
min_at_bats = 400   

# Significance level of test
alpha = 0.05        

# Show example Gaussian pdf
# This higlights that when there is a smaller percentage of the total 
# that means the extent on the x-axis of the histogram extends smaller 
# than when the percentage is higher
x = np.linspace(-10, 10, 1e3)
y = mlab.normpdf(x, 0, 1)
fig, ax = plt.subplots(1, 1, figsize=(9, 3.5))
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
appearances_position = appearances.groupby('playerID').sum()
appearances_position['POS'] = 'Other'
appearances_position.loc[appearances_position['G_1b'] > 
                          appearances_position['G_ss'], 'POS'] = 'First Basemen'
appearances_position.loc[appearances_position['G_1b'] < 
                          appearances_position['G_ss'], 'POS'] = 'Shortstop'

# Merge tables and group by position
# merged_batting_position = pd.merge(batting[batting.yearID > 2004], appearances_position, 
merged_batting_position = pd.merge(batting, appearances_position, 
                                   how='left', left_on='playerID', right_index=True)
batting_position = merged_batting_position.groupby('POS')
hr_pos = merged_batting_position

fig, ax = plt.subplots(figsize=(9, 3.5))
bins = np.arange(0, 50, 2)
hr_pos['HR'][(hr_pos['POS'] == 'Shortstop')].hist(alpha=0.5, bins=bins, normed=True, 
        label='Shortstop', color='r', ax=ax)
hr_pos['HR'][(hr_pos['POS'] == 'First Basemen')].hist(alpha=0.5, bins=bins, normed=True, 
        label='First Basemen', color='b', ax=ax)
ax.legend()
ax.set_title('Histogram of Home Runs by Position')
ax.set_xlabel('# of HR''s')
ax.set_ylabel('Normalized Histogram')
plt.tight_layout()
plt.savefig('images/hr_pos.png')

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
print("mean delta: {0}".format(mean_delta))
print("standard error: {0}".format(standard_error))
print("degrees of freedom: {0}".format(dof))
print("t-critical (alpha={0}): {1}".format(alpha, t_critical))

# Cohen's d
s = np.sqrt(((n1 - 1) * s1**2 + (n2 - 1) * s2**2) / (n1 + n2 - 2))
cohens_d = mean_delta / s
print("Standard Units: {0}".format(s))
print("Cohen's D: {0}".format(cohens_d))

# scipy.stats independent samples t-test
homeruns_firstbase = \
    merged_batting_position[merged_batting_position.POS == 'First Basemen'].HR
homeruns_shortstop = merged_batting_position[merged_batting_position.POS == 'Shortstop'].HR
homeruns_firstbase = np.array(homeruns_firstbase[~homeruns_firstbase.isnull()])
homeruns_shortstop = np.array(homeruns_shortstop[~homeruns_shortstop.isnull()])
print(ttest_ind(homeruns_firstbase, homeruns_shortstop))

# Compute batting average
batting['AV'] = batting['H'] / (batting['AB'] + 1e-15)

# Limit statistics to representative samples
batting_at_bats = batting[batting.AB > min_at_bats]
# batting[['yearID', 'playerID', 'AV']].groupby(['yearID', 'playerID']).max()
batting_max = batting_at_bats[['yearID', 'AV']].groupby('yearID').max()
fig, ax = plt.subplots(figsize=(9, 3.5))
batting_max.plot(ax=ax, legend=False)
ax.set_title('Maximum Batting Average by Year')
ax.set_xlabel('Year')
ax.set_ylabel('Batting Average')
plt.tight_layout()
plt.savefig('images/max_average.png')

# Compute number of teams, and number of players
# Show with population statistics, along with as percentage of total
teams_year = teams.groupby('yearID')
teams_count = teams_year.teamID.count()
players_count = teams_count * 25  # current roster limits 25 players/team
players_count.name = 'numPlayers'

# Compute as percent of populationulation
ratio = players_count / population.population * 100.0
fig, ax = plt.subplots(figsize=(9, 3.5))
ax.plot(ratio)
ax.set_title('MLB Players as % of US Population')
ax.set_xlabel('Year')
ax.set_ylabel('% MLB Players')
plt.tight_layout()
plt.savefig('images/pop_players.png')

# Plot standard deviation for batting average over time
fig, ax = plt.subplots(2, 1, figsize=(9, 6), sharex=True)

df = pd.DataFrame()
df = batting_at_bats[['AV','yearID']].groupby('yearID').std()
df['STD'] = df['AV']
df['RATIO'] = ratio
df['MEAN'] = batting_at_bats[['AV','yearID']].groupby('yearID').mean()['AV']
df = df[np.all(np.isfinite(df), axis=1)]
df = df.reset_index()

df.plot(x='yearID', y='STD', ax=ax[0], legend=False)
ax[0].set_title('Standard Deviation of Batting Average')
ax[0].set_xlabel('Year Range')
ax[0].set_ylabel('Standard Deviation')

ax[1].errorbar(df['yearID'], df['MEAN'], df['STD'], linestyle='--', marker='^', capsize=3)
ax[1].set_title('MLB Players Mean and STD Over Time')
ax[1].set_xlabel('Year')
ax[1].set_ylabel('Mean and STD')

plt.tight_layout()
plt.savefig('images/ave_std_mean.png')

plt.show()
