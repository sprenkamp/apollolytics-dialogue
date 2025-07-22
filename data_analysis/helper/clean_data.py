import pandas as pd

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

    return df

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

    return df