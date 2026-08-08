# Big-Data-Basketball-Analytics-Project

## Project Summary

This project aimed to discover the extent to which certain NBA efficiency metrics, namely Player Efficiency Rating (PER), Box Plus/Minus (BPM), and Value Over Replacement Player (VORP), can predict the quality of a player's next season. To accomplish this, choice variables from the 2010-2026 NBA seasons and multiple regression models (OLS, Ridge, LASSO, and PCA) were employed. After obtaining out-of-sample estimates for these statistics in Stata and calculating the percentage of correctly classified predictions, it was determined that (despite attempting to capture all of a player's individual contributions into a single value) none of these measurements could predict better than the naive model. 

## Data and Methodology

### Obtaining and Configuring Data 

All data was obtained using the nba_api Python package (locate the obtaindata.py in the "Data" file), which allows data to be taken from the official NBA website. Each row of data represents a single season for a specific NBA player (No G-League or college players). To ensure the results wouldn't be biased by outliers, only seasons where a player had participated in at least 45% of their team games were included in the dataset. The 45% value was chosen for multiple reasons. Firstly, it ensures that each season contains a large enough sample of games (30 to 40 depending on the overall season length) so that each statistic isn't distorted by small-sample noise. Secondly, a 45% benchmark is crucial for player career continuity. In other words, it allows the majority of players' seasons to be utilized regardless of any injury-shortened seasons (namely the 30 to 40 game seasons of superstars Joel Embiid and Anthony Davis), meaning the variation between each subsequent season can be represented in the data.  

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

Since OLS is poor at creating predictive models due to the variance introduced by its large estimates, it will be used as a comparison tool for the other three regressions (which are more equipped to handle predictive models due to their additional methods reducing variance) rather than a legitimate model unto itself. 

### Classification of Season Quality and Final Analysis

Once the out-of-sample estimates have been calculated, they'll be compared against their true counterparts to access prediction accuracy. Since season quality is the underlying factor in this analysis, the means and standard deviations for each of the true values of the efficiency metric differentials were tabulated, with season quality being determined as such:

Breakout: >+1.5SD from Mean of efficiency metric differential

Improvement: Between +0.75SD from +1.5SD from Mean of efficiency metric differential

Plateau: Between -0.75SD from +0.75SD from Mean of efficiency metric differential

Worsening: Between -0.75SD from -1.5SD from Mean of efficiency metric differential

Notable Decline: >-1.5SD from Mean of efficiency metric differential

The classification system was chosen for multiple reasons. Firstly, it reflects the intuition that only a handful of seasons in any given year will show any massive shift in quality (i.e. Breakout or Notable Decline), with most seasons hovering around the middle categories. Secondly, a Mean/SD model is not only simple to implement, but allows each efficiency metric to be categorized based on its own unique distribution, reflecting the scale and natural variance of each statistic. 

With each value being designated appropriately, each estimate was then compared to its true counterpart to see if their classification was identical, with a percentage of accurate predictions for each method being calculated. This percentage was then subtracted from that of the naive model (where every entry is classified as "Plateau", as this designation has the widest bounds and will be the most precise on average) as a measurement of accuracy compared to when no information is known. 

## Key Results

**Bold** = Best within DV | *Italic* = Best of all DVs

**Correct Prediction % Above Naive Model**

| | OLS | Ridge | LASSO | PCA |
|---|---|---|---|---|
| PER | -6.53% | -8.25% | -6.82% | **-5.50%** |
| BPM | -7.90% | -6.19% | -5.50% | **-5.50%** |
| VORP | -6.53% | -2.06% | -1.72% | ***0%*** |

**Confusion Matrix of Season Classifications: VORP PCA Model**

<img width="600" height="350" alt="image" src="https://github.com/user-attachments/assets/1da1cf8e-07fb-403f-8f4e-8da8e8927233" />

The above table demonstrates that not only do none of the efficiency metrics predict better than the naive model, but also that the best available means of prediction (the PCA VORP model) performs, at best, on par with the naive model. So, as a general method of classifying season quality, the experiment's methodology appears to be of little use. 

The confusion matrix, however, adds additional context to the percentage table. While there are no glaring classification errors (i.e. no "Breakout" seasons predicted to be "Notable Decline" seasons and vice versa), the confusion matrix reveals reason behind the VORP PCA model's accuracy: Estimating towards the center. Since, by the nature of the classification system, most of the true values will be in the middle categories (i.e. "Improvement", "Plateau", and "Worsening"), a model's accuracy would increase if its estimates were crowded in this range. Such a phenomenon is seen by how most seasons were predicted to be in the "Plateau" category on the confusion matrix, leaving very few entries to fill the "Breakout" and "Notable Decline" categories. This also ties into another key observation, which is that all 18 of the "Breakout" seasons were predicted incorrectly. Not only does this indicate that our model is a poor predictor of extreme increase in season quality, but also heavily limits its practical usage, as the knowledge that a player may have a breakout season would greatly impact the real-world processes of salary negotiations, trade decisions, and configuring lineups. 

Ultimately, it can be concluded that PER, BPM, and VORP aren't valuable estimates of anything having to do with future season quality under this experiment's methodology.

## Limitations and Future Research
In light of the unfavorable conclusion, it's worth noting that the methodology of this project has a number of potential flaws. The most prominent of these is the season classification system. While its implementation was simple, the system likely introduced systematic error into the experiment in many ways. One of these is the bounds of each category. The idea that only a few players can experience breakout seasons each year is intuitive, but the assumption that the proportion of bounds remains identical for each year is unsubstantiated. In reality, the amount of breakouts in a given season is dependent on a variety of personal, team, and administrative/coaching factors and changes dramatically each year. As a result, the classification system not only misrepresents the quality of each season by insisting a certain quantity must be in the extreme categories (i.e. Breakout or Notable Decline), but distorts the estimated statistical values through the same means, adding bias into the experiment. 

Another major issue with the classification system is its misalignment with the goals of this project. In other words, the system was meant to demonstrate whether the regression models were generally accurate and could adequately predict breakout seasons, but analysis of the results suggests otherwise. Instead of having both of these traits, the most accurate model achieved its percentage accuracy by categorizing most seasons into the more prevalent middle categories, thus boosting this metric without contributing any meaningful predictions. The fact that the means of classifying seasons rewards crowding the middle categories rather than correctly predicting breakout seasons is evidence of a fundamental detachment from the experiment's intentions, implying it cannot be used on subsequent trials. 

Outside of the classification system, 

If this project were to be repeated, the classification system would experience a major overhaul.
