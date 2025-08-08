from rapidfuzz import process, fuzz

def correct_input(input_value, valid_list, threshold=70):
    """
    General-purpose fuzzy string matching function to correct input based on a list of valid values.

    Parameters:
    - input_value (str): The input string to be checked.
    - valid_list (list): List of valid strings to match against.
    - threshold (int): Similarity threshold (0-100). Lower means more lenient.

    Returns:
    - str: Best match from the list, or None if no match meets threshold.
    """
    if not input_value or not valid_list:
        return None

    match = process.extractOne(input_value, valid_list, scorer=fuzz.ratio)
    if match and match[1] >= threshold:
        return match[0]
    return None

def correct_district_name(input_name):
    districts = ['Manhattan', 'Brooklyn', 'Queens', 'Bronx', 'Staten Island']
    return correct_input(input_name, districts)

def correct_crop_name(input_name):
    crops = ['Wheat', 'Rice', 'Maize', 'Soybean', 'Barley', 'Cotton']
    return correct_input(input_name, crops)