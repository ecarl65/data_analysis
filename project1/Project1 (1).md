

```python
#%matplotlib inline
import pandas
import matplotlib
matplotlib.use('SVG')
import matplotlib.pyplot as plt
import numpy as np
```

# Background Information

In a Stroop task, participants are presented with a list of words, with each word displayed in a color of ink. The participant’s task is to say out loud the color of the ink in which the word is printed. The task has two conditions: a congruent words condition, and an incongruent words condition. In the congruent words condition, the words being displayed are color words whose names match the colors in which they are printed: for example RED, BLUE. In the incongruent words condition, the words displayed are color words whose names do not match the colors in which they are printed: for example PURPLE, ORANGE. In each case, we measure the time it takes to name the ink colors in equally-sized lists. Each participant will go through and record a time from each condition.

# Questions for Investigation

## Question 1.1 - What is our independent variable? 

The independent variable is the choice of whether a word and its color is congruent or incongruent.

## Question 1.2 - What is our dependent variable?

The dependent variable is the time (in seconds) it takes to correctly identify the color of the word.

## Question 2.1 - What is an appropriate set of hypotheses for this task?

**Null Hypothesis** Under the null hypothesis we generally assume that we observe no effect, or no change. So the null hypothesis is that there is no change in the time it takes to correctly identify the color of the word for both the congruent and incongruent samples.
$$H_0: \mu_i - \mu_c \le 0$$

**Alternative Hypothesis** Under the alternative hypothesis we assume that the incongruent samples are more difficult to determine the correct color as quickly, due to the mismatch of color and word spelled. There is no reason to assume this would actually be easier to read than the congruent samples, therefore we are going to perform a one sided test.
$$H_a: \mu_i - \mu_c \gt 0$$

As is customary we'll use $\alpha=0.05$.


## Question 2.2 - What kind of statistical test do you expect to perform?

As mentioned above, this should be a one-sided test due to the expectation that having incongruent samples will make discerning the correct color more difficult. There is no reason to suspect that it will make the process easier. 

As per the description of the provided data, it would appear that the congruent and incongruent tests were both done on the same set of people. This means that a dependent test is in order, as opposed to an independent test. Also, since we are comparing two sets of samples, and do not have access to population data, we are going to have to perform a t-test. 

## Question 3 - Report Descriptive Statistics


```python
df = pandas.read_csv('stroopdata.csv')
n = len(df['Congruent'])
```

First, these data sets are not expected to be centered around zero mean. Let's normalize it, in the mean sense and under the null hypothesis, by computing the difference of the incongruent to congruent samples. Then we can measure the mean and median values of each of the samples.


```python
df['Delta'] = df['Incongruent'] - df['Congruent']
means = df.mean()
print(means)
```

    Congruent      14.051125
    Incongruent    22.015917
    Delta           7.964792
    dtype: float64


$$\overline{x}_c = 14.051$$
$$\overline{x}_i = 22.016$$
$$\overline{x}_d = 7.965$$


```python
print(df.median())
```

    Congruent      14.3565
    Incongruent    21.0175
    Delta           7.6665
    dtype: float64


The standard deviation of each data set should also be computed. Note that this method uses Bessel's correction, as required since this is the standard deviation of a sample, and not the population.


```python
devs = df.std()
print devs
```

    Congruent      3.559358
    Incongruent    4.797057
    Delta          4.864827
    dtype: float64


$$S_c = 3.559$$
$$S_i = 4.797$$
$$S_d = 4.865$$

## Question 4 - Plot the Data


```python
def plothist(x):
    inbins = np.arange(0, 10) * 5
    hist, bins = np.histogram(x, inbins)
    center = (bins[:-1] + bins[1:]) / 2
    plt.plot(center, hist, linewidth=1.5)
    plt.title('Histogram')
    plt.xlabel('Time (sec)')
    
plt.figure(figsize=(12,6))
plothist(df['Congruent'])
plothist(df['Incongruent'])
plothist(df['Delta'])
plt.legend(['Congruent', 'Incongruent', 'Delta'])
#plt.show()
plt.savefig('/home/ecc/data_analysis/histograms.svg')
```

Histograms are normally plotted using bar charts. However, a line plot is used here in order to observe the histogram of each set of data on the same chart. 

It's clear that this is unfortunately a small sample size. Typically smaller sizes are possible with dependent samples tests, but it makes meaningful visualization of the histogram challenging. Any more bins and we start getting some bins with no counts and the shape is distorted. Any fewer bins and the histogram provides little value. 

There are a few salient points about the histograms worth mentioning. It's interesting to note that the subtraction of the incongruent and congruent samples produces a resulting histogram that is entirely positive. Under the null hypothesis we would expect it to be zero mean. But we'll have to test the significance of the result later. The delta histogram especially seems to have a positive skew, based on the histogram and the mean to median ratio.

## Question 5 - Perform the Statistical Test and Interpret the Results


```python
from scipy.stats import t
dof = n - 1
alpha = 0.05
print("Number of samples = {0}".format(len(df['Congruent'])))
print("Degrees of freedom = {0}".format(dof))
print("Alpha = {0}".format(alpha))
print("Critical value = {:.3f}".format(-t.ppf(alpha, dof)))
```

    Number of samples = 24
    Degrees of freedom = 23
    Alpha = 0.05
    Critical value = 1.714


Since there are 24 measurements in each sample that means that there are 23 *degrees of freedom*.

For a dependent samples, one-sided (positive) t-test, with $\alpha=0.05$, and 23 degrees of freedom, that produces the following *critical value*:

$$t_{critital} = 1.714$$

The standard error of the mean is:


```python
se = devs['Delta'] / np.sqrt(n)
print("Standard error = {0:.3f}".format(se))
```

    Standard error = 0.993


$$SE = \frac{S_d}{\sqrt{n}} = \frac{4.865}{\sqrt{24}} = 0.993$$


```python
print("Cohen's D = {0:.3f}".format(means['Delta']/devs['Delta']))
```

    Cohen's D = 1.637


*Cohen's D* is given by:

$$d = \frac{\overline{x}_d - 0}{S_d} = \frac{7.965}{4.865} = 1.637$$

The *t-statistic* is given by:

$$t_{statistic} = \frac{\overline{x}_d}{SE} = \frac{\overline{x}_d}{\frac{S_d}{\sqrt{n}}}$$


```python
t_stat = means['Delta'] / se
print("T-statistic = {0:.3f}".format(t_stat))
```

    T-statistic = 8.021


$$t_{statistic} = 8.021$$


```python
from scipy.stats import ttest_rel
tst, p = ttest_rel(df['Congruent'],df['Incongruent'])
print("scipy.stats t-statistic = {0:.3f}".format(tst))
print("two-sided probability (WRONG ONE TO USE) = {0:3g}".format(p))
print("two-sided probability divided by two = {0:3g}".format(p/2.0))
from scipy.stats import t
rv = t(dof)
print("one sided probability = {0:3g}".format(rv.cdf(tst)))
print("one sided probability = {0:3g}".format(rv.cdf(-t_stat)))
```

    scipy.stats t-statistic = -8.021
    two-sided probability (WRONG ONE TO USE) = 4.103e-08
    two-sided probability divided by two = 2.0515e-08
    one sided probability = 2.0515e-08
    one sided probability = 2.0515e-08



```python
print df
```

        Congruent  Incongruent   Delta
    0      12.079       19.278   7.199
    1      16.791       18.741   1.950
    2       9.564       21.214  11.650
    3       8.630       15.687   7.057
    4      14.669       22.803   8.134
    5      12.238       20.878   8.640
    6      14.692       24.572   9.880
    7       8.987       17.394   8.407
    8       9.401       20.762  11.361
    9      14.480       26.282  11.802
    10     22.328       24.524   2.196
    11     15.298       18.644   3.346
    12     15.073       17.510   2.437
    13     16.929       20.330   3.401
    14     18.200       35.255  17.055
    15     12.130       22.158  10.028
    16     18.495       25.139   6.644
    17     10.639       20.429   9.790
    18     11.344       17.425   6.081
    19     12.369       34.288  21.919
    20     12.944       23.894  10.950
    21     14.233       17.960   3.727
    22     19.710       22.058   2.348
    23     16.004       21.157   5.153



```python

```
