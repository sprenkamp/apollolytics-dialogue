import pandas as pd
import matplotlib.pyplot as plt
import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../../..')))

from data_analysis.helper.clean_data import clean_dialogue, clean_static_and_control

# Ensure plots directory exists
os.makedirs('plots', exist_ok=True)

# Load and clean data
dialogue_critical = pd.read_csv('data_analysis/data/Apollolytics-DialogueBotCriticalPre.csv')
dialogue_confirmative = pd.read_csv('data_analysis/data/Apollolytics-DialogueBotConfirmativePre.csv')
dialogue_static = pd.read_csv('data_analysis/data/Apollolytics-DialogueStaticPre.csv')
dialogue_control = pd.read_csv('data_analysis/data/Apollolytics-DialogueControlPre.csv')
dialogue_without = pd.read_csv('data_analysis/data/Apollolytics-DialogueWithout.csv')

# Clean data
critical_clean = clean_dialogue(dialogue_critical)
confirmative_clean = clean_dialogue(dialogue_confirmative)
static_clean = clean_static_and_control(dialogue_static)
control_clean = clean_static_and_control(dialogue_control)
without_clean = clean_static_and_control(dialogue_without)

# Count Yes/No for each treatment
treatments = ['Control', 'Static', 'Critical', 'Confirmative', 'Without']
dataframes = [control_clean, static_clean, critical_clean, confirmative_clean, without_clean]

yes_counts = []
no_counts = []
yes_percentages = []
no_percentages = []

for df in dataframes:
    counts = df['is_propaganda_general'].value_counts()
    yes_count = counts.get('Yes', 0)
    no_count = counts.get('No', 0)
    total = yes_count + no_count
    
    yes_counts.append(yes_count)
    no_counts.append(no_count)
    yes_percentages.append((yes_count / total) * 100 if total > 0 else 0)
    no_percentages.append((no_count / total) * 100 if total > 0 else 0)

# Create stacked bar chart
    fig, ax = plt.subplots(figsize=(12, 6))

# Create bars with consistent treatment colors
treatment_colors = ['#1f77b4', '#ff7f0e', '#d62728', '#2ca02c', '#9467bd']  # Control, Static, Critical, Confirmative, Without
bars = ax.bar(treatments, yes_percentages, label='Yes', color=treatment_colors, alpha=0.8)
bars2 = ax.bar(treatments, no_percentages, bottom=yes_percentages, label='No', color=treatment_colors, alpha=0.8)

# Add value labels on bars
for i, (yes_pct, no_pct, yes_count, no_count) in enumerate(zip(yes_percentages, no_percentages, yes_counts, no_counts)):
    ax.text(i, yes_pct/2, f'{yes_pct:.1f}%\n({yes_count})', ha='center', va='center', fontweight='bold')
    ax.text(i, yes_pct + no_pct/2, f'{no_pct:.1f}%\n({no_count})', ha='center', va='center', fontweight='bold')

# Customize plot
ax.set_title('Is Propaganda General Responses by Treatment', fontweight='bold', fontsize=14)
ax.set_ylabel('Percentage of Participants', fontsize=12)
ax.legend()
ax.grid(axis='y', alpha=0.3)

# Save plot
plt.tight_layout()
plt.savefig('data_analysis/hypothesis_testing/between_treatments/plots/is_propaganda_general_bar_plot.png', dpi=300, bbox_inches='tight')
print("Plot saved to: data_analysis/hypothesis_testing/between_treatments/plots/is_propaganda_general_bar_plot.png")

# Print summary
print("\nSummary:")
for treatment, yes_pct, no_pct, yes_count, no_count in zip(treatments, yes_percentages, no_percentages, yes_counts, no_counts):
    total = yes_count + no_count
    print(f"{treatment}: Yes={yes_pct:.1f}% ({yes_count}), No={no_pct:.1f}% ({no_count}), Total={total}")

# Load correct answers
import json
with open('data_analysis/data/demo_article/is_propaganda.json', 'r') as f:
    correct_answers = json.load(f)

# Analyze individual propaganda statements
print("\n" + "="*60)
print("INDIVIDUAL PROPAGANDA STATEMENTS ANALYSIS")
print("="*60)

# Calculate accuracy for each treatment
treatment_accuracies = []

for df in dataframes:
    correct_count = 0
    total_responses = 0
    
    for i in range(1, 9):
        col_name = f'is_propaganda_{i}'
        if col_name in df.columns:
            participant_responses = df[col_name].dropna()
            correct_answer = correct_answers[col_name]
            
            for response in participant_responses:
                if response == correct_answer:
                    correct_count += 1
                total_responses += 1
    
    accuracy = (correct_count / total_responses * 100) if total_responses > 0 else 0
    treatment_accuracies.append(accuracy)
    print(f"Total responses: {total_responses}, Correct: {correct_count}, Accuracy: {accuracy:.1f}%")

# Create accuracy bar chart
    fig2, ax2 = plt.subplots(figsize=(12, 6))

bars = ax2.bar(treatments, treatment_accuracies, color=['#1f77b4', '#ff7f0e', '#d62728', '#2ca02c'], alpha=0.8)

# Add value labels on bars
for i, (bar, acc) in enumerate(zip(bars, treatment_accuracies)):
    ax2.text(bar.get_x() + bar.get_width()/2, bar.get_height() + 1, 
             f'{acc:.1f}%', ha='center', va='bottom', fontweight='bold')

# Customize plot
ax2.set_title('Propaganda Detection Accuracy by Treatment', fontweight='bold', fontsize=14)
ax2.set_ylabel('Accuracy (%)', fontsize=12)
ax2.set_ylim(0, 100)
ax2.grid(axis='y', alpha=0.3)

# Save accuracy plot
plt.tight_layout()
plt.savefig('data_analysis/hypothesis_testing/between_treatments/plots/propaganda_accuracy_bar_plot.png', dpi=300, bbox_inches='tight')
print("\nAccuracy plot saved to: data_analysis/hypothesis_testing/between_treatments/plots/propaganda_accuracy_bar_plot.png")

# Print accuracy summary
print("\nAccuracy Summary:")
for treatment, accuracy in zip(treatments, treatment_accuracies):
    print(f"{treatment}: {accuracy:.1f}%") 