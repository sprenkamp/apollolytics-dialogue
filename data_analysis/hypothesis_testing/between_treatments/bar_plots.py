import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
import sys
import os
import numpy as np
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../../..')))

# Import your cleaning functions
from data_analysis.helper.clean_data import clean_dialogue, clean_static_and_control
from statsmodels.stats.multicomp import pairwise_tukeyhsd

# Ensure plots directory exists
import os
os.makedirs('data_analysis/hypothesis_testing/between_treatments/plots', exist_ok=True)

# Define consistent colors for each treatment
TREATMENT_COLORS = {
    'Critical': '#d62728',      # Red
    'Confirmative': '#2ca02c',  # Green
    'Static': '#ff7f0e',        # Orange
    'Control': '#1f77b4',       # Blue
    'Without': '#9467bd'     # Purple
}

# Define proper headings for each plot
PLOT_HEADINGS = {
    # Thinking mode variables
    'thinkingmode_quickskim_slowcarefulread': 'Quick Skim vs. Slow Careful Read',
    'thinkingmode_absorbingseveral_focusingone': 'Absorbing Several vs. Focusing on One',
    'thinkingmode_spontaneous_deliberate': 'Spontaneous vs. Deliberate',
    'thinkingmode_easy_automatic_significanteffort': 'Easy/Automatic vs. Significant Effort',
    'thinkingmode_connections_rules': 'Connections vs. Rules',
    'thinkingmode_initialimpressions_regularlyupdating': 'Initial Impressions vs. Regularly Updating',
    
    # News evaluation variables
    'newseval_knowledgebefore': 'Knowledge Before Reading',
    'newseval_accuracy': 'Perceived Accuracy',
    'newseval_bias': 'Perceived Bias',
    'newseval_informative': 'Perceived Informativeness',
    'newseval_believable_trust': 'Believability & Trust',
    'newseval_clear_wellwritten': 'Clarity & Writing Quality',
    
    # Other variables
    # 'nps_score': 'Net Promoter Score',  # Commented out as it doesn't exist in Without dataset
    
    # Mean variables
    'thinkingmode_mean': 'Thinking Mode - Overall Mean',
    'newseval_mean': 'News Evaluation - Overall Mean'
}

def get_significance_levels(data, groups, alpha=0.05):
    """Get significance levels for pairwise comparisons using Tukey's HSD."""
    try:
        tukey = pairwise_tukeyhsd(endog=data, groups=groups, alpha=alpha)
        return tukey
    except:
        return None

def add_significance_bars(ax, means, treatments, tukey_result, y_offset_factor=0.1):
    """Add significance bars to the plot with proper star notation."""
    if tukey_result is None:
        return
    
    # Get the maximum y value for positioning
    max_y = max(means.values)
    y_offset = max_y * y_offset_factor
    
    # Create significance bar positions
    bar_positions = {treatment: i for i, treatment in enumerate(treatments)}
    
    # Map treatment names from Tukey results to display names
    treatment_mapping = {
        'BotConfirmative': 'Confirmative',
        'BotCritical': 'Critical',
        'Control': 'Control',
        'Static': 'Static',
        'Without': 'Without'
    }
    
    # Get significant pairwise comparisons
    significant_comparisons = []
    
    # Access the pairwise comparison results correctly
    # The Tukey result contains all pairwise comparisons, we need to check which ones are significant
    for i, p_value in enumerate(tukey_result.pvalues):
        if p_value < 0.05:  # Only significant comparisons
            # Get the group names for this comparison
            # The groups are stored in the order they appear in the comparison
            group1_idx = i // (len(tukey_result.groupsunique) - 1)
            group2_idx = i % (len(tukey_result.groupsunique) - 1) + group1_idx + 1
            
            if group1_idx < len(tukey_result.groupsunique) and group2_idx < len(tukey_result.groupsunique):
                group1 = tukey_result.groupsunique[group1_idx]
                group2 = tukey_result.groupsunique[group2_idx]
                
                # Map to display names
                display_name1 = treatment_mapping.get(group1, group1)
                display_name2 = treatment_mapping.get(group2, group2)
                
                if display_name1 in bar_positions and display_name2 in bar_positions:
                    significant_comparisons.append({
                        'group1': display_name1,
                        'group2': display_name2,
                        'p_value': p_value,
                        'pos1': bar_positions[display_name1],
                        'pos2': bar_positions[display_name2]
                    })
    
    # Sort comparisons by position to avoid overlapping lines
    significant_comparisons.sort(key=lambda x: (x['pos1'], x['pos2']))
    
    # Add significance bars with proper stacking
    line_levels = {}  # Track which y-levels are occupied
    for comp in significant_comparisons:
        pos1, pos2 = comp['pos1'], comp['pos2']
        p_value = comp['p_value']
        
        # Determine star notation
        if p_value < 0.01:
            star = '**'
        else:
            star = '*'
        
        # Find available y-level for this comparison
        y_level = 0
        while True:
            y_pos = max_y + y_offset + (y_level * y_offset * 0.4)
            # Check if this level is free for the range [pos1, pos2]
            level_occupied = False
            for level, occupied_range in line_levels.items():
                if level == y_level and not (pos2 < occupied_range[0] or pos1 > occupied_range[1]):
                    level_occupied = True
                    break
            
            if not level_occupied:
                break
            y_level += 1
        
        # Mark this level as occupied
        line_levels[y_level] = (pos1, pos2)
        
        # Draw horizontal significance line
        ax.plot([pos1, pos2], [y_pos, y_pos], 'k-', linewidth=1.5)
        
        # Draw vertical lines connecting to bars
        ax.plot([pos1, pos1], [y_pos, y_pos - y_offset * 0.1], 'k-', linewidth=1.5)
        ax.plot([pos2, pos2], [y_pos, y_pos - y_offset * 0.1], 'k-', linewidth=1.5)
        
        # Add star notation above the line
        ax.text((pos1 + pos2) / 2, y_pos + y_offset * 0.1, star, 
                ha='center', va='bottom', fontsize=12, fontweight='bold')

def create_bar_plots():
    """Create bar plots showing means for each column across treatments."""
    
    # Load and clean data
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
    
    # Combine all data
    all_data = pd.concat([
        dialogue_critical_clean,
        dialogue_confirmative_clean,
        dialogue_static_clean,
        dialogue_control_clean,
        dialogue_without_clean
    ], ignore_index=True)
    
    # Columns to analyze (excluding treatment column)
    columns_to_plot = [
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
        # 'nps_score'  # Commented out as it doesn't exist in Without dataset
        # Add more columns as needed
    ]
    
    # Add mean columns
    mean_columns = ['thinkingmode_mean', 'newseval_mean']
    columns_to_plot.extend(mean_columns)
    
    # Set up the plotting style
    plt.style.use('default')
    
    # Define the treatment order
    treatment_order = ['Control', 'Static', 'Critical', 'Confirmative', 'Without']
    
    # Create individual plots for each column
    for column in columns_to_plot:
        print(f"\nProcessing column: {column}")
        
        # Check if column exists
        if column not in all_data.columns:
            print(f"Column {column} not found, skipping...")
            continue
        
        # Convert to numeric and handle errors
        all_data[column] = pd.to_numeric(all_data[column], errors='coerce')
        
        # Skip if no valid numeric data
        if all_data[column].isna().all():
            print(f"Column {column} has no valid numeric data, skipping...")
            continue
        
        # Create a new figure for each column
        plt.figure(figsize=(12, 6))
        
        # Calculate means by treatment (only for non-NaN values)
        means = all_data.groupby('treatment')[column].mean()
        std_errors = all_data.groupby('treatment')[column].sem()
        
        # Reorder means and std_errors according to treatment_order
        means_ordered = means.reindex(treatment_order)
        std_errors_ordered = std_errors.reindex(treatment_order)
        
        # Create bar plot with consistent colors for each treatment
        colors = [TREATMENT_COLORS.get(treatment, '#1f77b4') for treatment in means_ordered.index]
        bars = plt.bar(means_ordered.index, means_ordered.values, yerr=std_errors_ordered.values, 
                      capsize=5, alpha=0.8, edgecolor='black', linewidth=0.5, color=colors)
        
        # Get significance levels using Tukey's HSD
        # Prepare data for Tukey test
        data_for_tukey = []
        groups_for_tukey = []
        for treatment in treatment_order:
            treatment_data = all_data[all_data['treatment'] == treatment][column].dropna()
            data_for_tukey.extend(treatment_data.values)
            groups_for_tukey.extend([treatment] * len(treatment_data))
        
        tukey_result = get_significance_levels(data_for_tukey, groups_for_tukey)
        
        # Customize the plot
        plot_title = PLOT_HEADINGS.get(column, column.replace('_', ' ').title())
        # plt.title(plot_title, fontweight='bold', fontsize=14)
        plt.ylabel('Mean Value', fontsize=12)
        plt.xlabel('Treatment Group', fontsize=12)
        plt.grid(axis='y', alpha=0.3)
        
        # Remove only the top and right spines (bounding box), keep x and y axes
        ax = plt.gca()
        ax.spines['top'].set_visible(False)
        ax.spines['right'].set_visible(False)
        
        # Add value labels on bars
        for i, (bar, mean_val) in enumerate(zip(bars, means_ordered.values)):
            height = bar.get_height()
            # Position labels inside the bars for better readability
            plt.text(bar.get_x() + bar.get_width()/2., height/2,
                   f'{mean_val:.2f}', ha='center', va='center', fontsize=11, fontweight='bold', color='black')
        
        # Add significance bars
        add_significance_bars(plt.gca(), means_ordered, means_ordered.index, tukey_result)
        
        # Rotate x-axis labels if needed
        plt.xticks(rotation=45)
        
        # Adjust layout
        plt.tight_layout()
        
        # Save the individual plot
        # Clean column name for filename (replace special characters)
        clean_column_name = column.replace('/', '_').replace(' ', '_').lower()
        output_path = f'data_analysis/hypothesis_testing/between_treatments/plots/bar_plot_{clean_column_name}.png'
        plt.savefig(output_path, dpi=300, bbox_inches='tight')
        print(f"Saved plot to: {output_path}")
        
        # Close the figure to free memory
        plt.close()

def create_comprehensive_plot():
    """Create a comprehensive plot showing all variables in subplots."""
    
    # Load and clean data
    print("Loading and cleaning data for comprehensive plot...")
    
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
    
    # Combine all data
    all_data = pd.concat([
        dialogue_critical_clean,
        dialogue_confirmative_clean,
        dialogue_static_clean,
        dialogue_control_clean,
        dialogue_without_clean
    ], ignore_index=True)
    
    # Columns to analyze
    columns_to_plot = [
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
    
    # Filter out columns that don't exist or have no data
    valid_columns = []
    for column in columns_to_plot:
        if column in all_data.columns:
            all_data[column] = pd.to_numeric(all_data[column], errors='coerce')
            if not all_data[column].isna().all():
                valid_columns.append(column)
    
    print(f"Creating comprehensive plot with {len(valid_columns)} valid columns")
    
    # Calculate subplot layout
    n_cols = 4  # 4 columns
    n_rows = (len(valid_columns) + n_cols - 1) // n_cols  # Calculate rows needed
    
    # Create the comprehensive figure
    fig, axes = plt.subplots(n_rows, n_cols, figsize=(24, 5*n_rows))
    fig.suptitle('Comprehensive Analysis: All Variables by Treatment', fontsize=16, fontweight='bold', y=0.98)
    
    # Flatten axes for easier indexing
    if n_rows == 1:
        axes = [axes] if n_cols == 1 else axes
    else:
        axes = axes.flatten()
    
    # Define the treatment order
    treatment_order = ['Control', 'Static', 'Critical', 'Confirmative', 'Without']
    
    # Create subplots
    for i, column in enumerate(valid_columns):
        ax = axes[i]
        
        # Calculate means by treatment
        means = all_data.groupby('treatment')[column].mean()
        std_errors = all_data.groupby('treatment')[column].sem()
        
        # Reorder means and std_errors according to treatment_order
        means_ordered = means.reindex(treatment_order)
        std_errors_ordered = std_errors.reindex(treatment_order)
        
        # Create bar plot with consistent colors for each treatment
        colors = [TREATMENT_COLORS.get(treatment, '#1f77b4') for treatment in means_ordered.index]
        bars = ax.bar(means_ordered.index, means_ordered.values, yerr=std_errors_ordered.values, 
                     capsize=3, alpha=0.8, edgecolor='black', linewidth=0.5, color=colors)
        
        # Get significance levels using Tukey's HSD
        # Prepare data for Tukey test
        data_for_tukey = []
        groups_for_tukey = []
        for treatment in treatment_order:
            treatment_data = all_data[all_data['treatment'] == treatment][column].dropna()
            data_for_tukey.extend(treatment_data.values)
            groups_for_tukey.extend([treatment] * len(treatment_data))
        
        tukey_result = get_significance_levels(data_for_tukey, groups_for_tukey)
        
        # Customize the subplot
        plot_title = PLOT_HEADINGS.get(column, column.replace('_', ' ').title())
        ax.set_title(plot_title, fontweight='bold', fontsize=10)
        ax.set_ylabel('Mean Value', fontsize=9)
        ax.grid(axis='y', alpha=0.3)
        
        # Add value labels on bars
        for bar, mean_val in zip(bars, means_ordered.values):
            height = bar.get_height()
            ax.text(bar.get_x() + bar.get_width()/2., height,
                   f'{mean_val:.2f}', ha='center', va='bottom', fontsize=8)
        
        # Add significance bars
        add_significance_bars(ax, means_ordered, means_ordered.index, tukey_result)
        
        # Rotate x-axis labels
        ax.tick_params(axis='x', rotation=45)
        
        # Hide unused subplots
        if i >= len(valid_columns):
            ax.set_visible(False)
    
    # Adjust layout
    plt.tight_layout()
    
    # Save the comprehensive plot
    output_path = 'data_analysis/hypothesis_testing/between_treatments/plots/comprehensive_bar_plots.png'
    plt.savefig(output_path, dpi=300, bbox_inches='tight')
    print(f"Saved comprehensive plot to: {output_path}")
    
    # Close the figure to free memory
    plt.close()

def create_mean_plots():
    """Create individual plots for mean variables."""
    
    # Load and clean data
    print("Loading and cleaning data for mean plots...")
    
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
    
    # Combine all data
    all_data = pd.concat([
        dialogue_critical_clean,
        dialogue_confirmative_clean,
        dialogue_static_clean,
        dialogue_control_clean,
        dialogue_without_clean
    ], ignore_index=True)
    
    # Mean columns to plot
    mean_columns = ['thinkingmode_mean', 'newseval_mean']
    
    # Set up the plotting style
    plt.style.use('default')
    
    # Define the treatment order
    treatment_order = ['Control', 'Static', 'Critical', 'Confirmative', 'Without']
    
    # Create individual mean plots
    for column in mean_columns:
        print(f"\nProcessing mean column: {column}")
        
        # Check if column exists
        if column not in all_data.columns:
            print(f"Column {column} not found, skipping...")
            continue
        
        # Convert to numeric and handle errors
        all_data[column] = pd.to_numeric(all_data[column], errors='coerce')
        
        # Skip if no valid numeric data
        if all_data[column].isna().all():
            print(f"Column {column} has no valid numeric data, skipping...")
            continue
        
        # Create a new figure for each mean column
        plt.figure(figsize=(12, 6))
        
        # Calculate means by treatment (only for non-NaN values)
        means = all_data.groupby('treatment')[column].mean()
        std_errors = all_data.groupby('treatment')[column].sem()
        
        # Reorder means and std_errors according to treatment_order
        means_ordered = means.reindex(treatment_order)
        std_errors_ordered = std_errors.reindex(treatment_order)
        
        # Create bar plot with consistent colors for each treatment
        colors = [TREATMENT_COLORS.get(treatment, '#1f77b4') for treatment in means_ordered.index]
        bars = plt.bar(means_ordered.index, means_ordered.values, yerr=std_errors_ordered.values, 
                      capsize=5, alpha=0.8, edgecolor='black', linewidth=0.5, color=colors)
        
        # Get significance levels using Tukey's HSD
        # Prepare data for Tukey test
        data_for_tukey = []
        groups_for_tukey = []
        for treatment in treatment_order:
            treatment_data = all_data[all_data['treatment'] == treatment][column].dropna()
            data_for_tukey.extend(treatment_data.values)
            groups_for_tukey.extend([treatment] * len(treatment_data))
        
        tukey_result = get_significance_levels(data_for_tukey, groups_for_tukey)
        
        # Customize the plot
        plot_title = PLOT_HEADINGS.get(column, column.replace('_', ' ').title())
        # plt.title(plot_title, fontweight='bold', fontsize=14)
        plt.ylabel('Mean Value', fontsize=12)
        plt.xlabel('Treatment Group', fontsize=12)
        plt.grid(axis='y', alpha=0.3)
        
        # Remove only the top and right spines (bounding box), keep x and y axes
        ax = plt.gca()
        ax.spines['top'].set_visible(False)
        ax.spines['right'].set_visible(False)
        
        # Add value labels on bars
        for i, (bar, mean_val) in enumerate(zip(bars, means_ordered.values)):
            height = bar.get_height()
            # Position labels inside the bars for better readability
            plt.text(bar.get_x() + bar.get_width()/2., height/2,
                   f'{mean_val:.2f}', ha='center', va='center', fontsize=11, fontweight='bold', color='black')
        
        # Add significance bars
        add_significance_bars(plt.gca(), means_ordered, means_ordered.index, tukey_result)
        
        # Rotate x-axis labels if needed
        plt.xticks(rotation=45)
        
        # Adjust layout
        plt.tight_layout()
        
        # Save the individual mean plot
        # Clean column name for filename (replace special characters)
        clean_column_name = column.replace('/', '_').replace(' ', '_').lower()
        output_path = f'data_analysis/hypothesis_testing/between_treatments/plots/mean_plot_{clean_column_name}.png'
        plt.savefig(output_path, dpi=300, bbox_inches='tight')
        print(f"Saved mean plot to: {output_path}")
        
        # Close the figure to free memory
        plt.close()

if __name__ == "__main__":
    print("Creating individual bar plots...")
    create_bar_plots()
    
    print("\nCreating comprehensive plot...")
    create_comprehensive_plot()
    
    print("\nCreating mean plots...")
    create_mean_plots()
    
    print("\nAll plots created successfully!") 