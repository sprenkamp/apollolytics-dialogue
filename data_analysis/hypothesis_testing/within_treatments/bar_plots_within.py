import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
import sys
import os
import numpy as np
from scipy import stats
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../../..')))

# Import your cleaning functions
from data_analysis.helper.clean_data import clean_dialogue, clean_static_and_control

# Ensure plots directory exists
os.makedirs('data_analysis/hypothesis_testing/within_treatments/plots', exist_ok=True)

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
    
    # Mean variables
    'thinkingmode_mean': 'Thinking Mode - Overall Mean',
    'newseval_mean': 'News Evaluation - Overall Mean'
}

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
    
    # Debug: Check what variables are available in each dataset
    print(f"Critical columns: {len(dialogue_critical_clean.columns)}")
    print(f"Confirmative columns: {len(dialogue_confirmative_clean.columns)}")
    print(f"Static columns: {len(dialogue_static_clean.columns)}")
    print(f"Control columns: {len(dialogue_control_clean.columns)}")
    print(f"Without columns: {len(dialogue_without_clean.columns)}")
    
    # Check for post-reading variables in Control
    control_post_vars = [col for col in dialogue_control_clean.columns if col.startswith('post_reading_')]
    print(f"Control post-reading variables: {control_post_vars}")
    
    return {
        'Critical': dialogue_critical_clean,
        'Confirmative': dialogue_confirmative_clean,
        'Static': dialogue_static_clean,
        'Control': dialogue_control_clean,
        'Without': dialogue_without_clean
    }

def perform_ttest(pre_scores, post_scores):
    """Perform paired t-test and return p-value and significance level."""
    if len(pre_scores) < 2 or len(post_scores) < 2:
        return None, None
    
    try:
        # Perform paired t-test
        t_stat, p_value = stats.ttest_rel(pre_scores, post_scores)
        return p_value, t_stat
    except:
        return None, None

def add_significance_marker(ax, pre_mean, post_mean, p_value, y_offset_factor=0.1):
    """Add significance marker above the bars based on t-test p-value."""
    if p_value is None:
        return
    
    # Get the maximum y value for positioning
    max_y = max(pre_mean, post_mean)
    y_offset = max_y * y_offset_factor
    
    # Determine significance level
    if p_value < 0.001:
        marker = '***'
    elif p_value < 0.01:
        marker = '**'
    elif p_value < 0.05:
        marker = '*'
    else:
        return  # No significance
    
    # Add significance marker above the bars
    y_pos = max_y + y_offset
    ax.text(0.5, y_pos, marker, ha='center', va='bottom', fontsize=14, fontweight='bold')

def create_within_treatment_plots():
    """Create bar plots showing pre vs post comparisons for each treatment."""
    
    # Load data
    treatment_data = load_and_clean_data()
    
    # Define treatments list
    treatments = ['Critical', 'Confirmative', 'Static', 'Control', 'Without']
    
    # Check if Control treatment has post-reading variables
    control_df = treatment_data['Control']
    control_post_vars = [col for col in control_df.columns if col.startswith('post_reading_')]
    print(f"\nControl treatment post-reading variables found: {len(control_post_vars)}")
    if len(control_post_vars) == 0:
        print("WARNING: Control treatment has no post-reading variables!")
        print("This treatment will show 'Data not available' for all comparisons.")
        print("Available Control columns:", [col for col in control_df.columns if 'thinkingmode' in col or 'newseval' in col])
    
    # Define the variable pairs to compare (pre vs post)
    variable_pairs = [
        ('thinkingmode_quickskim_slowcarefulread', 'post_reading_thinkingmode_quickskim_slowcarefulread'),
        ('thinkingmode_absorbingseveral_focusingone', 'post_reading_thinkingmode_absorbingseveral_focusingone'),
        ('thinkingmode_spontaneous_deliberate', 'post_reading_thinkingmode_spontaneous_deliberate'),
        ('thinkingmode_easy_automatic_significanteffort', 'post_reading_thinkingmode_easy_automatic_significanteffort'),
        ('thinkingmode_connections_rules', 'post_reading_thinkingmode_connections_rules'),
        ('newseval_knowledgebefore', 'post_reading_newseval_knowledgebefore'),
        ('newseval_accuracy', 'post_reading_newseval_accuracy'),
        ('newseval_bias', 'post_reading_newseval_bias'),
        ('newseval_informative', 'post_reading_newseval_informative'),
        ('newseval_believable_trust', 'post_reading_newseval_believable_trust'),
        ('newseval_clear_wellwritten', 'post_reading_newseval_clear_wellwritten'),
        ('thinkingmode_mean', 'post_reading_thinkingmode_mean'),
        ('newseval_mean', 'post_reading_newseval_mean')
    ]
    
    # Debug: Check which variable pairs are available for each treatment
    print("\nChecking variable availability for each treatment:")
    for treatment in treatments:
        print(f"\n{treatment}:")
        available_pairs = []
        for pre_var, post_var in variable_pairs:
            # Check if the standard post_reading_ variable exists
            if pre_var in treatment_data[treatment].columns and post_var in treatment_data[treatment].columns:
                available_pairs.append(f"{pre_var} ✓")
            else:
                # Try post_intervention_ naming convention
                post_intervention_var = post_var.replace('post_reading_', 'post_intervention_')
                if pre_var in treatment_data[treatment].columns and post_intervention_var in treatment_data[treatment].columns:
                    available_pairs.append(f"{pre_var} ✓ (post_intervention)")
                else:
                    missing = []
                    if pre_var not in treatment_data[treatment].columns:
                        missing.append(pre_var)
                    if post_var not in treatment_data[treatment].columns and post_intervention_var not in treatment_data[treatment].columns:
                        missing.append(f"post variable (tried: {post_var}, {post_intervention_var})")
                    available_pairs.append(f"Missing: {', '.join(missing)}")
        print(f"  Available pairs: {len([p for p in available_pairs if '✓' in p])}/{len(variable_pairs)}")
        for i, pair_info in enumerate(available_pairs):
            if 'Missing:' in pair_info:
                print(f"    {variable_pairs[i][0]} vs {variable_pairs[i][1]}: {pair_info}")
    
    # Set up the plotting style
    plt.style.use('default')
    
    # Create individual plots for each variable pair
    for pre_var, post_var in variable_pairs:
        print(f"\nCreating plot for {pre_var} vs {post_var}")
        
        # Create a figure with subplots for each treatment
        # Calculate subplot layout for 5 treatments
        n_treatments = len(treatments)
        n_cols = 3  # 3 columns
        n_rows = (n_treatments + n_cols - 1) // n_cols  # Calculate rows needed
        fig, axes = plt.subplots(n_rows, n_cols, figsize=(18, 6*n_rows))
        plot_title = PLOT_HEADINGS.get(pre_var, pre_var.replace('_', ' ').title())
        fig.suptitle(f'With vs Without Intervention Comparison: {plot_title}', 
                    fontsize=16, fontweight='bold', y=0.98)
        
        # Use consistent colors from the TREATMENT_COLORS dictionary
        colors = [TREATMENT_COLORS[treatment] for treatment in treatments]
        
        # Flatten axes for easier indexing
        if n_rows == 1:
            axes = [axes] if n_cols == 1 else axes
        else:
            axes = axes.flatten()
            
        for i, (treatment, color) in enumerate(zip(treatments, colors)):
            ax = axes[i]
            df = treatment_data[treatment]
            
            # Try to find the post variable with either naming convention
            post_var_to_use = post_var
            if post_var not in df.columns:
                # Try post_intervention_ naming convention
                post_intervention_var = post_var.replace('post_reading_', 'post_intervention_')
                if post_intervention_var in df.columns:
                    post_var_to_use = post_intervention_var
                    print(f"  {treatment}: Using {post_intervention_var} instead of {post_var}")
            
            # Debug: Check what's missing
            missing_vars = []
            if pre_var not in df.columns:
                missing_vars.append(pre_var)
            if post_var_to_use not in df.columns:
                missing_vars.append(post_var_to_use)
            
            # Check if both variables exist
            if pre_var not in df.columns or post_var_to_use not in df.columns:
                ax.text(0.5, 0.5, f'Data not available\nfor {treatment}\nMissing: {", ".join(missing_vars)}', 
                       ha='center', va='center', transform=ax.transAxes, fontsize=10)
                ax.set_title(f'{treatment}', fontweight='bold')
                continue
            
            # Get pre and post scores
            pre_scores = df[pre_var].dropna().astype(float)
            post_scores = df[post_var_to_use].dropna().astype(float)
            
            # Only keep participants with both pre and post scores
            common_indices = pre_scores.index.intersection(post_scores.index)
            if len(common_indices) < 2:
                ax.text(0.5, 0.5, f'Insufficient data\nfor {treatment}', 
                       ha='center', va='center', transform=ax.transAxes, fontsize=12)
                ax.set_title(f'{treatment}', fontweight='bold')
                continue
            
            pre_scores = pre_scores.loc[common_indices]
            post_scores = post_scores.loc[common_indices]
            
            # Calculate means and standard errors
            pre_mean = pre_scores.mean()
            post_mean = post_scores.mean()
            pre_se = pre_scores.sem()
            post_se = post_scores.sem()
            
            # Create bar plot
            x_pos = [0, 1]
            means = [pre_mean, post_mean]
            errors = [pre_se, post_se]
            labels = ['Pre', 'Post']
            
            bars = ax.bar(x_pos, means, yerr=errors, capsize=5, alpha=0.8, 
                         edgecolor='black', linewidth=0.5, color=[color, color])
            
            # Customize the subplot
            ax.set_title(f'{treatment} (n={len(pre_scores)})', fontweight='bold', fontsize=12)
            ax.set_ylabel('Mean Score', fontsize=10)
            ax.set_xticks(x_pos)
            ax.set_xticklabels(labels)
            ax.grid(axis='y', alpha=0.3)
            
            # Add value labels on bars
            for bar, mean_val in zip(bars, means):
                height = bar.get_height()
                ax.text(bar.get_x() + bar.get_width()/2., height,
                       f'{mean_val:.2f}', ha='center', va='bottom', fontsize=10)
            
            # Perform t-test and add significance marker
            p_value, t_stat = perform_ttest(pre_scores, post_scores)
            add_significance_marker(ax, pre_mean, post_mean, p_value)
            
            # Add mean difference text
            mean_diff = post_mean - pre_mean
            ax.text(0.5, 0.95, f'Δ = {mean_diff:.2f}', ha='center', va='top', 
                   transform=ax.transAxes, fontsize=10, fontweight='bold',
                   bbox=dict(boxstyle="round,pad=0.3", facecolor="white", alpha=0.8))
        
        # Hide unused subplots
        for i in range(len(treatments), len(axes)):
            axes[i].set_visible(False)
        
        # Adjust layout
        plt.tight_layout()
        plt.subplots_adjust(top=0.92)
        
        # Save the plot
        clean_var_name = pre_var.replace('/', '_').replace(' ', '_').lower()
        output_path = f'data_analysis/hypothesis_testing/within_treatments/plots/within_treatment_{clean_var_name}.png'
        plt.savefig(output_path, dpi=300, bbox_inches='tight')
        print(f"Plot saved to: {output_path}")
        
            # Close the figure to free memory
    plt.close()

def create_means_summary_plot():
    """Create two separate plots: one for thinking mode means and one for news evaluation means."""
    
    # Load data
    treatment_data = load_and_clean_data()
    
    # Define treatments and their order
    treatments = ['Control', 'Static', 'Critical', 'Confirmative', 'Without']
    
    # Create two separate plots
    for var_type in ['thinkingmode_mean', 'newseval_mean']:
        # Set up the plotting style
        plt.style.use('default')
        
        # Create figure
        fig, ax = plt.subplots(figsize=(12, 6))
        
        # Prepare data for plotting
        bar_data = []
        bar_labels = []
        bar_colors = []
        bar_errors = []
        bar_pvalues = []
        
        # Collect data for each treatment
        for treatment in treatments:
            df = treatment_data[treatment]
            color = TREATMENT_COLORS[treatment]
            
            # Check if variable exists
            if var_type not in df.columns:
                continue
                
            # Get pre scores
            pre_scores = df[var_type].dropna().astype(float)
            
            # Try to find post variable with either naming convention
            if 'thinkingmode' in var_type:
                post_var = var_type.replace('thinkingmode_', 'post_reading_thinkingmode_')
            else:
                post_var = var_type.replace('newseval_', 'post_reading_newseval_')
            
            post_var_to_use = post_var
            
            if post_var not in df.columns:
                # Try post_intervention_ naming convention
                post_intervention_var = post_var.replace('post_reading_', 'post_intervention_')
                if post_intervention_var in df.columns:
                    post_var_to_use = post_intervention_var
            
            if post_var_to_use not in df.columns:
                continue
                
            # Get post scores
            post_scores = df[post_var_to_use].dropna().astype(float)
            
            # Only keep participants with both pre and post scores
            common_indices = pre_scores.index.intersection(post_scores.index)
            if len(common_indices) < 2:
                continue
                
            pre_scores = pre_scores.loc[common_indices]
            post_scores = post_scores.loc[common_indices]
            
            # Calculate means and standard errors
            pre_mean = pre_scores.mean()
            post_mean = post_scores.mean()
            pre_se = pre_scores.sem()
            post_se = post_scores.sem()
            
            # Perform t-test
            p_value, t_stat = perform_ttest(pre_scores, post_scores)
            
            # Add to plotting data
            bar_data.extend([pre_mean, post_mean])
            bar_errors.extend([pre_se, post_se])
            bar_pvalues.extend([p_value, p_value])  # Store p-value for both pre and post
            
            # Create labels
            bar_labels.extend([f'{treatment}\nWith Intervention', f'{treatment}\nWithout Intervention'])
            
            # Add colors (pre and post get same treatment color)
            bar_colors.extend([color, color])
        
        # Create the bar plot with error bars
        bars = ax.bar(range(len(bar_data)), bar_data, yerr=bar_errors, capsize=5, 
                      color=bar_colors, alpha=0.8, edgecolor='black', linewidth=0.5)
        
        # Customize the plot
        var_name = PLOT_HEADINGS.get(var_type, var_type.replace('_', ' ').title())
        # ax.set_title(f'{var_name}: With vs Without Intervention Comparison by Treatment', fontsize=14, fontweight='bold', pad=20)
        ax.set_ylabel('Mean Score', fontsize=12)
        ax.set_xlabel('Treatment Group', fontsize=12)
        
        # Set x-axis labels
        ax.set_xticks(range(len(bar_data)))
        ax.set_xticklabels(bar_labels, rotation=45, ha='right', fontsize=10)
        
        # Add grid
        ax.grid(axis='y', alpha=0.3)
        
        # Remove only the top and right spines (bounding box), keep x and y axes
        ax.spines['top'].set_visible(False)
        ax.spines['right'].set_visible(False)
        
        # Add value labels on bars
        for i, (bar, value) in enumerate(zip(bars, bar_data)):
            height = bar.get_height()
            # Position labels inside the bars for better readability
            ax.text(bar.get_x() + bar.get_width()/2., height/2,
                   f'{value:.2f}', ha='center', va='center', fontsize=9, fontweight='bold', color='black')
        
        # Add significance bars connecting pre and post bars for each treatment
        for treatment_idx, treatment in enumerate(treatments):
            # Find the indices for this treatment's pre and post bars
            pre_idx = treatment_idx * 2
            post_idx = treatment_idx * 2 + 1
            
            # Check if we have both bars and a valid p-value
            if (pre_idx < len(bar_pvalues) and post_idx < len(bar_pvalues) and 
                bar_pvalues[pre_idx] is not None and bar_pvalues[pre_idx] < 0.05):
                
                p_value = bar_pvalues[pre_idx]
                
                # Determine significance level
                if p_value < 0.001:
                    marker = '***'
                elif p_value < 0.01:
                    marker = '**'
                else:
                    marker = '*'
                
                # Get the positions of the pre and post bars
                pre_bar = bars[pre_idx]
                post_bar = bars[post_idx]
                
                # Calculate positions for the connecting bar
                pre_center = pre_bar.get_x() + pre_bar.get_width()/2
                post_center = post_bar.get_x() + post_bar.get_width()/2
                
                # Calculate height for the connecting bar (above the higher bar)
                pre_height = pre_bar.get_height()
                post_height = post_bar.get_height()
                pre_error = bar_errors[pre_idx] if pre_idx < len(bar_errors) else 0
                post_error = bar_errors[post_idx] if post_idx < len(bar_errors) else 0
                
                max_height = max(pre_height + pre_error, post_height + post_error)
                bar_y_pos = max_height + (max(bar_data) * 0.1)  # Add offset
                
                # Draw horizontal connecting bar
                ax.plot([pre_center, post_center], [bar_y_pos, bar_y_pos], 'k-', linewidth=2)
                
                # Draw vertical lines connecting to the bars
                ax.plot([pre_center, pre_center], [bar_y_pos, bar_y_pos - (max(bar_data) * 0.02)], 'k-', linewidth=2)
                ax.plot([post_center, post_center], [bar_y_pos, bar_y_pos - (max(bar_data) * 0.02)], 'k-', linewidth=2)
                
                # Add significance marker above the connecting bar
                ax.text((pre_center + post_center) / 2, bar_y_pos + (max(bar_data) * 0.02), 
                       marker, ha='center', va='bottom', fontsize=14, fontweight='bold')
        

        
        # Adjust layout
        plt.tight_layout()
        
        # Save the plot
        clean_var_name = var_type.replace('_', '_').lower()
        output_path = f'data_analysis/hypothesis_testing/within_treatments/plots/means_{clean_var_name}_plot.png'
        plt.savefig(output_path, dpi=300, bbox_inches='tight')
        print(f"Means plot for {var_type} saved to: {output_path}")
        
        # Close the figure to free memory
        plt.close()

def create_comprehensive_within_plot():
    """Create one comprehensive plot showing all within-treatment comparisons."""
    
    # Load data
    treatment_data = load_and_clean_data()
    
    # Define the variable pairs to compare (pre vs post)
    variable_pairs = [
        ('thinkingmode_quickskim_slowcarefulread', 'post_reading_thinkingmode_quickskim_slowcarefulread'),
        ('thinkingmode_absorbingseveral_focusingone', 'post_reading_thinkingmode_absorbingseveral_focusingone'),
        ('thinkingmode_spontaneous_deliberate', 'post_reading_thinkingmode_spontaneous_deliberate'),
        ('thinkingmode_easy_automatic_significanteffort', 'post_reading_thinkingmode_easy_automatic_significanteffort'),
        ('thinkingmode_connections_rules', 'post_reading_thinkingmode_connections_rules'),
        ('newseval_knowledgebefore', 'post_reading_newseval_knowledgebefore'),
        ('newseval_accuracy', 'post_reading_newseval_accuracy'),
        ('newseval_bias', 'post_reading_newseval_bias'),
        ('newseval_informative', 'post_reading_newseval_informative'),
        ('newseval_believable_trust', 'post_reading_newseval_believable_trust'),
        ('newseval_clear_wellwritten', 'post_reading_newseval_clear_wellwritten'),
        ('thinkingmode_mean', 'post_reading_thinkingmode_mean'),
        ('newseval_mean', 'post_reading_newseval_mean')
    ]
    
    # Filter out pairs that don't have data (check both naming conventions)
    valid_pairs = []
    for pre_var, post_var in variable_pairs:
        has_data = False
        for df in treatment_data.values():
            if pre_var in df.columns and (post_var in df.columns or 
                post_var.replace('post_reading_', 'post_intervention_') in df.columns):
                has_data = True
                break
        if has_data:
            valid_pairs.append((pre_var, post_var))
    
    print(f"Creating comprehensive plot with {len(valid_pairs)} valid variable pairs")
    
    # Check if we have any valid pairs
    if len(valid_pairs) == 0:
        print("No valid variable pairs found. Skipping comprehensive plot creation.")
        return
    
    # Calculate subplot layout
    n_cols = 5  # 5 treatments
    n_rows = len(valid_pairs)
    
    # Create the comprehensive figure
    fig, axes = plt.subplots(n_rows, n_cols, figsize=(24, 5*n_rows))
    fig.suptitle('Comprehensive Within-Treatment Analysis: Pre vs Post Comparisons', 
                fontsize=16, fontweight='bold', y=0.98)
    
    treatments = ['Critical', 'Confirmative', 'Static', 'Control', 'Without']
    # Use consistent colors from the TREATMENT_COLORS dictionary
    colors = [TREATMENT_COLORS[treatment] for treatment in treatments]
    
    # Create subplots
    for i, (pre_var, post_var) in enumerate(valid_pairs):
        for j, (treatment, color) in enumerate(zip(treatments, colors)):
            ax = axes[i, j]
            df = treatment_data[treatment]
            
            # Try to find the post variable with either naming convention
            post_var_to_use = post_var
            if post_var not in df.columns:
                # Try post_intervention_ naming convention
                post_intervention_var = post_var.replace('post_reading_', 'post_intervention_')
                if post_intervention_var in df.columns:
                    post_var_to_use = post_intervention_var
            
            # Check if both variables exist
            if pre_var not in df.columns or post_var_to_use not in df.columns:
                ax.text(0.5, 0.5, 'No data', ha='center', va='center', 
                       transform=ax.transAxes, fontsize=8)
                if i == 0:  # Only add treatment labels to first row
                    ax.set_title(f'{treatment}', fontweight='bold', fontsize=10)
                continue
            
            # Get pre and post scores
            pre_scores = df[pre_var].dropna().astype(float)
            post_scores = df[post_var_to_use].dropna().astype(float)
            
            # Only keep participants with both pre and post scores
            common_indices = pre_scores.index.intersection(post_scores.index)
            if len(common_indices) < 2:
                ax.text(0.5, 0.5, 'Insufficient\ndata', ha='center', va='center', 
                       transform=ax.transAxes, fontsize=8)
                if i == 0:
                    ax.set_title(f'{treatment}', fontweight='bold', fontsize=10)
                continue
            
            pre_scores = pre_scores.loc[common_indices]
            post_scores = post_scores.loc[common_indices]
            
            # Calculate means and standard errors
            pre_mean = pre_scores.mean()
            post_mean = post_scores.mean()
            pre_se = pre_scores.sem()
            post_se = post_scores.sem()
            
            # Create bar plot
            x_pos = [0, 1]
            means = [pre_mean, post_mean]
            errors = [pre_se, post_se]
            labels = ['Pre', 'Post']
            
            bars = ax.bar(x_pos, means, yerr=errors, capsize=3, alpha=0.8, 
                         edgecolor='black', linewidth=0.5, color=[color, color])
            
            # Customize the subplot
            if j == 0:  # Only add variable labels to first column
                plot_title = PLOT_HEADINGS.get(pre_var, pre_var.replace('_', ' ').title())
                ax.set_ylabel(plot_title, fontsize=9)
            if i == 0:  # Only add treatment labels to first row
                ax.set_title(f'{treatment}', fontweight='bold', fontsize=10)
            
            ax.set_xticks(x_pos)
            ax.set_xticklabels(labels, fontsize=8)
            ax.grid(axis='y', alpha=0.3)
            ax.tick_params(axis='y', labelsize=8)
            
            # Add value labels on bars
            for bar, mean_val in zip(bars, means):
                height = bar.get_height()
                ax.text(bar.get_x() + bar.get_width()/2., height,
                       f'{mean_val:.1f}', ha='center', va='bottom', fontsize=7)
    
    # Adjust layout
    plt.tight_layout()
    plt.subplots_adjust(top=0.95)
    
    # Save the comprehensive plot
    output_path = 'data_analysis/hypothesis_testing/within_treatments/plots/comprehensive_within_treatment_analysis.png'
    plt.savefig(output_path, dpi=300, bbox_inches='tight')
    print(f"Comprehensive plot saved to: {output_path}")
    
    # Close the figure to free memory
    plt.close()

if __name__ == "__main__":
    # Create individual within-treatment plots
    create_within_treatment_plots()
    
    # Create comprehensive plot
    create_comprehensive_within_plot()
    
    # Create means summary plot
    create_means_summary_plot()
    
    print(f"\n{'='*60}")
    print("WITHIN-TREATMENT PLOTS COMPLETE")
    print(f"{'='*60}")
    print("Individual plots show pre vs post comparisons for each variable and treatment.")
    print("Comprehensive plot shows all comparisons in one view.")
    print("Means summary plot shows all treatment means in one comprehensive view.") 