# Big-Data-Basketball-Analytics-Project

## Project Summary

This project aimed to discover the extent to which certain NBA efficiency metrics, namely Player Efficiency Rating (PER), Box Plus/Minus (BPM), and Value Over Replacement Player (VORP), can predict the quality of a player's next season. To accomplish this, choice variables from the 2010-2026 NBA seasons and multiple regression models (OLS, Ridge, LASSO, and PCA) were employed. After obtaining out-of-sample estimates for these statistics in Stata and calculating the percentage of correctly classified predictions, it was determined that (despite attempting to capture all of a player's individual contributions into a single value) none of these measurements could predict better than the naive model. 

## Data and Methodology

### Obtaining and Configuring Data 

All data was obtained using the nba_api Python package (locate the obtaindata.py in the "Data" file), which allows data to be taken from the official NBA website. Each row of data represents a single season for a specific NBA player (No G-League or college players). To ensure the results wouldn't be confabulated by outliers, only seasons where a player had participated in at least 45% of their team games were included in the dataset.

The primary predictors include a variety of personal attributes (Age, Position), individual performance metrics (Points, Rebounds, etc.), and team data (Win/Loss Record, Strength of Schedule, etc.), as well as the efficiency metrics in question. For each of the individual and team statistics, the previous season value and differential (last season value - two seasons ago value) were taken to track their current state and movement respectfully. Our dependent variables are the current season differentials (current season - last season) for each efficiency metric. Full documentation of predictors can be found in the "variable_doc.md" file in the Data folder.

The regressors created from these primary predictors include the raw values, squared variables (to account for any nonlinear relationships), and interactions, all of which was done in Stata (locate the Stata Code folder for the documentation). After this process, the final tally of regressors came to 643. All regressors are standardized, although the unstandardized dependent variables are kept to analyze RMSE in terms of each metric's scale.

### Regression Procedures

To ensure that the influence of only one efficiency metric is present in each regression, the regressors used will depend on the regression's dependent variable. All regressions will include the regressors that have nothing to do with the efficiency metrics, but the variables that do must match the dependent variable in the regression. For example, the regressions with PER dependent variables will have only the PER raw values, squared variables, and interactions. This phenomenon is demonstrated through the table below.

| Types of DV | PER DVs | BPM DVs | VORP DVs |
|---|---|---|---|
| Included Regressors | Non-efficiency metric regressors + PER raw predictors, square variables, and interactions | Non-efficiency metric regressors + BPM raw predictors, square variables, and interactions | Non-efficiency metric regressors + VORP raw predictors, square variables, and interactions |

Because of this process, only 519 of the 643 total regressors will appear in each regression.

For each dependent variable, standardized and unstandardized, four regression methods were used to process the data, totaling 24 regressions. The regression models utilized and any special procedures accompanied by them are as follows:

| Regression Method | Special Procedures |
|---|---|
| Ordinary Least Squares (OLS) | No special procedures, run normally |
| Ridge | Obtain optimal penalty factor (lambda) using m-fold cross validation and implement it when regressing on in-sample data |
| LASSO | Obtain optimal penalty factor (lambda) using m-fold cross validation and implement it when regressing on in-sample data |
| Principal Component Analysis (PCA) | Obtain scree plot of PCs and keep minimum amount to encompass 95% of variation |

### Classifcation of Season Quality and Final Analysis

Once the out-of-sample estimates have been calculated, they'll be compared against their true counterparts to access prediction accuracy. Since season quality is the underlying factor in this analysis, the means and standard deviations for each of the true values of the efficiency metric differentials were tabulated, with season quality being determined as such:

Breakout: >+1.5SD from Mean of efficiency metric differential

Improvement: Between +0.75SD from +1.5SD from Mean of efficiency metric differential

Plateau: Between -0.75SD from +0.75SD from Mean of efficiency metric differential

Worsening: Between -0.75SD from -1.5SD from Mean of efficiency metric differential

Notable Decline: >-1.5SD from Mean of efficiency metric differential

With each value being designated appropriately, each estimate was then compared to its true counterpart to see if their classification was identical, with a percentage of accurate predictions for each method being calculated. This percentage was then subtracted from that of the naive model (where every entry is classified as "Plateau", as this designation has the widest bounds and will be the most precise on average) as a measurement of accuracy compared to when no information is known. 

## Key Results

**Bold** = Best within DV | *Italic* = Best of all DVs

**Correct Prediction % Above Naive Model**

| | OLS | Ridge | LASSO | PCA |
|---|---|---|---|---|
| PER | -6.53% | -8.25% | -6.82% | **-5.50%** |
| BPM | -7.90% | -6.19% | -5.50% | **-5.50%** |
| VORP | -6.53% | -2.06% | -1.72% | ***0%*** |

**Confusion Matrix of Season Classifications**
<img width="852" height="545" alt="image" src="https://github.com/user-attachments/assets/1da1cf8e-07fb-403f-8f4e-8da8e8927233" />

The above table demonstrates that not only do none of the efficiency metrics predict better than the naive model, but also that the best available means of prediction (the PCA VORP model) performs, at best, on par with the naive model. Not only that, this specific model is incapable of predicting any "Breakout" seasons, with none of the 9 seasons of this caliber being categorized as such by the estimates. Ultimately, it can be concluded that PER, BPM, and VORP aren't valuable estimates of anything having to do with future season quality.

Further conclusions and opportunities for future research are located in the Presentation folder.
