import pandas as pd

def flip_bias_scale(df):
    """
    Flip the scale for bias questions so that higher values indicate less bias (more positive).
    Assumes the original scale is 1-7 where higher values indicate more bias.
    """
    bias_cols = ['newseval_bias', 'post_intervention_newseval_bias']
    
    for col in bias_cols:
        if col in df.columns:
            # Convert to numeric, then flip the scale (8 - original_value)
            # This transforms 1->7, 2->6, 3->5, 4->4, 5->3, 6->2, 7->1
            df[col] = pd.to_numeric(df[col], errors='coerce')
            df[col] = 8 - df[col]
            print(f"Flipped scale for {col}: now higher values indicate less bias")
    
    return df

def sort_columns_priority(df):
    """
    Sort columns so that priority columns appear first, followed by remaining columns.
    """
    # Define priority columns to appear first
    priority_columns = [
        'StartDate', 'EndDate', 'Status', 'IPAddress', 'Progress', 'Duration (in seconds)', 'Finished', 'RecordedDate', 'ResponseId', 'RecipientLastName', 'RecipientFirstName', 'RecipientEmail', 'ExternalReference', 'LocationLatitude', 'LocationLongitude', 'DistributionChannel', 'UserLanguage', 'Q2.1', 'prolific_id', 'devices', 'education', 'first_language', 'age', 'gender', 'education_level', 'country_of_residence', 'occupation', 'Q4.8', 'need_for_cognition_complex_problems', 'need_for_cognition_thinking_responsibility', 'need_for_cognition_thinking_not_fun', 'need_for_cognition_avoid_challenge', 'need_for_cognition_enjoy_problem_solving', 'need_for_cognition_prefer_intellectual_difficult', 'political_leaning', 'news_reading_frequency', 'news_media_trust', 'news_sources', 'thinkingmode_quickskim_slowcarefulread', 'thinkingmode_absorbingseveral_focusingone', 'thinkingmode_spontaneous_deliberate', 'thinkingmode_easy_automatic_significanteffort', 'thinkingmode_connections_rules', 'thinkingmode_initialimpressions_regularlyupdating', 'newseval_knowledgebefore', 'newseval_accuracy', 'newseval_bias', 'newseval_informative', 'newseval_believable_trust', 'newseval_clear_wellwritten', 'thinkingmode_mean', 'newseval_mean', 'post_intervention_thinkingmode_mean', 'post_intervention_newseval_mean', 'post_intervention_thinkingmode_quickskim_slowcarefulread', 'post_intervention_thinkingmode_absorbingseveral_focusingone', 'post_intervention_thinkingmode_spontaneous_deliberate', 'post_intervention_thinkingmode_easy_automatic_significanteffort', 'post_intervention_thinkingmode_connections_rules', 'post_intervention_why_you_felt_like_this', 'post_intervention_newseval_knowledgebefore', 'post_intervention_newseval_accuracy', 'post_intervention_newseval_bias', 'post_intervention_newseval_informative', 'post_intervention_newseval_believable_trust', 'post_intervention_newseval_clear_wellwritten', 'is_propaganda_general', 'why_propaganda',  'is_propaganda_1', 'is_propaganda_2', 'is_propaganda_3', 'is_propaganda_4', 'is_propaganda_5', 'is_propaganda_6', 'is_propaganda_7', 'is_propaganda_8', 'tool_improvement_suggestions', 'tool_awareness_propaganda', 'tool_most_helpful', 'NPS.5_NPS_GROUP', 'nps_score', 'tool_other_feedback',
    ]
    
    # Sort columns: priority columns first, then remaining columns
    existing_priority_cols = [col for col in priority_columns if col in df.columns]
    remaining_cols = [col for col in df.columns if col not in existing_priority_cols]
    sorted_cols = existing_priority_cols + remaining_cols
    return df[sorted_cols]

def add_thinkingmode_newseval_means(df):
    """
    Adds 'thinkingmode_mean', 'newseval_mean', 'post_intervention_thinkingmode_mean', and 'post_intervention_newseval_mean' columns to the DataFrame.
    """
    thinkingmode_cols = [
        'thinkingmode_quickskim_slowcarefulread',
        'thinkingmode_absorbingseveral_focusingone',
        'thinkingmode_spontaneous_deliberate',
        'thinkingmode_easy_automatic_significanteffort',
        'thinkingmode_connections_rules',
        'thinkingmode_initialimpressions_regularlyupdating',
    ]
    newseval_cols = [
        'newseval_knowledgebefore',
        'newseval_accuracy',
        'newseval_bias',
        'newseval_informative',
        'newseval_believable_trust',
        'newseval_clear_wellwritten',
    ]
    post_thinkingmode_cols = [
        'post_intervention_thinkingmode_quickskim_slowcarefulread',
        'post_intervention_thinkingmode_absorbingseveral_focusingone',
        'post_intervention_thinkingmode_spontaneous_deliberate',
        'post_intervention_thinkingmode_easy_automatic_significanteffort',
        'post_intervention_thinkingmode_connections_rules',
    ]
    post_newseval_cols = [
        'post_intervention_newseval_knowledgebefore',
        'post_intervention_newseval_accuracy',
        'post_intervention_newseval_bias',
        'post_intervention_newseval_informative',
        'post_intervention_newseval_believable_trust',
        'post_intervention_newseval_clear_wellwritten',
    ]
    
    df['thinkingmode_mean'] = df[thinkingmode_cols].apply(pd.to_numeric, errors='coerce').mean(axis=1)
    df['newseval_mean'] = df[newseval_cols].apply(pd.to_numeric, errors='coerce').mean(axis=1)
    
    # Add post-intervention means (only if columns exist)
    existing_post_thinkingmode = [col for col in post_thinkingmode_cols if col in df.columns]
    existing_post_newseval = [col for col in post_newseval_cols if col in df.columns]
    

    df['post_intervention_thinkingmode_mean'] = df[existing_post_thinkingmode].apply(pd.to_numeric, errors='coerce').mean(axis=1)
    df['post_intervention_newseval_mean'] = df[existing_post_newseval].apply(pd.to_numeric, errors='coerce').mean(axis=1)
    
    return df

def clean_dialogue(df):
    # Simple mapping
    simple_mapping = {
        "Q3.1": "prolific_id",
        "Q3.2": "devices",
        "Q3.3": "education",
        "Q3.4": "first_language",
        "Q4.2": "age",
        "Q4.3": "gender",
        "Q4.4": "education_level",
        "Q4.5_1": "country_of_residence",
        "Q4.7": "occupation",
        "Q5.1_1": "need_for_cognition_complex_problems",
        "Q5.1_2": "need_for_cognition_thinking_responsibility", 
        "Q5.1_3": "need_for_cognition_thinking_not_fun",
        "Q5.1_4": "need_for_cognition_avoid_challenge",
        "Q5.1_5": "need_for_cognition_enjoy_problem_solving",
        "Q5.1_6": "need_for_cognition_prefer_intellectual_difficult",
        "Q7.1_1": "political_leaning",
        "Q7.2_1": "news_reading_frequency", 
        "Q7.3_1": "news_media_trust",
        "Q7.4": "news_sources",
        'Q3_1.1': "post_intervention_thinkingmode_quickskim_slowcarefulread",
        'Q4_1.1': "post_intervention_thinkingmode_absorbingseveral_focusingone",
        'Q5_1.1': "post_intervention_thinkingmode_easy_automatic_significanteffort",
        'Q6_1.1': "post_intervention_thinkingmode_connections_rules",
        'Q7_1.1': "post_intervention_thinkingmode_initialimpressions_regularlyupdating",
        'Q8_1.1': "post_intervention_thinkingmode_spontaneous_deliberate",
        'Q9' : "post_intervention_why_you_felt_like_this",
        'Q10_1' : "post_intervention_newseval_knowledgebefore",
        'Q10_2' : "post_intervention_newseval_accuracy",
        'Q10_3' : "post_intervention_newseval_bias",
        'Q10_4' : "post_intervention_newseval_informative",
        'Q10_5' : "post_intervention_newseval_believable_trust",
        'Q10_6' : "post_intervention_newseval_clear_wellwritten",
        "Q11": "is_propaganda_general",
        "Q12": "why_propaganda",
        "Q14#1_1": "is_propaganda_1",
        "Q14#1_2": "is_propaganda_2", 
        "Q14#1_3": "is_propaganda_3",
        "Q14#1_4": "is_propaganda_4",
        "Q14#1_5": "is_propaganda_5",
        "Q14#1_6": "is_propaganda_6",
        "Q14#1_7": "is_propaganda_7",
        "Q14#1_8": "is_propaganda_8",
        "NPS.2": "tool_improvement_suggestions",
        "NPS.3": "tool_awareness_propaganda",
        "NPS.4": "tool_most_helpful",
        "NPS.5": "nps_score",
        "NPS.6": "tool_other_feedback"
    }
    df = df.rename(columns=simple_mapping)

    # Mapping from your canvas
    mapping = {
        "thinkingmode_quickskim_slowcarefulread": ["Q3_1", "Q374_1", "Q385_1"],
        "thinkingmode_absorbingseveral_focusingone": ["Q4_1", "Q375_1", "Q386_1"],
        "thinkingmode_spontaneous_deliberate": ["Q5_1", "Q376_1", "Q387_1"],
        "thinkingmode_easy_automatic_significanteffort": ["Q6_1", "Q377_1", "Q388_1"],
        "thinkingmode_connections_rules": ["Q7_1", "Q378_1", "Q389_1"],
        "thinkingmode_initialimpressions_regularlyupdating": ["Q8_1", "Q379_1", "Q390_1"],
        "newseval_knowledgebefore": ["Q9_1", "Q380_1", "Q391_1"],
        "newseval_accuracy": ["Q9_2", "Q380_2", "Q391_2"],
        "newseval_bias": ["Q9_3", "Q380_3", "Q391_3"],
        "newseval_informative": ["Q9_4", "Q380_4", "Q391_4"],
        "newseval_believable_trust": ["Q9_5", "Q380_5", "Q391_5"],
        "newseval_clear_wellwritten": ["Q9_6", "Q380_6", "Q391_6"],
    }

    # Create new mapped columns
    for new_col, source_cols in mapping.items():
        df[new_col] = df[source_cols].bfill(axis=1).iloc[:, 0]

    # Remove old columns that have been mapped
    mapped_cols = set(sum(mapping.values(), []))
    final_cols = [col for col in df.columns if col not in mapped_cols or col in mapping.keys()]
    df = df[final_cols]

    # Remove invalid prolific ids, non-English, and unwanted education
    df = df[df['prolific_id'].str.len() == 24]
    df = df[df.education == "Other"]
    df = df[df.first_language == "English"]
    df = df[df.Finished == "True"]
    # print(f'Number of participants before filtering short conversations smaller than 3 user turns: {len(df.prolific_id.unique())}')
    # Filter out participants with less than 3 user turns
    prolific_ids_with_few_user_turns = get_prolific_ids_with_few_user_turns(min_user_turns=3)
    # print(f'Number of participants with less than 3 user turns: {len(prolific_ids_with_few_user_turns)}')
    df = df[~df.prolific_id.isin(prolific_ids_with_few_user_turns)]
    # print(f'Number of participants after filtering short conversations smaller than 3 user turns: {len(df.prolific_id.unique())}')

    # Flip bias scale so higher values indicate less bias (more positive)
    # df = flip_bias_scale(df)
    
    # Add means
    df = add_thinkingmode_newseval_means(df)
    
    # drop if mean column is nan
    df = df.dropna(subset=['thinkingmode_mean', 'newseval_mean'])
    
    # Sort columns with priority columns first
    df = sort_columns_priority(df)

    return df


def get_prolific_ids_with_few_user_turns(min_user_turns=3):
    """
    Loads data from DynamoDB and returns a list of prolific_ids where any session has fewer than `min_user_turns` user messages.
    """
    import boto3
    import pandas as pd
    import os
    from dotenv import load_dotenv

    load_dotenv()
    aws_region = os.getenv('AWS_REGION', 'eu-north-1')
    endpoint_url = os.getenv('AWS_ENDPOINT_URL')
    DYNAMODB_TABLE = os.getenv('DYNAMODB_TABLE', 'apollolytics_dialogues')

    if endpoint_url:
        dynamodb = boto3.resource('dynamodb', region_name=aws_region, endpoint_url=endpoint_url)
    else:
        dynamodb = boto3.resource('dynamodb', region_name=aws_region)

    table = dynamodb.Table(DYNAMODB_TABLE)
    response = table.scan()
    items = response['Items']
    while 'LastEvaluatedKey' in response:
        response = table.scan(ExclusiveStartKey=response['LastEvaluatedKey'])
        items.extend(response['Items'])

    df = pd.DataFrame(items)
    # Only keep sessions with valid prolific IDs
    session_ids = df[df.prolific_id.str.len() == 24].session_id
    df = df[df.session_id.isin(session_ids)]
    # Forward fill prolific_id within each session (in case it's missing in some rows)
    df['prolific_id'] = df.groupby('session_id')['prolific_id'].ffill()
    # Count user messages per session
    user_turns = df[(df['event_type'] == 'message') & (df['role'] == 'user')].groupby('prolific_id').size()
    short_sessions = user_turns[user_turns < min_user_turns].index
    prolific_ids = df[df['prolific_id'].isin(short_sessions)]['prolific_id'].unique().tolist()
    return prolific_ids


def clean_static_and_control(df):
    #simple mapping
    simple_mapping = {
        "Q3.1": "prolific_id",
        "Q3.2": "devices",
        "Q3.3": "education",
        "Q3.4": "first_language",
        "Q4.2": "age",
        "Q4.3": "gender",
        "Q4.4": "education_level",
        "Q4.5_1": "country_of_residence",
        "Q4.7": "occupation",
        "Q5.1_1": "need_for_cognition_complex_problems",
        "Q5.1_2": "need_for_cognition_thinking_responsibility", 
        "Q5.1_3": "need_for_cognition_thinking_not_fun",
        "Q5.1_4": "need_for_cognition_avoid_challenge",
        "Q5.1_5": "need_for_cognition_enjoy_problem_solving",
        "Q5.1_6": "need_for_cognition_prefer_intellectual_difficult",
        "Q7.1_1": "political_leaning",
        "Q7.2_1": "news_reading_frequency", 
        "Q7.3_1": "news_media_trust",
        "Q7.4": "news_sources",
        'IM_1.3_1': "post_intervention_thinkingmode_quickskim_slowcarefulread",
        'IM_1.4_1': "post_intervention_thinkingmode_absorbingseveral_focusingone",
        'IM_1.5_1': "post_intervention_thinkingmode_easy_automatic_significanteffort",
        'IM_1.6_1': "post_intervention_thinkingmode_connections_rules",
        'IM_1.7_1': "post_intervention_thinkingmode_initialimpressions_regularlyupdating",
        'IM_1.8_1': "post_intervention_thinkingmode_spontaneous_deliberate",
        'IM_1.9': "post_intervention_why_you_felt_like_this",
        'IM_1.10_1' : "post_intervention_newseval_knowledgebefore",
        'IM_1.10_2' : "post_intervention_newseval_accuracy",
        'IM_1.10_3' : "post_intervention_newseval_bias",
        'IM_1.10_4' : "post_intervention_newseval_informative",
        'IM_1.10_5' : "post_intervention_newseval_believable_trust",
        'IM_1.10_6' : "post_intervention_newseval_clear_wellwritten",
        'IM_1.11' : "is_propaganda_general",
        'IM_1.12' : "why_propaganda",
        "IM_1.14#1_1": "is_propaganda_1",
        "IM_1.14#1_2": "is_propaganda_2", 
        "IM_1.14#1_3": "is_propaganda_3",
        "IM_1.14#1_4": "is_propaganda_4",
        "IM_1.14#1_5": "is_propaganda_5",
        "IM_1.14#1_6": "is_propaganda_6",
        "IM_1.14#1_7": "is_propaganda_7",
        "IM_1.14#1_8": "is_propaganda_8",
        "NPS.2": "tool_improvement_suggestions",
        "NPS.3": "tool_awareness_propaganda",
        "NPS.4": "tool_most_helpful",
        "NPS.5": "nps_score",
        "NPS.6": "tool_other_feedback"
    }

    df.rename(columns=simple_mapping, inplace=True)

    # Load mapping from your canvas (paste your mapping as a string)
    mapping = {
        "thinkingmode_quickskim_slowcarefulread": ["Q3_1", "Q397_1", "Q406_1"],
        "thinkingmode_absorbingseveral_focusingone": ["Q4_1", "Q398_1", "Q407_1"],
        "thinkingmode_spontaneous_deliberate": ["Q5_1", "Q399_1", "Q408_1"],
        "thinkingmode_easy_automatic_significanteffort": ["Q6_1", "Q400_1", "Q409_1"],
        "thinkingmode_connections_rules": ["Q7_1", "Q401_1", "Q410_1"],
        "thinkingmode_initialimpressions_regularlyupdating": ["Q8_1", "Q402_1", "Q411_1"],
        "newseval_knowledgebefore": ["Q9_1", "Q403_1", "Q412_1"],
        "newseval_accuracy": ["Q9_2", "Q403_2", "Q412_2"],
        "newseval_bias": ["Q9_3", "Q403_3", "Q412_3"],
        "newseval_informative": ["Q9_4", "Q403_4", "Q412_4"],
        "newseval_believable_trust": ["Q9_5", "Q403_5", "Q412_5"],
        "newseval_clear_wellwritten": ["Q9_6", "Q403_6", "Q412_6"],
        # "timing_firstclick": ["Q371_First Click", "Q393_First Click", "Q382_First Click", "Q2_First Click.1"],
        # "Timing_LastClick": ["Q371_Last Click", "Q393_Last Click", "Q382_Last Click", "Q2_Last Click.1"],
        # "Timing_PageSubmit": ["Q371_Page Submit", "Q393_Page Submit", "Q382_Page Submit", "Q2_Page Submit.1"],
        # "Timing_ClickCount": ["Q371_Click Count", "Q393_Click Count", "Q382_Click Count", "Q2_Click Count.1"]
    }

    # Create new mapped columns
    for new_col, source_cols in mapping.items():
        df[new_col] = df[source_cols].bfill(axis=1).iloc[:, 0]

    # Remove old columns that have been mapped
    mapped_cols = set(sum(mapping.values(), []))
    final_cols = [col for col in df.columns if col not in mapped_cols or col in mapping.keys()]
    df = df[final_cols]

    # Remove invalid prolific ids, non-English, and unwanted education
    df = df[df['prolific_id'].str.len() == 24]
    df = df[df.education == "Other"]
    df = df[df.first_language == "English"]
    df = df[df.Finished == "True"]

    # Flip bias scale so higher values indicate less bias (more positive)
    # df = flip_bias_scale(df)

    # Add means
    df = add_thinkingmode_newseval_means(df)
    
    # drop if mean column is nan
    df = df.dropna(subset=['thinkingmode_mean', 'newseval_mean'])
    
    # Sort columns with priority columns first
    df = sort_columns_priority(df)

    return df

if __name__ == "__main__":
    """
    Main execution block to load, clean, and save all dataframes.
    """
    import pandas as pd
    import os
    
    # Load the raw CSV files
    data_dir = "data_analysis/data/"
    
    # List of CSV files to process
    csv_files = [
        "Apollolytics-DialogueBotCriticalPre.csv",
        "Apollolytics-DialogueBotConfirmativePre.csv", 
        "Apollolytics-DialogueControlPre.csv",
        "Apollolytics-DialogueStaticPre.csv",
        "Apollolytics-DialogueWithout.csv"
    ]
    
    print("Loading and cleaning data...")
    
    for csv_file in csv_files:
        file_path = os.path.join(data_dir, csv_file)
        if os.path.exists(file_path):
            print(f"\nProcessing: {csv_file}")
            
            # Load the raw data
            df = pd.read_csv(file_path)
            print(f"Original shape: {df.shape}")
            
            # Determine which cleaning function to use based on filename
            if "Dialogue" in csv_file and ("BotCritical" in csv_file or "BotConfirmative" in csv_file):
                # Dialogue conditions
                cleaned_df = clean_dialogue(df)
                print(f"Cleaned shape: {cleaned_df.shape}")
                
                # Save cleaned data
                output_filename = csv_file.replace(".csv", "_clean.csv")
                output_path = os.path.join(data_dir, output_filename)
                cleaned_df.to_csv(output_path, index=False)
                print(f"Saved cleaned data to: {output_path}")
                
            elif "Static" in csv_file or "Control" in csv_file or "Without" in csv_file:
                # Static, control, and without pre conditions
                cleaned_df = clean_static_and_control(df)
                print(f"Cleaned shape: {cleaned_df.shape}")
                
                # Save cleaned data
                output_filename = csv_file.replace(".csv", "_clean.csv")
                output_path = os.path.join(data_dir, output_filename)
                cleaned_df.to_csv(output_path, index=False)
                print(f"Saved cleaned data to: {output_path}")
                
        else:
            print(f"Warning: File not found: {file_path}")
    
    print("\nData cleaning and saving completed!")