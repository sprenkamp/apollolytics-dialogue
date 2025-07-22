import pandas as pd
from scipy.stats import ttest_ind
import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

# Import your cleaning functions (assume they are in data_analysis/helper/clean_data.py)
from data_analysis.helper.clean_data import clean_dialogue, clean_static_and_control

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

def run_pairwise_ttests(columns):
    dfs = load_and_clean()
    group_names = ["BotConfirmative", "BotCritical", "Control", "Static"]
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
                col_results[f"{group_names[i]} vs {group_names[j]}"] = (t_stat, p_val)
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
        'nps_score'
    ]
    results = run_pairwise_ttests(columns_to_test)
    print("Pairwise t-test Results:")
    for col, pairs in results.items():
        print(f"\n{col}:")
        print(f"{'Group 1':<18} {'Group 2':<18} {'t-stat':>10} {'p-value':>10} {'Significance':>12}")
        print('-' * 75)
        for pair, res in pairs.items():
            group1, group2 = pair.split(' vs ')
            if res is None:
                print(f"{group1:<18} {group2:<18} {'N/A':>10} {'N/A':>10} {'':>12}")
            else:
                t_stat, p_val = res
                if p_val < 0.001:
                    sig = '***'
                elif p_val < 0.01:
                    sig = '**'
                elif p_val < 0.05:
                    sig = '*'
                else:
                    sig = ''
                print(f"{group1:<18} {group2:<18} {t_stat:10.4f} {p_val:10.4g} {sig:>12}") 