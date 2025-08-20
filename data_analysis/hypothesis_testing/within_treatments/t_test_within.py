import pandas as pd
from scipy.stats import ttest_rel
import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../../..')))

# Import your cleaning functions
from data_analysis.helper.clean_data import clean_dialogue, clean_static_and_control
from statsmodels.stats.power import TTestPower
import numpy as np

# Ensure plots directory exists
os.makedirs('plots', exist_ok=True)

def load_and_clean_data():
    """Load and clean all four treatment datasets."""
    print("Loading and cleaning data...")
    
    # Load the four datasets
    dialogue_critical = pd.read_csv('data_analysis/data/Apollolytics-DialogueBotCriticalPre.csv')
    dialogue_confirmative = pd.read_csv('data_analysis/data/Apollolytics-DialogueBotConfirmativePre.csv')
    dialogue_static = pd.read_csv('data_analysis/data/Apollolytics-DialogueStaticPre.csv')
    dialogue_control = pd.read_csv('data_analysis/data/Apollolytics-DialogueControlPre.csv')
    dialogue_without = pd.read_csv('data_analysis/data/Apollolytics-DialogueWithout.csv')
    
    # Clean the data
    dialogue_critical_clean = clean_dialogue(dialogue_critical)
    dialogue_confirmative_clean = clean_dialogue(dialogue_confirmative)
    dialogue_static_clean = clean_static_and_control(dialogue_static)
    dialogue_control_clean = clean_static_and_control(dialogue_control)
    dialogue_without_clean = clean_static_and_control(dialogue_without)
    
    # Add treatment labels
    dialogue_critical_clean['treatment'] = 'Critical'
    dialogue_confirmative_clean['treatment'] = 'Confirmative'
    dialogue_static_clean['treatment'] = 'Static'
    dialogue_control_clean['treatment'] = 'Control'
    dialogue_without_clean['treatment'] = 'Without'
    
    return {
        'Critical': dialogue_critical_clean,
        'Confirmative': dialogue_confirmative_clean,
        'Static': dialogue_static_clean,
        'Control': dialogue_control_clean,
        'Without': dialogue_without_clean
    }

def calculate_power_and_effect_size(pre_scores, post_scores, alpha=0.05):
    """Calculate power and effect size for paired t-test."""
    if len(pre_scores) < 2 or len(post_scores) < 2:
        return np.nan, np.nan, np.nan
    
    # Calculate paired differences
    differences = np.array(post_scores) - np.array(pre_scores)
    
    # Calculate effect size (Cohen's d for paired samples)
    mean_diff = np.mean(differences)
    std_diff = np.std(differences, ddof=1)
    
    if std_diff == 0:
        return np.nan, np.nan, np.nan
    
    effect_size = mean_diff / std_diff
    
    # Calculate power
    analysis = TTestPower()
    power = analysis.power(effect_size=abs(effect_size), nobs=len(differences), alpha=alpha)
    
    return power, effect_size, mean_diff

def run_within_treatment_tests():
    """Run paired t-tests for each treatment comparing pre vs post scores."""
    
    # Load data
    treatment_data = load_and_clean_data()
    
    # Define the variable pairs to compare (pre vs post)
    variable_pairs = [
        ('thinkingmode_quickskim_slowcarefulread', 'post_intervention_thinkingmode_quickskim_slowcarefulread'),
        ('thinkingmode_absorbingseveral_focusingone', 'post_intervention_thinkingmode_absorbingseveral_focusingone'),
        ('thinkingmode_spontaneous_deliberate', 'post_intervention_thinkingmode_spontaneous_deliberate'),
        ('thinkingmode_easy_automatic_significanteffort', 'post_intervention_thinkingmode_easy_automatic_significanteffort'),
        ('thinkingmode_connections_rules', 'post_intervention_thinkingmode_connections_rules'),
        ('newseval_knowledgebefore', 'post_intervention_newseval_knowledgebefore'),
        ('newseval_accuracy', 'post_intervention_newseval_accuracy'),
        ('newseval_bias', 'post_intervention_newseval_bias'),
        ('newseval_informative', 'post_intervention_newseval_informative'),
        ('newseval_believable_trust', 'post_intervention_newseval_believable_trust'),
        ('newseval_clear_wellwritten', 'post_intervention_newseval_clear_wellwritten'),
        ('thinkingmode_mean', 'post_intervention_thinkingmode_mean'),
        ('newseval_mean', 'post_intervention_newseval_mean')
    ]
    
    results = {}
    
    for treatment_name, df in treatment_data.items():
        print(f"\n{'='*60}")
        print(f"WITHIN-TREATMENT ANALYSIS: {treatment_name}")
        print(f"{'='*60}")
        
        treatment_results = {}
        
        for pre_var, post_var in variable_pairs:
            print(f"\nComparing {pre_var} (With Intervention) vs {post_var} (Without Intervention):")
            
            # Check if both variables exist
            if pre_var not in df.columns or post_var not in df.columns:
                print(f"  Missing columns: {pre_var} or {post_var}")
                treatment_results[f"{pre_var}_vs_{post_var}"] = None
                continue
            
            # Get pre and post scores (drop NaN values)
            pre_scores = df[pre_var].dropna().astype(float)
            post_scores = df[post_var].dropna().astype(float)
            
            # Only keep participants with both pre and post scores
            common_indices = pre_scores.index.intersection(post_scores.index)
            if len(common_indices) < 2:
                print(f"  Insufficient data: {len(common_indices)} participants with both scores")
                treatment_results[f"{pre_var}_vs_{post_var}"] = None
                continue
            
            pre_scores = pre_scores.loc[common_indices]
            post_scores = post_scores.loc[common_indices]
            
            # Run paired t-test
            t_stat, p_val = ttest_rel(pre_scores, post_scores)
            
            # Calculate power and effect size
            power, effect_size, mean_diff = calculate_power_and_effect_size(pre_scores, post_scores)
            
            # Determine significance
            sig_level = ""
            if p_val < 0.001:
                sig_level = "***"
            elif p_val < 0.01:
                sig_level = "**"
            elif p_val < 0.05:
                sig_level = "*"
            
            # Store results
            result = {
                't_stat': t_stat,
                'p_val': p_val,
                'sig_level': sig_level,
                'power': power,
                'effect_size': effect_size,
                'mean_diff': mean_diff,
                'n': len(pre_scores),
                'pre_mean': pre_scores.mean(),
                'post_mean': post_scores.mean(),
                'pre_std': pre_scores.std(),
                'post_std': post_scores.std()
            }
            
            treatment_results[f"{pre_var}_vs_{post_var}"] = result
            
            # Print results
            print(f"  n = {len(pre_scores)}")
            print(f"  With Intervention: M = {pre_scores.mean():.3f}, SD = {pre_scores.std():.3f}")
            print(f"  Without Intervention: M = {post_scores.mean():.3f}, SD = {post_scores.std():.3f}")
            print(f"  t({len(pre_scores)-1}) = {t_stat:.3f}, p = {p_val:.3g} {sig_level}")
            print(f"  Cohen's d = {effect_size:.3f}, Power = {power:.3f}")
            print(f"  Mean difference = {mean_diff:.3f}")
        
        results[treatment_name] = treatment_results
    
    return results

def create_summary_table(results):
    """Create a summary table of all results."""
    print(f"\n{'='*100}")
    print("SUMMARY TABLE: WITHIN-TREATMENT COMPARISONS (With vs Without Intervention)")
    print(f"{'='*100}")
    
    # Get all variable pairs
    all_pairs = set()
    for treatment_results in results.values():
        for pair_name in treatment_results.keys():
            if treatment_results[pair_name] is not None:
                all_pairs.add(pair_name)
    
    all_pairs = sorted(list(all_pairs))
    
    # Print header
    print(f"{'Variable Pair':<50} {'Treatment':<12} {'n':<4} {'t':<8} {'p':<8} {'d':<8} {'Power':<8} {'Sig':<4}")
    print("-" * 100)
    
    # Print results for each variable pair and treatment
    for pair in all_pairs:
        for treatment in ['Critical', 'Confirmative', 'Static', 'Control']:
            if treatment in results and pair in results[treatment] and results[treatment][pair] is not None:
                res = results[treatment][pair]
                print(f"{pair:<50} {treatment:<12} {res['n']:<4} {res['t_stat']:<8.3f} {res['p_val']:<8.3g} {res['effect_size']:<8.3f} {res['power']:<8.3f} {res['sig_level']:<4}")

if __name__ == "__main__":
    # Run the within-treatment analyses
    results = run_within_treatment_tests()
    
    # Create summary table
    create_summary_table(results)
    
    print(f"\n{'='*100}")
    print("ANALYSIS COMPLETE")
    print(f"{'='*100}")
    print("Note: This analysis compares with vs without intervention scores within each treatment.")
    print("Positive effect sizes indicate higher scores without intervention.")
    print("Negative effect sizes indicate lower scores without intervention.") 