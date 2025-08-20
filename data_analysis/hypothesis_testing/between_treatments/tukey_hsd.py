import pandas as pd
from statsmodels.stats.multicomp import pairwise_tukeyhsd
from scipy.stats import f_oneway
import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../../..')))

# Import your cleaning functions (assume they are in data_analysis/helper/clean_data.py)
from data_analysis.helper.clean_data import clean_dialogue, clean_static_and_control
from statsmodels.stats.power import FTestAnovaPower
import numpy as np

def calculate_power(effect_size, nobs, alpha=0.05, k_groups=4):
    power = FTestAnovaPower().power(effect_size=effect_size, nobs=nobs, alpha=alpha, k_groups=k_groups)
    return power

def required_n_anova(effect_size, alpha=0.05, power=0.8, k_groups=4):
    analysis = FTestAnovaPower()
    n_per_group = analysis.solve_power(effect_size=effect_size, alpha=alpha, power=power, k_groups=k_groups)
    return int(np.ceil(n_per_group)) if not np.isnan(n_per_group) else np.nan

def observed_cohens_f(groups):
    all_data = np.concatenate(groups)
    grand_mean = np.mean(all_data)
    k = len(groups)
    n = sum([len(g) for g in groups])
    ss_between = sum([len(g) * (np.mean(g) - grand_mean) ** 2 for g in groups])
    ss_within = sum([sum((g - np.mean(g)) ** 2) for g in groups])
    if ss_within + ss_between == 0:
        return np.nan
    f = np.sqrt(ss_between / (ss_within + ss_between))
    return f

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

def run_tukey_hsd(columns):
    dfs = load_and_clean()
    group_names = ["BotConfirmative", "BotCritical", "Control", "Static", "Without"]
    results = {}
    for col in columns:
        # Combine all groups into a single Series and create a group label array
        data = []
        labels = []
        groups = []
        for i, df in enumerate(dfs):
            vals = df[col].dropna().astype(float)
            data.extend(vals)
            labels.extend([group_names[i]] * len(vals))
            groups.append(vals)
        if len(set(labels)) < 2 or len(data) < 2:
            results[col] = None
            continue
        tukey = pairwise_tukeyhsd(endog=data, groups=labels, alpha=0.05)
        # Calculate ANOVA power for this column
        nobs_col = min([len(g) for g in groups])
        group_sizes = [len(g) for g in groups]
        effect_size = observed_cohens_f(groups)
        n_needed = required_n_anova(effect_size, alpha=0.05, power=0.8, k_groups=5) if not np.isnan(effect_size) and effect_size != 0 else np.nan
        power = calculate_power(effect_size, nobs_col, alpha=0.05, k_groups=5) if not np.isnan(effect_size) else np.nan
        results[col] = (tukey, power, effect_size, group_sizes, n_needed)
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
    results = run_tukey_hsd(columns_to_test)
    
    # Prepare output for both printing and saving
    output_lines = []
    output_lines.append("Tukey's HSD Post-hoc Test Results:")
    
    for col, res in results.items():
        output_lines.append(f"\n{col}:")
        if res is None:
            output_lines.append("  Not enough data for Tukey's HSD.")
        else:
            tukey, power, effect_size, group_sizes, n_needed = res
            output_lines.append(str(tukey.summary()))
            output_lines.append(f"ANOVA Power: {power:.3f} (Cohen's f: {effect_size:.3f}) | n per group: {group_sizes} | needed n: {n_needed}")
    
    # Print results
    for line in output_lines:
        print(line)
    
    # Save results to text file
    output_file = 'tukey_hsd_results.txt'
    with open(output_file, 'w') as f:
        for line in output_lines:
            f.write(line + '\n')
    
    print(f"\nResults saved to: {output_file}") 