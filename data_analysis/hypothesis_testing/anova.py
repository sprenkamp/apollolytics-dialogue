import pandas as pd
from scipy.stats import f_oneway
import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

# Import your cleaning functions (assume they are in data_analysis/helper/clean_data.py)
from data_analysis.helper.clean_data import clean_dialogue, clean_static_and_control
from statsmodels.stats.power import FTestAnovaPower

# Example file paths (update as needed)
dialogue_files = [
    'data_analysis/data/Apollolytics-DialogueBotConfirmativePre.csv',
    'data_analysis/data/Apollolytics-DialogueBotCriticalPre.csv'
]
static_control_files = [
    'data_analysis/data/Apollolytics-DialogueControlPre.csv',
    'data_analysis/data/Apollolytics-DialogueStaticPre.csv'
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

def run_anova_on_columns(columns):
    dfs = load_and_clean()
    results = {}
    for col in columns:
        # Extract the column from each treatment group
        groups = [df[col].dropna().astype(float) for df in dfs]
        stat, p = f_oneway(*groups)
        results[col] = {'F': stat, 'p': p}
    return results

def calculate_power(effect_size, nobs, alpha=0.05, k_groups=4):
    """
    effect_size: Cohen's f
    nobs: number of observations per group (use min group size for conservative estimate)
    alpha: significance level
    k_groups: number of groups (treatments)
    """
    power = FTestAnovaPower().power(effect_size=effect_size, nobs=nobs, alpha=alpha, k_groups=k_groups)
    return power

if __name__ == '__main__':
    # Example usage: specify columns to test
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
        'nps_score'
        # Add more columns as needed
    ]
    dfs = load_and_clean()
    effect_size = 0.25  # Cohen's f (medium); replace with your estimate if you have one
    k_groups = 4
    alpha = 0.05

    print("\nANOVA and Power Analysis Results:")
    for col in columns_to_test:
        # ANOVA
        groups = [df[col].dropna().astype(float) for df in dfs]
        stat, p = f_oneway(*groups)
        sig = '*** SIGNIFICANT ***' if p < 0.05 else ''
        # Power
        nobs_col = min([len(g) for g in groups])
        power = calculate_power(effect_size, nobs_col, alpha=alpha, k_groups=k_groups)
        print(f"{col}: F = {stat:.3f}, p = {p:.3g} {sig} | Power: {power:.3f}") 