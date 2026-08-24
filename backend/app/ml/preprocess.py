from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Dict, Iterable, List

import pandas as pd


# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

PROJECT_ROOT = Path(__file__).resolve().parents[2]

RAW_DATA_DIR = PROJECT_ROOT / "data" / "raw"
PROCESSED_DATA_DIR = PROJECT_ROOT / "data" / "processed"

OUTPUT_FILE = PROCESSED_DATA_DIR / "occupation_profiles.json"

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s",
)

logger = logging.getLogger(__name__)


FILES = {
    "occupation": "Occupation Data.xlsx",
    "knowledge": "Knowledge.xlsx",
    "abilities": "Abilities.xlsx",
    "interests": "Career Interest Types.xlsx",
    "specific_interests": "Specific Interest Areas.xlsx",
    "interest_keywords": "Career Interest Type Keywords.xlsx",
    "transferable_skills": "Transferable Skills.xlsx",
    "essential_skills": "Essential Skills.xlsx",
    "software_skills": "Software Skills.xlsx",
}


# ---------------------------------------------------------------------------
# Required columns
# ---------------------------------------------------------------------------

REQUIRED_COLUMNS = {
    "occupation": {
        "O*NET-SOC Code",
        "Title",
        "Description",
    },
    "knowledge": {
        "O*NET-SOC Code",
        "Title",
        "Element Name",
        "Scale ID",
        "Scale Name",
        "Data Value",
    },
    "abilities": {
        "O*NET-SOC Code",
        "Title",
        "Element Name",
        "Scale ID",
        "Scale Name",
        "Data Value",
    },
    "interests": {
        "O*NET-SOC Code",
        "Title",
        "Element Name",
        "Scale ID",
        "Scale Name",
        "Data Value",
    },
    "specific_interests": {
        "O*NET-SOC Code",
        "Title",
        "Element Name",
        "Scale ID",
        "Scale Name",
        "Data Value",
    },
    "interest_keywords": {
        "Element ID",
        "Element Name",
        "Keyword",
        "Keyword Type",
    },
    "transferable_skills": {
        "O*NET-SOC Code",
        "Title",
        "Element Name",
        "Scale ID",
        "Scale Name",
        "Data Value",
    },
    "essential_skills": {
        "O*NET-SOC Code",
        "Title",
        "Element Name",
        "Scale ID",
        "Scale Name",
        "Data Value",
    },
    "software_skills": {
        "O*NET-SOC Code",
        "Title",
        "Workplace Example",
        "Element ID",
        "Element Name",
        "Hot Technology",
        "In Demand",
    },
}


# ---------------------------------------------------------------------------
# Utility functions
# ---------------------------------------------------------------------------

def normalize_text(value) -> str:
    """
    Convert a value into clean text.

    NaN / None values become an empty string.
    """
    if pd.isna(value):
        return ""

    return " ".join(str(value).strip().split())


def normalize_soc(value) -> str:
    """
    Normalize O*NET-SOC codes so they can safely be used as dictionary keys.
    """
    return normalize_text(value)


def unique_strings(values: Iterable[str]) -> List[str]:
    """
    Remove empty values and duplicates while preserving order.
    """
    result = []
    seen = set()

    for value in values:
        value = normalize_text(value)

        if not value:
            continue

        key = value.lower()

        if key not in seen:
            seen.add(key)
            result.append(value)

    return result


def safe_float(value):
    """
    Convert a value to float when possible.
    """
    try:
        if pd.isna(value):
            return None

        return float(value)

    except (TypeError, ValueError):
        return None


# ---------------------------------------------------------------------------
# File loading and validation
# ---------------------------------------------------------------------------

def get_file_path(file_name: str) -> Path:
    """
    Return the path of an input Excel file.
    """
    path = RAW_DATA_DIR / file_name

    if not path.exists():
        raise FileNotFoundError(
            f"Required dataset not found: {path}"
        )

    return path


def load_excel(dataset_name: str) -> pd.DataFrame:
    """
    Load an Excel dataset and validate its required columns.
    """
    if dataset_name not in FILES:
        raise ValueError(f"Unknown dataset: {dataset_name}")

    file_name = FILES[dataset_name]
    path = get_file_path(file_name)

    logger.info("Loading %s", file_name)

    df = pd.read_excel(path)

    expected_columns = REQUIRED_COLUMNS[dataset_name]
    actual_columns = set(df.columns)

    missing_columns = expected_columns - actual_columns

    if missing_columns:
        raise ValueError(
            f"{file_name} is missing required columns: "
            f"{sorted(missing_columns)}"
        )

    logger.info(
        "Loaded %s rows from %s",
        len(df),
        file_name,
    )

    return df


# ---------------------------------------------------------------------------
# Occupation base data
# ---------------------------------------------------------------------------

def build_occupation_profiles(
    occupation_df: pd.DataFrame,
) -> Dict[str, dict]:
    """
    Create the base occupation profile from Occupation Data.xlsx.
    """
    profiles: Dict[str, dict] = {}

    for _, row in occupation_df.iterrows():

        soc_code = normalize_soc(row["O*NET-SOC Code"])

        if not soc_code:
            continue

        profiles[soc_code] = {
            "onet_soc_code": soc_code,
            "title": normalize_text(row["Title"]),
            "description": normalize_text(row["Description"]),
            "knowledge": [],
            "abilities": [],
            "transferable_skills": [],
            "essential_skills": [],
            "software_skills": [],
            "hot_technologies": [],
            "in_demand_software": [],
            "specific_interests": [],
            "riasec": {
                "Realistic": None,
                "Investigative": None,
                "Artistic": None,
                "Social": None,
                "Enterprising": None,
                "Conventional": None,
            },
        }

    logger.info(
        "Created %d base occupation profiles",
        len(profiles),
    )

    return profiles


# ---------------------------------------------------------------------------
# Generic O*NET element processing
# ---------------------------------------------------------------------------

def add_weighted_elements(
    profiles: Dict[str, dict],
    df: pd.DataFrame,
    output_field: str,
    importance_only: bool = True,
) -> None:
    """
    Add O*NET elements such as Knowledge, Abilities, Essential Skills,
    and Transferable Skills to occupation profiles.

    O*NET provides multiple scales for many datasets.

    We prioritize:
        IM = Importance

    When importance_only=True, only importance rows are retained.
    """
    required_fields = {
        "O*NET-SOC Code",
        "Element Name",
        "Scale ID",
        "Scale Name",
        "Data Value",
    }

    missing = required_fields - set(df.columns)

    if missing:
        raise ValueError(
            f"Dataset for '{output_field}' is missing columns: "
            f"{sorted(missing)}"
        )

    for _, row in df.iterrows():

        soc_code = normalize_soc(row["O*NET-SOC Code"])

        if soc_code not in profiles:
            continue

        scale_id = normalize_text(row["Scale ID"])

        if importance_only and scale_id != "IM":
            continue

        element_name = normalize_text(row["Element Name"])

        if not element_name:
            continue

        data_value = safe_float(row["Data Value"])

        item = {
            "name": element_name,
            "importance": data_value,
        }

        profiles[soc_code][output_field].append(item)


# ---------------------------------------------------------------------------
# RIASEC processing
# ---------------------------------------------------------------------------

RIASEC_TYPES = (
    "Realistic",
    "Investigative",
    "Artistic",
    "Social",
    "Enterprising",
    "Conventional",
)


def add_riasec_profiles(
    profiles: Dict[str, dict],
    interests_df: pd.DataFrame,
) -> None:
    """
    Extract the six O*NET occupational interest dimensions.

    The uploaded dataset uses:
        Scale ID = OI
        Scale Name = Occupational Interests

    The dataset also contains:
        IH = Occupational Interest High-Point

    For the recommendation engine we retain the six OI values.
    """
    for _, row in interests_df.iterrows():

        soc_code = normalize_soc(row["O*NET-SOC Code"])

        if soc_code not in profiles:
            continue

        scale_id = normalize_text(row["Scale ID"])

        if scale_id != "OI":
            continue

        element_name = normalize_text(row["Element Name"])

        if element_name not in RIASEC_TYPES:
            continue

        data_value = safe_float(row["Data Value"])

        profiles[soc_code]["riasec"][element_name] = data_value


# ---------------------------------------------------------------------------
# Specific interest areas
# ---------------------------------------------------------------------------

def add_specific_interests(
    profiles: Dict[str, dict],
    df: pd.DataFrame,
) -> None:
    """
    Add detailed occupational interest areas.

    Only OI rows are retained because DS represents display rank,
    while OI represents the occupational interest value.
    """
    for _, row in df.iterrows():

        soc_code = normalize_soc(row["O*NET-SOC Code"])

        if soc_code not in profiles:
            continue

        scale_id = normalize_text(row["Scale ID"])

        if scale_id != "OI":
            continue

        element_name = normalize_text(row["Element Name"])

        if not element_name:
            continue

        data_value = safe_float(row["Data Value"])

        profiles[soc_code]["specific_interests"].append(
            {
                "name": element_name,
                "value": data_value,
            }
        )


# ---------------------------------------------------------------------------
# Software skills
# ---------------------------------------------------------------------------

def add_software_skills(
    profiles: Dict[str, dict],
    df: pd.DataFrame,
) -> None:
    """
    Add software/tool information from Software Skills.xlsx.

    The uploaded file does not contain a numeric importance value.
    Therefore we retain:
        - workplace example
        - software category
        - hot technology flag
        - in-demand flag
    """
    for _, row in df.iterrows():

        soc_code = normalize_soc(row["O*NET-SOC Code"])

        if soc_code not in profiles:
            continue

        software = normalize_text(row["Workplace Example"])
        category = normalize_text(row["Element Name"])

        if not software:
            continue

        hot_technology = (
            normalize_text(row["Hot Technology"]).upper() == "Y"
        )

        in_demand = (
            normalize_text(row["In Demand"]).upper() == "Y"
        )

        item = {
            "name": software,
            "category": category,
            "hot_technology": hot_technology,
            "in_demand": in_demand,
        }

        profiles[soc_code]["software_skills"].append(item)

        if hot_technology:
            profiles[soc_code]["hot_technologies"].append(software)

        if in_demand:
            profiles[soc_code]["in_demand_software"].append(software)


# ---------------------------------------------------------------------------
# Interest keywords
# ---------------------------------------------------------------------------

def build_interest_keywords(
    df: pd.DataFrame,
) -> Dict[str, List[str]]:
    """
    Build a RIASEC type -> keyword mapping.

    Example:
        Realistic -> ["Build", "Drive", "Install", ...]
    """
    keywords: Dict[str, List[str]] = {
        interest_type: []
        for interest_type in RIASEC_TYPES
    }

    for _, row in df.iterrows():

        element_name = normalize_text(row["Element Name"])
        keyword = normalize_text(row["Keyword"])

        if (
            element_name in keywords
            and keyword
        ):
            keywords[element_name].append(keyword)

    for interest_type in keywords:
        keywords[interest_type] = unique_strings(
            keywords[interest_type]
        )

    return keywords


# ---------------------------------------------------------------------------
# Deduplication
# ---------------------------------------------------------------------------

def clean_profile_lists(
    profiles: Dict[str, dict],
) -> None:
    """
    Remove duplicate entries from list-based occupation fields.
    """
    for profile in profiles.values():

        for field in (
            "knowledge",
            "abilities",
            "transferable_skills",
            "essential_skills",
            "specific_interests",
        ):
            seen = set()
            cleaned = []

            for item in profile[field]:

                name = normalize_text(item.get("name"))

                if not name:
                    continue

                key = (
                    name.lower(),
                    item.get("importance")
                    if "importance" in item
                    else item.get("value"),
                )

                if key in seen:
                    continue

                seen.add(key)
                cleaned.append(item)

            profile[field] = cleaned

        for field in (
            "software_skills",
            "hot_technologies",
            "in_demand_software",
        ):
            if field in profile:
                if field == "software_skills":
                    seen = set()
                    cleaned = []

                    for item in profile[field]:
                        key = item["name"].lower()

                        if key in seen:
                            continue

                        seen.add(key)
                        cleaned.append(item)

                    profile[field] = cleaned

                else:
                    profile[field] = unique_strings(
                        profile[field]
                    )


# ---------------------------------------------------------------------------
# Searchable text
# ---------------------------------------------------------------------------

def build_search_text(profile: dict) -> str:
    """
    Build the text representation that train.py will later vectorize.

    The representation intentionally includes:
        occupation title
        description
        knowledge
        abilities
        transferable skills
        essential skills
        software
        specific interests

    RIASEC numeric values are NOT converted into text here.
    They are preserved separately for the hybrid recommendation score.
    """
    parts: List[str] = []

    parts.append(profile["title"])
    parts.append(profile["description"])

    for field in (
        "knowledge",
        "abilities",
        "transferable_skills",
        "essential_skills",
    ):
        for item in profile[field]:
            name = item.get("name")

            if name:
                parts.append(name)

    for item in profile["software_skills"]:
        software_name = item.get("name")
        category = item.get("category")

        if software_name:
            parts.append(software_name)

        if category:
            parts.append(category)

    for item in profile["specific_interests"]:
        name = item.get("name")

        if name:
            parts.append(name)

    return " ".join(
        unique_strings(parts)
    )


# ---------------------------------------------------------------------------
# Main preprocessing pipeline
# ---------------------------------------------------------------------------

def preprocess() -> Path:
    """
    Execute the complete Phase 1 preprocessing pipeline.
    """
    logger.info("Starting O*NET preprocessing")

    PROCESSED_DATA_DIR.mkdir(
        parents=True,
        exist_ok=True,
    )

    # ---------------------------------------------------------------
    # 1. Load datasets
    # ---------------------------------------------------------------

    occupation_df = load_excel("occupation")
    knowledge_df = load_excel("knowledge")
    abilities_df = load_excel("abilities")
    interests_df = load_excel("interests")
    specific_interests_df = load_excel("specific_interests")
    interest_keywords_df = load_excel("interest_keywords")
    transferable_skills_df = load_excel("transferable_skills")
    essential_skills_df = load_excel("essential_skills")
    software_skills_df = load_excel("software_skills")

    # ---------------------------------------------------------------
    # 2. Create base occupation profiles
    # ---------------------------------------------------------------

    profiles = build_occupation_profiles(
        occupation_df
    )

    # ---------------------------------------------------------------
    # 3. Add occupational knowledge
    # ---------------------------------------------------------------

    add_weighted_elements(
        profiles,
        knowledge_df,
        "knowledge",
    )

    # ---------------------------------------------------------------
    # 4. Add abilities
    # ---------------------------------------------------------------

    add_weighted_elements(
        profiles,
        abilities_df,
        "abilities",
    )

    # ---------------------------------------------------------------
    # 5. Add transferable skills
    # ---------------------------------------------------------------

    add_weighted_elements(
        profiles,
        transferable_skills_df,
        "transferable_skills",
    )

    # ---------------------------------------------------------------
    # 6. Add essential skills
    # ---------------------------------------------------------------

    add_weighted_elements(
        profiles,
        essential_skills_df,
        "essential_skills",
    )

    # ---------------------------------------------------------------
    # 7. Add RIASEC occupational interests
    # ---------------------------------------------------------------

    add_riasec_profiles(
        profiles,
        interests_df,
    )

    # ---------------------------------------------------------------
    # 8. Add specific interest areas
    # ---------------------------------------------------------------

    add_specific_interests(
        profiles,
        specific_interests_df,
    )

    # ---------------------------------------------------------------
    # 9. Add software skills
    # ---------------------------------------------------------------

    add_software_skills(
        profiles,
        software_skills_df,
    )

    # ---------------------------------------------------------------
    # 10. Build RIASEC keyword dictionary
    # ---------------------------------------------------------------

    interest_keywords = build_interest_keywords(
        interest_keywords_df
    )

    # ---------------------------------------------------------------
    # 11. Clean duplicate entries
    # ---------------------------------------------------------------

    clean_profile_lists(profiles)

    # ---------------------------------------------------------------
    # 12. Build searchable occupation text
    # ---------------------------------------------------------------

    for profile in profiles.values():
        profile["search_text"] = build_search_text(
            profile
        )

    # ---------------------------------------------------------------
    # 13. Final validation
    # ---------------------------------------------------------------

    valid_profiles = {}

    for soc_code, profile in profiles.items():

        if not profile["title"]:
            logger.warning(
                "Skipping occupation %s because title is empty",
                soc_code,
            )
            continue

        if not profile["search_text"]:
            logger.warning(
                "Skipping occupation %s because search text is empty",
                soc_code,
            )
            continue

        valid_profiles[soc_code] = profile

    # ---------------------------------------------------------------
    # 14. Create final output
    # ---------------------------------------------------------------

    output = {
        "metadata": {
            "source": "O*NET datasets",
            "occupation_count": len(valid_profiles),
            "riasec_types": list(RIASEC_TYPES),
            "description": (
                "Preprocessed occupation profiles for the "
                "AI-based career recommendation system."
            ),
        },
        "interest_keywords": interest_keywords,
        "occupations": valid_profiles,
    }

    with open(
        OUTPUT_FILE,
        "w",
        encoding="utf-8",
    ) as file:
        json.dump(
            output,
            file,
            ensure_ascii=False,
            indent=2,
        )

    logger.info(
        "Preprocessing completed successfully"
    )

    logger.info(
        "Processed occupations: %d",
        len(valid_profiles),
    )

    logger.info(
        "Output written to: %s",
        OUTPUT_FILE,
    )

    return OUTPUT_FILE


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    try:
        output_path = preprocess()

        print()
        print("Phase 1 preprocessing completed.")
        print(f"Output: {output_path}")

    except Exception as exc:
        logger.exception(
            "Preprocessing failed: %s",
            exc,
        )
        raise