import pandas as pd
from statsmodels.stats.multicomp import pairwise_tukeyhsd
from scipy.stats import f_oneway
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

def run_tukey_hsd(columns):
    dfs = load_and_clean()
    group_names = ["BotConfirmative", "BotCritical", "Control", "Static"]
    results = {}
    for col in columns:
        # Combine all groups into a single Series and create a group label array
        data = []
        labels = []
        for i, df in enumerate(dfs):
            vals = df[col].dropna().astype(float)
            data.extend(vals)
            labels.extend([group_names[i]] * len(vals))
        if len(set(labels)) < 2 or len(data) < 2:
            results[col] = None
            continue
        tukey = pairwise_tukeyhsd(endog=data, groups=labels, alpha=0.05)
        results[col] = tukey
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
    results = run_tukey_hsd(columns_to_test)
    print("Tukey's HSD Post-hoc Test Results:")
    for col, tukey in results.items():
        print(f"\n{col}:")
        if tukey is None:
            print("  Not enough data for Tukey's HSD.")
        else:
            print(tukey.summary()) 