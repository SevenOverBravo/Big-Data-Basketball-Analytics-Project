/*===========================================================================
  Breakouts or Bricks? - Independent Basketball Analytics Project
  Stata Do-File: Variable Construction, Standardization, Regressions,
                 Cross-Validation (Ridge/Lasso), PCA, OOS Evaluation
===========================================================================*/


/*---------------------------------------------------------------------------
  SECTION 1: RENAMING VARIABLES + VARIABLE LIST SETUP
---------------------------------------------------------------------------*/

* Rename variables to facilitate organization
rename AGE v1	
rename LAST_TRADED	v2
rename DRAFT_PROP v3	
rename UNDRAFTED v4	
rename GP_PCT v5	
rename POS_Forward v6	
rename POS_Guard v7	
rename LAST_PTS_36 v8
rename LAST_AST_36 v9
rename LAST_REB_36 v10
rename LAST_STL_36 v11
rename LAST_BLK_36 v12
rename LAST_TOV_36 v13
rename LAST_USG_PCT v14	
rename LAST_TS_PCT v15
rename LAST_PTS_36_DIFF v16	
rename LAST_AST_36_DIFF v17	
rename LAST_REB_36_DIFF v18	
rename LAST_STL_36_DIFF v19	
rename LAST_BLK_36_DIFF v20	
rename LAST_TOV_36_DIFF v21	
rename LAST_USG_PCT_DIFF v22	
rename LAST_TS_PCT_DIFF v23	
rename LAST_TEAM_ORTG v24	
rename LAST_TEAM_DRTG v25	
rename LAST_TEAM_WIN_PCT v26	
rename LAST_TEAM_ORTG_DIFF v27
rename LAST_TEAM_DRTG_DIFF v28
rename LAST_TEAM_WIN_PCT_DIFF v29

* Rename efficiency metrics
rename LAST_PER e1
rename LAST_BPM e2
rename LAST_VORP e3
rename LAST_PER_DIFF e1_diff
rename LAST_BPM_DIFF e2_diff
rename LAST_VORP_DIFF e3_diff

* Define variable lists
global prims v1 v2 v3 v4 v5 v6 v7 v8 v9 v10 v11 v12 v13 v14 v15 v16 v17 v18 v19 v20 v21 v22 v23 v24 v25 v26 v27 v28 v29

global e_prims e1 e2 e3

global e_diff_prims e1_diff e2_diff e3_diff


/*---------------------------------------------------------------------------
  SECTION 2: DEFINE SQUARE VARIABLES / DROP BINARIES
---------------------------------------------------------------------------*/

* Generate squared terms for all primary predictors
foreach v of varlist $prims {
    gen `v'_sq = `v'^2
}

* Drop squared terms for binary/near-binary variables
drop v2_sq
drop v4_sq
drop v6_sq
drop v7_sq

* Drop v3_sq due to high multicollinearity (corr(v3, v3_sq) = 0.9651)
correlate v3 v3_sq
drop v3_sq


/*---------------------------------------------------------------------------
  SECTION 3: DEFINE INTERACTION TERMS (PRIMARY PREDICTORS)
---------------------------------------------------------------------------*/

local plist $prims
local n : word count `plist'

forvalues i = 1/`n' {
    local vi : word `i' of `plist'
    forvalues j = `=`i'+1'/`n' {
        local vj : word `j' of `plist'
        gen `vi'X`vj' = `vi' * `vj'
    }
}


/*---------------------------------------------------------------------------
  SECTION 4: EFFICIENCY VARIABLES - SQUARE TERMS
---------------------------------------------------------------------------*/

* Squared terms for efficiency levels
foreach e of varlist $e_prims {
    gen `e'_sq = `e'^2
}

* Squared terms for efficiency differences
foreach e of varlist $e_diff_prims {
    gen `e'_diff_sq = `e'^2
}


/*---------------------------------------------------------------------------
  SECTION 5: EFFICIENCY VARIABLES - INTERACTION TERMS
---------------------------------------------------------------------------*/

* e1 interactions with all primary predictors
global e1_ints ""
foreach v of varlist $prims {
    gen e1X`v' = e1 * `v'
    global e1_ints "$e1_ints e1X`v'"
}

* e2 interactions with all primary predictors
global e2_ints ""
foreach v of varlist $prims {
    gen e2X`v' = e2 * `v'
    global e2_ints "$e2_ints e2X`v'"
}

* e3 interactions with all primary predictors
global e3_ints ""
foreach v of varlist $prims {
    gen e3X`v' = e3 * `v'
    global e3_ints "$e3_ints e3X`v'"
}

* e1_diff interactions with all primary predictors
global e1_diff_ints ""
foreach v of varlist $prims {
    gen e1_diffX`v' = e1_diff * `v'
    global e1_diff_ints "$e1_diff_ints e1_diffX`v'"
}

* e2_diff interactions with all primary predictors
global e2_diff_ints ""
foreach v of varlist $prims {
    gen e2_diffX`v' = e2_diff * `v'
    global e2_diff_ints "$e2_diff_ints e2_diffX`v'"
}

* e3_diff interactions with all primary predictors
global e3_diff_ints ""
foreach v of varlist $prims {
    gen e3_diffX`v' = e3_diff * `v'
    global e3_diff_ints "$e3_diff_ints e3_diffX`v'"
}


/*---------------------------------------------------------------------------
  SECTION 6: STANDARDIZE DEPENDENT VARIABLES
---------------------------------------------------------------------------*/

foreach v of varlist per_diff bpm_diff vorp_diff {
    quietly summarize `v'
    scalar mean_`v' = r(mean)
    scalar sd_`v'   = r(sd)
    gen `v'_std = (`v' - mean_`v') / sd_`v'
}


/*---------------------------------------------------------------------------
  SECTION 7: STANDARDIZE INDEPENDENT VARIABLES (PRIMARY PREDICTORS)
---------------------------------------------------------------------------*/

* Standardize primary predictors (v1-v29)
forvalues i = 1/29 {
    quietly summarize v`i'
    scalar mean_v`i' = r(mean)
    scalar sd_v`i'   = r(sd)
    gen v`i'_std = (v`i' - r(mean)) / r(sd)
    global allpreds "$allpreds v`i'_std"
}

* Standardize squared primary predictors
* (excludes v2, v3, v4, v6, v7 — dropped above)
foreach i in 1 5 8 9 10 11 12 13 14 15 16 17 18 19 20 21 22 23 24 25 26 27 28 29 {
    quietly summarize v`i'_sq
    scalar mean_v`i'_sq = r(mean)
    scalar sd_v`i'_sq   = r(sd)
    gen v`i'_sq_std = (v`i'_sq - r(mean)) / r(sd)
    global allpreds "$allpreds v`i'_sq_std"
}

* Standardize pairwise interaction terms
forvalues i = 1/29 {
    forvalues j = `=`i'+1'/29 {
        quietly summarize v`i'Xv`j'
        scalar mean_v`i'Xv`j' = r(mean)
        scalar sd_v`i'Xv`j'   = r(sd)
        gen v`i'Xv`j'_std = (v`i'Xv`j' - r(mean)) / r(sd)
        global allpreds "$allpreds v`i'Xv`j'_std"
    }
}

* Drop interaction between position binaries and undrafted binary x draft proportion
drop v6Xv7_std
local remove "v6Xv7_std"
global allpreds : list allpreds - remove

* Also drop v3Xv4 (collinear combination)
drop v3Xv4


/*---------------------------------------------------------------------------
  SECTION 8: STANDARDIZE EFFICIENCY STATISTICS
---------------------------------------------------------------------------*/

* Standardize efficiency levels
foreach e in e1 e2 e3 {
    quietly summarize `e'
    scalar mean_`e' = r(mean)
    scalar sd_`e'   = r(sd)
    gen `e'_std = (`e' - r(mean)) / r(sd)
}

* Standardize squared efficiency levels
foreach e in e1_sq e2_sq e3_sq {
    quietly summarize `e'
    scalar mean_`e' = r(mean)
    scalar sd_`e'   = r(sd)
    gen `e'_std = (`e' - r(mean)) / r(sd)
}

* Standardize e1 interaction terms
global e1_ints_std ""
foreach e in $e1_ints {
    quietly summarize `e'
    scalar mean_`e' = r(mean)
    scalar sd_`e'   = r(sd)
    gen `e'_std = (`e' - r(mean)) / r(sd)
    global e1_ints_std "$e1_ints_std `e'_std"
}

* Standardize e2 interaction terms
global e2_ints_std ""
foreach e in $e2_ints {
    quietly summarize `e'
    scalar mean_`e' = r(mean)
    scalar sd_`e'   = r(sd)
    gen `e'_std = (`e' - r(mean)) / r(sd)
    global e2_ints_std "$e2_ints_std `e'_std"
}

* Standardize e3 interaction terms
global e3_ints_std ""
foreach e in $e3_ints {
    quietly summarize `e'
    scalar mean_`e' = r(mean)
    scalar sd_`e'   = r(sd)
    gen `e'_std = (`e' - r(mean)) / r(sd)
    global e3_ints_std "$e3_ints_std `e'_std"
}

* Standardize efficiency difference levels
foreach e in e1_diff e2_diff e3_diff {
    quietly summarize `e'
    scalar mean_`e' = r(mean)
    scalar sd_`e'   = r(sd)
    gen `e'_std = (`e' - r(mean)) / r(sd)
}

* Standardize squared efficiency differences
foreach e in e1_diff_sq e2_diff_sq e3_diff_sq {
    quietly summarize `e'
    scalar mean_`e' = r(mean)
    scalar sd_`e'   = r(sd)
    gen `e'_std = (`e' - r(mean)) / r(sd)
}

* Standardize e1_diff interaction terms
global e1_diff_ints_std ""
foreach e in $e1_diff_ints {
    quietly summarize `e'
    scalar mean_`e' = r(mean)
    scalar sd_`e'   = r(sd)
    gen `e'_std = (`e' - r(mean)) / r(sd)
    global e1_diff_ints_std "$e1_diff_ints_std `e'_std"
}

* Standardize e2_diff interaction terms
global e2_diff_ints_std ""
foreach e in $e2_diff_ints {
    quietly summarize `e'
    scalar mean_`e' = r(mean)
    scalar sd_`e'   = r(sd)
    gen `e'_std = (`e' - r(mean)) / r(sd)
    global e2_diff_ints_std "$e2_diff_ints_std `e'_std"
}

* Standardize e3_diff interaction terms
global e3_diff_ints_std ""
foreach e in $e3_diff_ints {
    quietly summarize `e'
    scalar mean_`e' = r(mean)
    scalar sd_`e'   = r(sd)
    gen `e'_std = (`e' - r(mean)) / r(sd)
    global e3_diff_ints_std "$e3_diff_ints_std `e'_std"
}


/*---------------------------------------------------------------------------
  SECTION 9: COMBINE INTO SINGLE PREDICTOR LISTS
---------------------------------------------------------------------------*/

global perpreds  "$allpreds e1_std e1_diff_std e1_sq_std e1_diff_sq_std $e1_ints_std $e1_diff_ints_std"
global bpmpreds  "$allpreds e2_std e2_diff_std e2_sq_std e2_diff_sq_std $e2_ints_std $e2_diff_ints_std"
global vorppreds "$allpreds e3_std e3_diff_std e3_sq_std e3_diff_sq_std $e3_ints_std $e3_diff_ints_std"


/*===========================================================================
  SECTION 10: IN-SAMPLE REGRESSIONS (STANDARDIZED DEPENDENT VARIABLES)
===========================================================================*/

/*--- PER: OLS ---*/
reg per_diff_std $perpreds, r nocons
* RMSE = 0.68155
estimates save "ols_per.ster", replace

/*--- PER: Ridge — M-Fold CV (10 folds) to find optimal lambda ---*/
elasticnet linear per_diff_std $perpreds, alpha(0) rseed(42) nfolds(10)
* Optimal lambda = 0.258777

elasticnet linear per_diff_std $perpreds, alpha(0) lambda(0.258777) nfolds(10)
* RMSE = 0.7434
estimates store ridge_per

/*--- PER: Lasso — M-Fold CV (10 folds) to find optimal lambda ---*/
elasticnet linear per_diff_std $perpreds, alpha(1) rseed(42) nfolds(10)
* Optimal lambda = 0.0073701

elasticnet linear per_diff_std $perpreds, alpha(1) lambda(0.0073701) nfolds(10)
* RMSE = 0.7365
estimates store lasso_per

/*--- PER: PCA ---*/
quietly pca $perpreds

* Screeplot — crosses eigenvalue=1 line at approximately p = 75
screeplot

* Confirm: 75 components explain ~94.8% of variation
scalar var_pc75 = 0
forvalues k = 1/75 {
    scalar var_pc75 = var_pc75 + e(Ev)[1, `k']
}
scalar total_var = trace(e(Ev))
scalar var_pc75 = var_pc75 / total_var * 100
di var_pc75
* Should display ~94.796136

* Re-run PCA retaining 75 components, save loadings, predict scores
quietly pca $perpreds, components(75)
estimates save pca_loadings_per, replace
quietly predict pc_per1-pc_per75, score

* Regress standardized PER difference on 75 PCs
reg per_diff_std pc_per1-pc_per75, r nocons
* RMSE = 0.7162
estimates save "pca_per.ster", replace


/*--- BPM: OLS ---*/
reg bpm_diff_std $bpmpreds, r nocons
* RMSE = 0.7538
estimates save "ols_bpm.ster", replace

/*--- BPM: Ridge — CV for optimal lambda ---*/
elasticnet linear bpm_diff_std $bpmpreds, alpha(0) rseed(42) nfolds(10)
* Optimal lambda = 1.06952

elasticnet linear bpm_diff_std $bpmpreds, alpha(0) lambda(1.06952) nfolds(10)
* RMSE = 0.8226
estimates store ridge_bpm

/*--- BPM: Lasso — CV for optimal lambda ---*/
elasticnet linear bpm_diff_std $bpmpreds, alpha(1) rseed(42) nfolds(10)
* Optimal lambda = 0.0304603

elasticnet linear bpm_diff_std $bpmpreds, alpha(1) lambda(0.0304603) nfolds(10)
* RMSE = 0.8534
estimates store lasso_bpm

/*--- BPM: PCA ---*/
quietly pca $bpmpreds

* Screeplot — crosses line at approximately p = 80
screeplot

* Confirm ~95% of variation in p = 80
scalar var_pc80 = 0
forvalues k = 1/80 {
    scalar var_pc80 = var_pc80 + e(Ev)[1, `k']
}
scalar var_pc80 = var_pc80 / 519 * 100
di var_pc80
* Should display ~94.394

quietly pca $bpmpreds, components(80)
estimates save pca_loadings_bpm, replace
quietly predict pc_bpm1-pc_bpm80, score

reg bpm_diff_std pc_bpm1-pc_bpm80, r nocons
* RMSE = 0.7892
estimates save "pca_bpm.ster", replace


/*--- VORP: OLS ---*/
reg vorp_diff_std $vorppreds, r nocons
* RMSE = 0.8049
estimates save "ols_vorp.ster", replace

/*--- VORP: Ridge — CV for optimal lambda ---*/
elasticnet linear vorp_diff_std $vorppreds, alpha(0) rseed(42) nfolds(10)
* Optimal lambda = 0.225009

elasticnet linear vorp_diff_std $vorppreds, alpha(0) lambda(0.225009) nfolds(10)
* RMSE = 0.8630
estimates store ridge_vorp

/*--- VORP: Lasso — CV for optimal lambda ---*/
elasticnet linear vorp_diff_std $vorppreds, alpha(1) rseed(42) nfolds(10)
* Optimal lambda = 0.0064083

elasticnet linear vorp_diff_std $vorppreds, alpha(1) lambda(0.0064083) nfolds(10)
* RMSE = 0.8531
estimates store lasso_vorp

/*--- VORP: PCA ---*/
quietly pca $vorppreds

* Screeplot — crosses line at approximately p = 95
screeplot

* Confirm variation contained in 95 components
scalar var_pc95 = 0
forvalues k = 1/95 {
    scalar var_pc95 = var_pc95 + e(Ev)[1, `k']
}
scalar var_pc95 = var_pc95 / 519 * 100
di var_pc95
* Should display ~94.847

quietly pca $vorppreds, components(95)
estimates save pca_loadings_vorp, replace
quietly predict pc_vorp1-pc_vorp95, score

reg vorp_diff_std pc_vorp1-pc_vorp95, r nocons
* RMSE = 0.8615
estimates save "pca_vorp.ster", replace


/*===========================================================================
  SECTION 11: IN-SAMPLE REGRESSIONS (UNSTANDARDIZED DEPENDENT VARIABLES)
===========================================================================*/

/*--- PER: OLS (unstandardized) ---*/
reg per_diff $perpreds, r nocons
* RMSE = 2.3989
estimates save "ols_per_unstd.ster", replace

/*--- PER: Ridge — CV for optimal lambda (unstandardized) ---*/
elasticnet linear per_diff $perpreds, alpha(0) rseed(42) nfolds(10)
* Optimal lambda = 0.3261192

elasticnet linear per_diff $perpreds, alpha(0) lambda(0.3261192) nfolds(10)
* RMSE = 2.628
estimates store ridge_per_unstd

/*--- PER: Lasso — CV for optimal lambda (unstandardized) ---*/
elasticnet linear per_diff $perpreds, alpha(1) rseed(42) nfolds(10)
* Optimal lambda = 0.0258444

elasticnet linear per_diff $perpreds, alpha(1) lambda(0.0258444) nfolds(10)
* RMSE = 2.633
estimates store lasso_per_unstd

/*--- PER: PCA (unstandardized) — reuse previously gathered PCs ---*/
reg per_diff pc_per1-pc_per75, r nocons
* RMSE = 2.519
estimates save "pca_per_unstd.ster", replace


/*--- BPM: OLS (unstandardized) ---*/
reg bpm_diff $bpmpreds, r nocons
* RMSE = 1.7023
estimates save "ols_bpm_unstd.ster", replace

/*--- BPM: Ridge — CV for optimal lambda (unstandardized) ---*/
elasticnet linear bpm_diff $bpmpreds, alpha(0) rseed(42) nfolds(10)
* Optimal lambda = 1.381433

elasticnet linear bpm_diff $bpmpreds, alpha(0) lambda(1.381433) nfolds(10)
* RMSE = 1.852
estimates store ridge_bpm_unstd

/*--- BPM: Lasso — CV for optimal lambda (unstandardized) ---*/
elasticnet linear bpm_diff $bpmpreds, alpha(1) rseed(42) nfolds(10)
* Optimal lambda = 0.090889

elasticnet linear bpm_diff $bpmpreds, alpha(1) lambda(0.090889) nfolds(10)
* RMSE = 1.910
estimates store lasso_bpm_unstd

/*--- BPM: PCA (unstandardized) — reuse previously gathered PCs ---*/
reg bpm_diff pc_bpm1-pc_bpm80, r nocons
* RMSE = 1.782
estimates save "pca_bpm_unstd.ster", replace


/*--- VORP: OLS (unstandardized) ---*/
reg vorp_diff $vorppreds, r nocons
* RMSE = 0.7435
estimates save "ols_vorp_unstd.ster", replace

/*--- VORP: Ridge — CV for optimal lambda (unstandardized) ---*/
elasticnet linear vorp_diff $vorppreds, alpha(0) rseed(42) nfolds(10)
* Optimal lambda = 0.3632288

elasticnet linear vorp_diff $vorppreds, alpha(0) lambda(0.3632288) nfolds(10)
* RMSE = 0.8643
estimates store ridge_vorp_unstd

/*--- VORP: Lasso — CV for optimal lambda (unstandardized) ---*/
elasticnet linear vorp_diff $vorppreds, alpha(1) rseed(42) nfolds(10)
* Optimal lambda = 0.0078255

elasticnet linear vorp_diff $vorppreds, alpha(1) lambda(0.0078255) nfolds(10)
* RMSE = 0.7878
estimates store lasso_vorp_unstd

/*--- VORP: PCA (unstandardized) — reuse previously gathered PCs ---*/
reg vorp_diff pc_vorp1-pc_vorp95, r nocons
* RMSE = 0.7958
estimates save "pca_vorp_unstd.ster", replace


/*===========================================================================
  SECTION 12: OUT-OF-SAMPLE PREDICTION SETUP
  Store in-sample moments, then standardize OOS data using IS means/SDs
===========================================================================*/

* Define a combined global of all non-multicollinear independent + dependent variables
* global everypred $perpreds $bpmpreds $vorppreds per_diff bpm_diff vorp_diff per_diff_std bpm_diff_std vorp_diff_std 

* Save in-sample means and standard deviations
postfile handle str32 varname mean sd using "train_moments.dta", replace
foreach v of global everypred {
    quietly sum `v'
    post handle ("`v'") (r(mean)) (r(sd))
}
postclose handle

* In OOS data: preserve, load moments, restore, then standardize
preserve
    use "train_moments.dta", clear
    local n = _N
    forvalues i = 1/`n' {
        local vname = varname[`i']
        scalar mean_`vname' = mean[`i']
        scalar sd_`vname'   = sd[`i']
    }
restore
foreach v of global everypred {
    gen `v'_std = (`v' - mean_`v') / sd_`v'
}


/*===========================================================================
  SECTION 13: OOS PREDICTIONS
===========================================================================*/

/*--- OLS predictions ---*/
estimates use ols_per
predict yhat_ols_per
(option xb assumed; fitted values)

estimates use ols_bpm
predict yhat_ols_bpm

estimates use ols_vorp
predict yhat_ols_vorp

estimates use ols_per_unstd
predict yhat_ols_per_unstd

estimates use ols_bpm_unstd
predict yhat_ols_bpm_unstd

estimates use ols_vorp_unstd
predict yhat_ols_vorp_unstd

/*--- Ridge predictions ---*/
estimates restore ridge_per
predict y_hat_ridge_per

estimates restore ridge_bpm
predict y_hat_ridge_bpm

estimates restore ridge_vorp
predict y_hat_ridge_vorp

estimates restore ridge_per_unstd
predict y_hat_ridge_per_unstd

estimates restore ridge_bpm_unstd
predict y_hat_ridge_bpm_unstd

estimates restore ridge_vorp_unstd
predict y_hat_ridge_vorp_unstd

/*--- Lasso predictions ---*/
estimates restore lasso_per
predict y_hat_lasso_per

estimates restore lasso_bpm
predict y_hat_lasso_bpm

estimates restore lasso_vorp
predict y_hat_lasso_vorp

estimates restore lasso_per_unstd
predict y_hat_lasso_per_unstd

estimates restore lasso_bpm_unstd
predict y_hat_lasso_bpm_unstd

estimates restore lasso_vorp_unstd
predict y_hat_lasso_vorp_unstd

/*--- PCA predictions: reload loadings, score OOS data, then get fitted values ---*/

* PER
estimates use pca_loadings_per
quietly predict pc_per1-pc_per75, score
estimates use pca_per
predict y_hat_pca_per

* BPM
estimates use pca_loadings_bpm
quietly predict pc_bpm1-pc_bpm80, score
estimates use pca_bpm
predict y_hat_pca_bpm

* VORP
estimates use pca_loadings_vorp
quietly predict pc_vorp1-pc_vorp95, score
estimates use pca_vorp
predict y_hat_pca_vorp

* Unstandardized PCA predictions (reuse standardized loadings, unstd regression coefficients)
estimates use pca_per_unstd
predict y_hat_pca_per_unstd

estimates use pca_bpm_unstd
predict y_hat_pca_bpm_unstd

estimates use pca_vorp_unstd
predict y_hat_pca_vorp_unstd


/*===========================================================================
  SECTION 14: OOS RMSE
===========================================================================*/

/*--- Standardized PER ---*/
foreach m in yhat_ols_per y_hat_pca_per y_hat_ridge_per y_hat_lasso_per {
    gen err_`m' = (per_diff_std - `m')^2
    summarize err_`m'
    display "RMSE = " sqrt(r(mean))
}
* OLS RMSE   ≈ 0.74948
* PCA RMSE   ≈ 0.72513
* Ridge RMSE ≈ 0.71444
* Lasso RMSE ≈ 0.71557

/*--- Standardized BPM ---*/
foreach m in yhat_ols_bpm y_hat_pca_bpm y_hat_ridge_bpm y_hat_lasso_bpm {
    gen err_`m' = (bpm_diff_std - `m')^2
    summarize err_`m'
    display "RMSE = " sqrt(r(mean))
}
* OLS RMSE   ≈ 0.85435
* PCA RMSE   ≈ 0.85583
* Ridge RMSE ≈ 0.83918
* Lasso RMSE ≈ 0.84365

/*--- Standardized VORP ---*/
foreach m in yhat_ols_vorp y_hat_pca_vorp y_hat_ridge_vorp y_hat_lasso_vorp {
    gen err_`m' = (vorp_diff_std - `m')^2
    summarize err_`m'
    display "RMSE = " sqrt(r(mean))
}
* OLS RMSE   ≈ 0.90066
* PCA RMSE   ≈ 0.86554
* Ridge RMSE ≈ 0.85940
* Lasso RMSE ≈ 0.84814

/*--- Unstandardized PER ---*/
foreach m in yhat_ols_per_unstd y_hat_pca_per_unstd y_hat_ridge_per_unstd y_hat_lasso_per_unstd {
    gen err_`m' = (per_diff - `m')^2
    summarize err_`m'
    display "RMSE = " sqrt(r(mean))
}
* OLS RMSE   ≈ 2.6255
* PCA RMSE   ≈ 2.5421
* Ridge RMSE ≈ 2.4942
* Lasso RMSE ≈ 2.4973

/*--- Unstandardized BPM ---*/
foreach m in yhat_ols_bpm_unstd y_hat_pca_bpm_unstd y_hat_ridge_bpm_unstd y_hat_lasso_bpm_unstd {
    gen err_`m' = (bpm_diff - `m')^2
    summarize err_`m'
    display "RMSE = " sqrt(r(mean))
}
* OLS RMSE   ≈ 1.9356
* PCA RMSE   ≈ 1.9548
* Ridge RMSE ≈ 1.8953
* Lasso RMSE ≈ 1.8994

/*--- Unstandardized VORP ---*/
foreach m in yhat_ols_vorp_unstd y_hat_pca_vorp_unstd y_hat_ridge_vorp_unstd y_hat_lasso_vorp_unstd {
    gen err_`m' = (vorp_diff - `m')^2
    summarize err_`m'
    display "RMSE = " sqrt(r(mean))
}
* OLS RMSE   ≈ 0.8327
* PCA RMSE   ≈ 0.8017
* Ridge RMSE ≈ 0.7926
* Lasso RMSE ≈ 0.7806


/*===========================================================================
  SECTION 15: OOS R-SQUARED
===========================================================================*/

/*--- Standardized PER ---*/
foreach m in yhat_ols_per y_hat_pca_per y_hat_ridge_per y_hat_lasso_per {
    summarize err_`m'
    scalar SSR = r(sum)
    quietly summarize per_diff_std
    scalar TSS = r(Var) * (r(N) - 1)
    display "OOS R-Squared `m' = " 1 - (SSR/TSS)
}
* OLS   ≈ 0.039
* PCA   ≈ 0.101
* Ridge ≈ 0.127
* Lasso ≈ 0.124

/*--- Standardized BPM ---*/
foreach m in yhat_ols_bpm y_hat_pca_bpm y_hat_ridge_bpm y_hat_lasso_bpm {
    summarize err_`m'
    scalar SSR = r(sum)
    quietly summarize bpm_diff_std
    scalar TSS = r(Var) * (r(N) - 1)
    display "OOS R-Squared `m' = " 1 - (SSR/TSS)
}
* OLS   ≈ 0.199
* PCA   ≈ 0.196
* Ridge ≈ 0.227
* Lasso ≈ 0.219

/*--- Standardized VORP ---*/
foreach m in yhat_ols_vorp y_hat_pca_vorp y_hat_ridge_vorp y_hat_lasso_vorp {
    summarize err_`m'
    scalar SSR = r(sum)
    quietly summarize vorp_diff_std
    scalar TSS = r(Var) * (r(N) - 1)
    display "OOS R-Squared `m' = " 1 - (SSR/TSS)
}
* OLS   ≈ 0.109
* PCA   ≈ 0.178
* Ridge ≈ 0.189
* Lasso ≈ 0.210

/*===========================================================================
  END OF DO-FILE
===========================================================================*/
