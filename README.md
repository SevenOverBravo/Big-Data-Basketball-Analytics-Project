# Big-Data-Basketball-Analytics-Project

## Project Summary
This project aimed to discover the extent to which certain NBA efficiency metrics, namely Player Efficiency Rating (PER), Box Plus/Minus (BPM) and Value Over Replacement Player (VORP), can predict the quality of a player's next season. To accomplish this, choice variables from the 2010-2026 NBA seasons and multiple regression models (OLS, Ridge, LASSO, and PCA) were employed. After obtaining out-of-sample estimates for these staistics in Stata and calculating the percentage of correctly classified predictions, it was determined that (despite attempting to capture all of a player's individual contributions into a single value) none of these measurements could predict better than the naive model. 

## Data and Methodology
All data was obtained using the nba_api Python package (locate the obtaindata.py in the "Data" file), which allows data to be taken from the official NBA website. Each row of data represents a single season for a specific NBA player (No G-League or College Players). To ensure the results wouldn't be confabulated by outliers, only seasons where a player had participated in at least 45% of their team games were included in the dataset.

The list of obtained variables is as follows:



## Key Results

## 
