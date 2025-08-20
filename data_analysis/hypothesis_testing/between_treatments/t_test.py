import pandas as pd
from scipy.stats import ttest_ind
import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../../..')))

# Import your cleaning functions (assume they are in data_analysis/helper/clean_data.py)
from data_analysis.helper.clean_data import clean_dialogue, clean_static_and_control
from statsmodels.stats.power import TTestIndPower
import numpy as np

def required_n_ttest(effect_size, alpha=0.05, power=0.8, ratio=1.0):
    analysis = TTestIndPower()
    n_per_group = analysis.solve_power(effect_size=effect_size, alpha=alpha, power=power, ratio=ratio)
    return int(np.ceil(n_per_group)) if not np.isnan(n_per_group) else np.nan

# Example file paths (update as needed)
dialogue_files = [
    'data_analysis/data/Apollolytics-DialogueBotConfirmativePre.csv',
    'data_analysis/data/Apollolytics-DialogueBotCriticalPre.csv'
]
static_control_files = [
    'data_analysis/data/Apollolytics-DialogueControlPre.csv',
    'data_analysis/data/Apollolytics-DialogueStaticPre.csv',
    'data_analysis/data/Apollolytics-DialogueWithout.csv'
]

def load_and_clean():
    dfs = []
    for file in dialogue_files:
        df = pd.read_csv(file)
        df = clean_dialogue(df)
        dfs.append(df)
    for file in static_control_files:
        df = pd.read_csv(file)
        df = clean_static_and_control(df)
        dfs.append(df)
    return dfs

def calculate_ttest_power(group1, group2, alpha=0.05):
    analysis = TTestIndPower()
    n1 = len(group1)
    n2 = len(group2)
    if n1 < 2 or n2 < 2:
        return np.nan, np.nan
    # Calculate effect size (Cohen's d)
    mean1, mean2 = np.mean(group1), np.mean(group2)
    std1, std2 = np.std(group1, ddof=1), np.std(group2, ddof=1)
    pooled_std = np.sqrt(((n1-1)*std1**2 + (n2-1)*std2**2) / (n1+n2-2))
    if pooled_std == 0:
        return np.nan, np.nan
    effect_size = (mean1 - mean2) / pooled_std
    power = analysis.power(effect_size=abs(effect_size), nobs1=n1, ratio=n2/n1, alpha=alpha)
    return power, effect_size

def run_pairwise_ttests(columns):
    dfs = load_and_clean()
    group_names = ["BotConfirmative", "BotCritical", "Control", "Static", "Without"]
    results = {}
    n = len(dfs)
    for col in columns:
        col_results = {}
        for i in range(n):
            for j in range(i+1, n):
                group1 = dfs[i][col].dropna().astype(float)
                group2 = dfs[j][col].dropna().astype(float)
                if len(group1) < 2 or len(group2) < 2:
                    col_results[f"{group_names[i]} vs {group_names[j]}"] = None
                    continue
                t_stat, p_val = ttest_ind(group1, group2, equal_var=False)  # Welch's t-test
                power, effect_size = calculate_ttest_power(group1, group2)
                n_needed = required_n_ttest(effect_size, alpha=0.05, power=0.8, ratio=len(group2)/len(group1)) if not np.isnan(effect_size) and effect_size != 0 else np.nan
                col_results[f"{group_names[i]} vs {group_names[j]}"] = (t_stat, p_val, power, effect_size, len(group1), len(group2), n_needed)
        results[col] = col_results
    return results

if __name__ == '__main__':
    columns_to_test = [
        'thinkingmode_quickskim_slowcarefulread',
        'thinkingmode_absorbingseveral_focusingone',
        'thinkingmode_spontaneous_deliberate',
        'thinkingmode_easy_automatic_significanteffort',
        'thinkingmode_connections_rules',
        'thinkingmode_initialimpressions_regularlyupdating',
        'newseval_knowledgebefore',
        'newseval_accuracy',
        'newseval_bias',
        'newseval_informative',
        'newseval_believable_trust',
        'newseval_clear_wellwritten',
        # 'nps_score',  # Commented out as it doesn't exist in Without dataset
        'thinkingmode_mean',
        'newseval_mean'
    ]
    results = run_pairwise_ttests(columns_to_test)
    print("Pairwise t-test Results:")
    for col, pairs in results.items():
        print(f"\n{col}:")
        print(f"{'Group 1':<18} {'Group 2':<18} {'t-stat':>10} {'p-value':>10} {'Significance':>12} {'Power':>10} {'Cohen\'s d':>10} {'n1':>6} {'n2':>6} {'needed n':>10}")
        print('-' * 120)
        for pair, res in pairs.items():
            group1, group2 = pair.split(' vs ')
            if res is None:
                print(f"{group1:<18} {group2:<18} {'N/A':>10} {'N/A':>10} {'':>12} {'N/A':>10} {'N/A':>10} {'N/A':>6} {'N/A':>6} {'N/A':>10}")
            else:
                t_stat, p_val, power, effect_size, n1, n2, n_needed = res
                if p_val < 0.001:
                    sig = '***'
                elif p_val < 0.01:
                    sig = '**'
                elif p_val < 0.05:
                    sig = '*'
                else:
                    sig = ''
                print(f"{group1:<18} {group2:<18} {t_stat:10.4f} {p_val:10.4g} {sig:>12} {power:10.3f} {effect_size:10.3f} {n1:6d} {n2:6d} {n_needed:10}") 