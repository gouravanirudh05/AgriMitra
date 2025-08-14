import requests
import json
import time
from langchain.tools import tool
API_URL = "https://soilhealth4.dac.gov.in//"  # change to actual endpoint

HEADERS = {
    "Content-Type": "application/json"
}

# -------------------------------
# Helper: Delay
# -------------------------------
def delay(seconds=0.5):
    time.sleep(seconds)

# -------------------------------
# Generic GraphQL POST
# -------------------------------
def gql_request(operation_name, query, variables):
    try:
        payload = {
            "operationName": operation_name,
            "variables": variables,
            "query": query
        }
        response = requests.post(API_URL, headers=HEADERS, json=payload)
        response.raise_for_status()
        return response.json().get("data", None)
    except requests.RequestException as e:
        print(f"Error in {operation_name}: {e}")
        return None

# -------------------------------
# Queries
# -------------------------------
GET_PROGRESS_REPORT = """
query GetProgressReportForPortal($state: ID, $district: ID, $block: ID, $village: ID, $count: Boolean, $cycle: String, $scheme: String) {
  getProgressReportForPortal(
    state: $state
    district: $district
    block: $block
    village: $village
    count: $count
    cycle: $cycle
    scheme: $scheme
  )
}
"""

GET_CROP_REGISTRIES = """
query GetCropRegistries($state: String) {
  getCropRegistries(state: $state) {
    GFRavailable
    id
    combinedName
    __typename
  }
}
"""

GET_RECOMMENDATIONS = """
query GetRecommendations($state: ID!, $results: JSON!, $district: ID, $crops: [ID!]) {
  getRecommendations(
    state: $state
    results: $results
    district: $district
    crops: $crops
  )
}
"""

# -------------------------------
# API Wrappers
# -------------------------------
def get_all_states_id(scheme, cycle):
    return gql_request("GetProgressReportForPortal", GET_PROGRESS_REPORT, {
        "scheme": scheme,
        "cycle": cycle
    })

def get_all_districts_id(state_id, scheme, cycle):
    return gql_request("GetProgressReportForPortal", GET_PROGRESS_REPORT, {
        "state": state_id,
        "scheme": scheme,
        "cycle": cycle
    })

def get_all_crops_id(state_id):
    return gql_request("GetCropRegistries", GET_CROP_REGISTRIES, {
        "state": state_id
    })

def get_recommendation_online(crops, state_id, district_id, results):
    return gql_request("GetRecommendations", GET_RECOMMENDATIONS, {
        "crops": crops,
        "state": state_id,
        "district": district_id,
        "results": results
    })
def dict_to_markdown(data: dict) -> str:
    md_lines = []

    # Assuming data is like: {'getRecommendations': [...]}
    for rec in data.get('getRecommendations', []):
        crop = rec.get('crop', 'Unknown Crop')
        md_lines.append(f"## Crop Recommendation\n")
        md_lines.append(f"### Crop\n**{crop}**\n")

        # Fertilizers Data
        fert_data = rec.get('fertilizersdata', [])
        if fert_data:
            md_lines.append("### Fertilizers Data")
            md_lines.append("| Name | Value | Unit |")
            md_lines.append("|------|-------|------|")
            for fert in fert_data:
                md_lines.append(f"| {fert['name']} | {fert['values']} | {fert['unit']} |")
            md_lines.append("")

        # Fertilizers Data Combination Two
        fert_comb2 = rec.get('fertilizzersdatacombTwo', [])
        if fert_comb2:
            md_lines.append("### Fertilizers Data (Combination Two)")
            md_lines.append("| Name | Value | Unit |")
            md_lines.append("|------|-------|------|")
            for fert in fert_comb2:
                md_lines.append(f"| {fert['name']} | {fert['values']} | {fert['unit']} |")
            md_lines.append("")

        # FYM
        fym = rec.get('fym')
        if fym:
            md_lines.append("### FYM (Farmyard Manure)")
            md_lines.append("| Value | Unit |")
            md_lines.append("|-------|------|")
            md_lines.append(f"| {fym['value']} | {fym['unit']} |")
            md_lines.append("")

    return "\n".join(md_lines)


# Example usage:
# data = {
#     'getRecommendations': [{
#         'crop': 'ಬಾಳೆ (All Variety / Rainfed / Rabi)',
#         'fertilizersdata': [
#             {'name': '15-15-15', 'values': 2905, 'unit': 'Kg per Hectare'}
#         ],
#         'fertilizzersdatacombTwo': [
#             {'name': '10-26-26', 'values': 1675.9615384615383, 'unit': 'Kg per Hectare'}
#         ],
#         'fym': {'value': 13.6, 'unit': 'Tonne per Hectare'}
#     }]
# }

# print(dict_to_markdown(data))

# -------------------------------
# Cache Builder
# -------------------------------
def build_cache(scheme, cycle, output_file="cache.json"):
    print("Fetching all states...")
    states_data = get_all_states_id(scheme, cycle)
    if not states_data:
        print("No states data retrieved.")
        return

    states = states_data.get("getProgressReportForPortal", [])
    print(states)
    cache = []

    for state in states:
        state = state.get("state")
        state_id = state.get("_id")
        state_name = state.get("name")
        print(f"Processing state: {state_name} ({state_id})")

        # Fetch districts
        delay(1)
        districts_data = get_all_districts_id(state_id, scheme, cycle)
        print("District done")
        # print(districts_data)
        districts = [
            {"id": d.get('district').get("_id"), "name": d.get('district').get("name")}
            for d in (districts_data.get("getProgressReportForPortal", []) if districts_data else [])
        ]

        # Fetch crops
        delay(1)
        crops_data = get_all_crops_id(state_id)
        print("Crops done")
        crops = [
            {"id": c.get("id"), "name": c.get("combinedName")}
            for c in (crops_data.get("getCropRegistries", []) if crops_data else [])
        ]

        cache.append({
            "id": state_id,
            "name": state_name,
            "districts": districts,
            "crops": crops
        })
        with open(output_file, "w", encoding="utf-8") as f:
            json.dump(cache, f, indent=2, ensure_ascii=False)
        delay(10)  # longer pause before next state

    # Save to file
    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(cache, f, indent=2, ensure_ascii=False)
    print(f"Cache saved to {output_file}")

# -------------------------------
# Example usage
# -------------------------------

import json
from rapidfuzz import process, fuzz

@tool("get_recommendation")
def get_recommendation(district_name, crop_name, npk_oc):
    """
    Finds state, district, and crop IDs from cache.json using fuzzy search.
    
    Args:
        district_name (str): District name to fuzzy match.
        crop_name (str): Crop name to fuzzy match.
        npk_oc (dict): Dictionary with keys 'n', 'p', 'k', 'OC'.
    
    Returns:
        str: Markdown table of recommendations.
        or None if not found.
    """
    cache_file = "../../datasets/fertilizer/cache.json"
    with open(cache_file, 'r', encoding='utf-8') as f:
        data = json.load(f)

    # Ensure data is iterable (handle both list or single dict formats)
    states = data if isinstance(data, list) else [data]

    # Helper for best fuzzy match
    def best_match(name, items):
        if not items:
            return None
        match_name, score, idx = process.extractOne(
            name,
            [item["name"] for item in items],
            scorer=fuzz.token_sort_ratio
        )
        return items[idx] if score > 60 else None  # score threshold to avoid bad matches

    # Search for matching district → get state
    for state in states:
        district_match = best_match(district_name, state.get("districts", []))
        print(district_match)
        if district_match:
            state_id = state["id"]
            district_id = district_match["id"]

            # Now find matching crop in that state
            crop_match = best_match(crop_name, state.get("crops", []))
            print(crop_match,state_id,district_id)
            if crop_match:
                crop_id = [crop_match["id"]]
                print(crop_id, state_id, district_id, npk_oc)
                return dict_to_markdown(get_recommendation_online(crop_id, state_id, district_id, npk_oc))

    return "Error in fetching recommendation"

# # Example usage:
# npk_oc_values = {"n": "4", "p": "3", "k": "2", "OC": "4"}

# result = get_recommendation(
#     "cache.json",
#     district_name="South Andaman",
#     crop_name="Banana Rainfed",
#     npk_oc=npk_oc_values
# )

# if result:
#     get_recommendation(result["cropid"], result["stateid"], result["districtid"], {
#         "n": result["n"],
#         "p": result["p"],
#         "k": result["k"],
#         "OC": result["OC"]
#     })


if __name__ == "__main__":
    SCHEME = "XXX"
    CYCLE = "2025-26"
    # build_cache(SCHEME, CYCLE)
    response = get_recommendation.invoke(input={"district_name": 'NORTH AND MIDDLE ANDAMAN', "crop_name": "Arecanut (All Variety)", "npk_oc":{'n': 1.0, 'k': 3.0, 'p': 2.0, 'OC': 4.0}})
    # response = get_recommendation("","", )
    # response = get_recommendation_online(["67178c3b70b4612eb9f4ee42"],"63f99fbd519359b7438a84ca","63f9b4b2519359b7438c290c",{"n": "4", "p": "3", "k": "2", "OC": "4"})
    print(response)