import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

# Import your cleaning functions
from data_analysis.helper.clean_data import clean_dialogue, clean_static_and_control

def create_bar_plots():
    """Create bar plots showing means for each column across treatments."""
    
    # Load and clean data
    print("Loading and cleaning data...")
    
    # Load the four datasets
    dialogue_critical = pd.read_csv('data_analysis/data/Apollolytics-DialogueBotCriticalPre.csv')
    dialogue_confirmative = pd.read_csv('data_analysis/data/Apollolytics-DialogueBotConfirmativePre.csv')
    dialogue_static = pd.read_csv('data_analysis/data/Apollolytics-DialogueStaticPre.csv')
    dialogue_control = pd.read_csv('data_analysis/data/Apollolytics-DialogueControlPre.csv')
    
    # Clean the data
    dialogue_critical_clean = clean_dialogue(dialogue_critical)
    dialogue_confirmative_clean = clean_dialogue(dialogue_confirmative)
    dialogue_static_clean = clean_static_and_control(dialogue_static)
    dialogue_control_clean = clean_static_and_control(dialogue_control)
    
    # Add treatment labels
    dialogue_critical_clean['treatment'] = 'Critical'
    dialogue_confirmative_clean['treatment'] = 'Confirmative'
    dialogue_static_clean['treatment'] = 'Static'
    dialogue_control_clean['treatment'] = 'Control'
    
    # Combine all data
    all_data = pd.concat([
        dialogue_critical_clean,
        dialogue_confirmative_clean,
        dialogue_static_clean,
        dialogue_control_clean
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
        'nps_score'
        # Add more columns as needed
    ]
    
    # Set up the plotting style
    plt.style.use('default')
    
    # Define the treatment order
    treatment_order = ['Critical', 'Confirmative', 'Static', 'Control']
    
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
        plt.figure(figsize=(10, 6))
        
        # Calculate means by treatment (only for non-NaN values)
        means = all_data.groupby('treatment')[column].mean()
        std_errors = all_data.groupby('treatment')[column].sem()
        
        # Reorder means and std_errors according to treatment_order
        means_ordered = means.reindex(treatment_order)
        std_errors_ordered = std_errors.reindex(treatment_order)
        
        # Create bar plot with standard blue color
        bars = plt.bar(means_ordered.index, means_ordered.values, yerr=std_errors_ordered.values, 
                      capsize=5, alpha=0.8, edgecolor='black', linewidth=0.5, color='#1f77b4')
        
        # Customize the plot
        plt.title(f'{column}', fontweight='bold', fontsize=14)
        plt.ylabel('Mean Value', fontsize=12)
        plt.xlabel('Treatment', fontsize=12)
        plt.grid(axis='y', alpha=0.3)
        
        # Add value labels on bars
        for i, (bar, mean_val) in enumerate(zip(bars, means_ordered.values)):
            height = bar.get_height()
            if i < len(std_errors_ordered):
                std_err = std_errors_ordered.iloc[i]
            else:
                std_err = 0
            plt.text(bar.get_x() + bar.get_width()/2., height + std_err,
                    f'{mean_val:.2f}', ha='center', va='bottom', fontsize=11)
        
        # Rotate x-axis labels if needed
        plt.xticks(rotation=45)
        
        # Adjust layout
        plt.tight_layout()
        
        # Save the individual plot
        # Clean column name for filename (replace special characters)
        clean_column_name = column.replace('/', '_').replace(' ', '_').lower()
        output_path = f'data_analysis/hypothesis_testing/plots/bar_plot_{clean_column_name}.png'
        plt.savefig(output_path, dpi=300, bbox_inches='tight')
        print(f"Bar plot for '{column}' saved to: {output_path}")
        
        # Close the figure to free memory
        plt.close()
    
    # Print summary statistics
    print("\n" + "="*50)
    print("SUMMARY STATISTICS BY TREATMENT")
    print("="*50)
    
    for column in columns_to_plot:
        if column in all_data.columns:
            print(f"\n{column}:")
            print("-" * 30)
            try:
                summary = all_data.groupby('treatment')[column].agg(['count', 'mean', 'std']).round(3)
                print(summary)
            except Exception as e:
                print(f"Error calculating summary for {column}: {e}")
        else:
            print(f"\n{column}: Column not found in data")
        print()

def create_comprehensive_plot():
    """Create one massive plot with all bar plots as subplots."""
    
    # Load and clean data (same as before)
    print("Loading and cleaning data for comprehensive plot...")
    
    # Load the four datasets
    dialogue_critical = pd.read_csv('data_analysis/data/Apollolytics-DialogueBotCriticalPre.csv')
    dialogue_confirmative = pd.read_csv('data_analysis/data/Apollolytics-DialogueBotConfirmativePre.csv')
    dialogue_static = pd.read_csv('data_analysis/data/Apollolytics-DialogueStaticPre.csv')
    dialogue_control = pd.read_csv('data_analysis/data/Apollolytics-DialogueControlPre.csv')
    
    # Clean the data
    dialogue_critical_clean = clean_dialogue(dialogue_critical)
    dialogue_confirmative_clean = clean_dialogue(dialogue_confirmative)
    dialogue_static_clean = clean_static_and_control(dialogue_static)
    dialogue_control_clean = clean_static_and_control(dialogue_control)
    
    # Add treatment labels
    dialogue_critical_clean['treatment'] = 'Critical'
    dialogue_confirmative_clean['treatment'] = 'Confirmative'
    dialogue_static_clean['treatment'] = 'Static'
    dialogue_control_clean['treatment'] = 'Control'
    
    # Combine all data
    all_data = pd.concat([
        dialogue_critical_clean,
        dialogue_confirmative_clean,
        dialogue_static_clean,
        dialogue_control_clean
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
        'nps_score'
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
    fig, axes = plt.subplots(n_rows, n_cols, figsize=(20, 5*n_rows))
    fig.suptitle('Comprehensive Analysis: All Variables by Treatment', fontsize=16, fontweight='bold', y=0.98)
    
    # Flatten axes for easier indexing
    if n_rows == 1:
        axes = [axes] if n_cols == 1 else axes
    else:
        axes = axes.flatten()
    
    # Define the treatment order
    treatment_order = ['Critical', 'Confirmative', 'Static', 'Control']
    
    # Create subplots
    for i, column in enumerate(valid_columns):
        ax = axes[i]
        
        # Calculate means by treatment
        means = all_data.groupby('treatment')[column].mean()
        std_errors = all_data.groupby('treatment')[column].sem()
        
        # Reorder means and std_errors according to treatment_order
        means_ordered = means.reindex(treatment_order)
        std_errors_ordered = std_errors.reindex(treatment_order)
        
        # Create bar plot
        bars = ax.bar(means_ordered.index, means_ordered.values, yerr=std_errors_ordered.values, 
                     capsize=3, alpha=0.8, edgecolor='black', linewidth=0.5, color='#1f77b4')
        
        # Customize the subplot
        ax.set_title(f'{column}', fontweight='bold', fontsize=10)
        ax.set_ylabel('Mean Value', fontsize=9)
        ax.grid(axis='y', alpha=0.3)
        
        # Add value labels on bars
        for bar, mean_val in zip(bars, means_ordered.values):
            height = bar.get_height()
            ax.text(bar.get_x() + bar.get_width()/2., height,
                   f'{mean_val:.2f}', ha='center', va='bottom', fontsize=8)
        
        # Rotate x-axis labels
        ax.tick_params(axis='x', rotation=45, labelsize=8)
        ax.tick_params(axis='y', labelsize=8)
    
    # Hide empty subplots
    for i in range(len(valid_columns), len(axes)):
        axes[i].set_visible(False)
    
    # Adjust layout
    plt.tight_layout()
    plt.subplots_adjust(top=0.95)
    
    # Save the comprehensive plot
    output_path = 'data_analysis/hypothesis_testing/plots/comprehensive_bar_plots.png'
    plt.savefig(output_path, dpi=300, bbox_inches='tight')
    print(f"Comprehensive plot saved to: {output_path}")
    
    # Close the figure to free memory
    plt.close()

if __name__ == "__main__":
    # Create individual plots
    create_bar_plots()
    
    # Create comprehensive plot
    create_comprehensive_plot() 