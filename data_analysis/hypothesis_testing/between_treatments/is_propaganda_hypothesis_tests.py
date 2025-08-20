import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import sys
import os
import json
from scipy.stats import chi2_contingency, f_oneway, chi2
from scipy.stats import ttest_ind
from statsmodels.stats.multicomp import pairwise_tukeyhsd
import seaborn as sns

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../../..')))

from data_analysis.helper.clean_data import clean_dialogue, clean_static_and_control

# Ensure plots directory exists
os.makedirs('data_analysis/hypothesis_testing/between_treatments/plots', exist_ok=True)

def load_and_clean_data():
    """Load and clean all treatment datasets."""
    dialogue_critical = pd.read_csv('data_analysis/data/Apollolytics-DialogueBotCriticalPre.csv')
    dialogue_confirmative = pd.read_csv('data_analysis/data/Apollolytics-DialogueBotConfirmativePre.csv')
    dialogue_static = pd.read_csv('data_analysis/data/Apollolytics-DialogueStaticPre.csv')
    dialogue_control = pd.read_csv('data_analysis/data/Apollolytics-DialogueControlPre.csv')
    dialogue_without = pd.read_csv('data_analysis/data/Apollolytics-DialogueWithout.csv')
    
    critical_clean = clean_dialogue(dialogue_critical)
    confirmative_clean = clean_dialogue(dialogue_confirmative)
    static_clean = clean_static_and_control(dialogue_static)
    control_clean = clean_static_and_control(dialogue_control)
    without_clean = clean_static_and_control(dialogue_without)
    
    return {
        'Critical': critical_clean,
        'Confirmative': confirmative_clean,
        'Static': static_clean,
        'Control': control_clean,
        'Without': without_clean
    }

def calculate_individual_accuracies(df, correct_answers):
    """Calculate accuracy for each participant."""
    participant_accuracies = []
    
    for _, participant in df.iterrows():
        correct_count = 0
        total_responses = 0
        
        for i in range(1, 9):
            col_name = f'is_propaganda_{i}'
            if col_name in df.columns and pd.notna(participant[col_name]):
                correct_answer = correct_answers[col_name]
                if participant[col_name] == correct_answer:
                    correct_count += 1
                total_responses += 1
        
        if total_responses > 0:
            accuracy = (correct_count / total_responses) * 100
            participant_accuracies.append(accuracy)
    
    return participant_accuracies

def run_hypothesis_tests():
    """Run various hypothesis tests on propaganda detection accuracy."""
    
    # Load data
    treatment_data = load_and_clean_data()
    
    # Load correct answers
    with open('data_analysis/data/demo_article/is_propaganda.json', 'r') as f:
        correct_answers = json.load(f)
    
    print("="*80)
    print("PROPAGANDA DETECTION HYPOTHESIS TESTS")
    print("="*80)
    
    # Calculate individual participant accuracies
    treatment_accuracies = {}
    all_accuracies = []
    all_labels = []
    
    for treatment_name, df in treatment_data.items():
        accuracies = calculate_individual_accuracies(df, correct_answers)
        treatment_accuracies[treatment_name] = accuracies
        all_accuracies.extend(accuracies)
        all_labels.extend([treatment_name] * len(accuracies))
        
        print(f"\n{treatment_name}:")
        print(f"  N = {len(accuracies)}")
        print(f"  Mean accuracy = {np.mean(accuracies):.1f}%")
        print(f"  SD = {np.std(accuracies):.1f}%")
        print(f"  Range = {np.min(accuracies):.1f}% - {np.max(accuracies):.1f}%")
    
    # 1. One-way ANOVA
    print(f"\n{'='*50}")
    print("1. ONE-WAY ANOVA")
    print(f"{'='*50}")
    
    groups = [treatment_accuracies[t] for t in ['Critical', 'Confirmative', 'Static', 'Control', 'Without']]
    f_stat, p_value = f_oneway(*groups)
    
    print(f"F-statistic: {f_stat:.3f}")
    print(f"p-value: {p_value:.6f}")
    print(f"Significance: {'***' if p_value < 0.001 else '**' if p_value < 0.01 else '*' if p_value < 0.05 else 'ns'}")
    
    # 2. Chi-square test for independence (contingency table)
    print(f"\n{'='*50}")
    print("2. CHI-SQUARE TEST FOR INDEPENDENCE")
    print(f"{'='*50}")
    
    # Create contingency table: Treatment vs High/Low accuracy
    contingency_data = []
    for treatment_name, accuracies in treatment_data.items():
        high_accuracy = sum(1 for acc in treatment_accuracies[treatment_name] if acc >= 75)  # 75% threshold
        low_accuracy = len(treatment_accuracies[treatment_name]) - high_accuracy
        contingency_data.append([high_accuracy, low_accuracy])
    
    contingency_table = pd.DataFrame(
        contingency_data,
        index=['Critical', 'Confirmative', 'Static', 'Control', 'Without'],
        columns=['High Accuracy (≥75%)', 'Low Accuracy (<75%)']
    )
    
    print("Contingency Table:")
    print(contingency_table)
    
    chi2_stat, chi2_p, dof, expected = chi2_contingency(contingency_table)
    print(f"\nChi-square statistic: {chi2_stat:.3f}")
    print(f"p-value: {chi2_p:.6f}")
    print(f"Degrees of freedom: {dof}")
    print(f"Significance: {'***' if chi2_p < 0.001 else '**' if chi2_p < 0.01 else '*' if chi2_p < 0.05 else 'ns'}")
    
    # 3. Pairwise t-tests
    print(f"\n{'='*50}")
    print("3. PAIRWISE T-TESTS")
    print(f"{'='*50}")
    
    treatments = ['Critical', 'Confirmative', 'Static', 'Control', 'Without']
    for i in range(len(treatments)):
        for j in range(i+1, len(treatments)):
            t_stat, p_val = ttest_ind(
                treatment_accuracies[treatments[i]], 
                treatment_accuracies[treatments[j]]
            )
            print(f"{treatments[i]} vs {treatments[j]}:")
            print(f"  t = {t_stat:.3f}, p = {p_val:.6f}")
            print(f"  Significance: {'***' if p_val < 0.001 else '**' if p_val < 0.01 else '*' if p_val < 0.05 else 'ns'}")
    
    # 4. Tukey's HSD test
    print(f"\n{'='*50}")
    print("4. TUKEY'S HSD TEST")
    print(f"{'='*50}")
    
    # Prepare data for Tukey test
    tukey_data = []
    tukey_labels = []
    for treatment_name, accuracies in treatment_accuracies.items():
        tukey_data.extend(accuracies)
        tukey_labels.extend([treatment_name] * len(accuracies))
    
    tukey_result = pairwise_tukeyhsd(tukey_data, tukey_labels, alpha=0.05)
    print(tukey_result)
    
    # 5. Effect size (Cohen's d for pairwise comparisons)
    print(f"\n{'='*50}")
    print("5. EFFECT SIZES (COHEN'S D)")
    print(f"{'='*50}")
    
    for i in range(len(treatments)):
        for j in range(i+1, len(treatments)):
            group1 = treatment_accuracies[treatments[i]]
            group2 = treatment_accuracies[treatments[j]]
            
            # Calculate Cohen's d
            pooled_std = np.sqrt(((len(group1)-1)*np.var(group1, ddof=1) + 
                                 (len(group2)-1)*np.var(group2, ddof=1)) / 
                                (len(group1) + len(group2) - 2))
            
            if pooled_std != 0:
                cohens_d = (np.mean(group1) - np.mean(group2)) / pooled_std
            else:
                cohens_d = 0
                
            print(f"{treatments[i]} vs {treatments[j]}: Cohen's d = {cohens_d:.3f}")
    
    # Create visualization
    create_hypothesis_test_plots(treatment_accuracies)
    
    return treatment_accuracies

def create_hypothesis_test_plots(treatment_accuracies):
    """Create plots for hypothesis test results."""
    
    # 1. Box plot
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(16, 6))
    
    # Box plot
    treatments = list(treatment_accuracies.keys())
    data = [treatment_accuracies[t] for t in treatments]
    
    bp = ax1.boxplot(data, labels=treatments, patch_artist=True)
    colors = ['#1f77b4', '#ff7f0e', '#2ca02c', '#d62728']
    for patch, color in zip(bp['boxes'], colors):
        patch.set_facecolor(color)
        patch.set_alpha(0.7)
    
    ax1.set_title('Propaganda Detection Accuracy by Treatment', fontweight='bold', fontsize=14)
    ax1.set_ylabel('Accuracy (%)', fontsize=12)
    ax1.grid(axis='y', alpha=0.3)
    
    # Violin plot
    all_data = []
    all_labels = []
    for treatment, accuracies in treatment_accuracies.items():
        all_data.extend(accuracies)
        all_labels.extend([treatment] * len(accuracies))
    
    df_plot = pd.DataFrame({'Treatment': all_labels, 'Accuracy': all_data})
    sns.violinplot(data=df_plot, x='Treatment', y='Accuracy', ax=ax2, palette=colors)
    ax2.set_title('Distribution of Accuracy Scores', fontweight='bold', fontsize=14)
    ax2.set_ylabel('Accuracy (%)', fontsize=12)
    ax2.grid(axis='y', alpha=0.3)
    
    plt.tight_layout()
    plt.savefig('data_analysis/hypothesis_testing/between_treatments/plots/propaganda_hypothesis_tests.png', 
                dpi=300, bbox_inches='tight')
    print(f"\nHypothesis test plots saved to: data_analysis/hypothesis_testing/between_treatments/plots/propaganda_hypothesis_tests.png")

if __name__ == "__main__":
    run_hypothesis_tests() 