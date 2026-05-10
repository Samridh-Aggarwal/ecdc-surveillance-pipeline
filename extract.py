import requests
import time
import os
import pandas as pd
from huggingface_hub import HfApi, login

login(token=os.environ["HF_TOKEN"])

BASE = "https://atlas.ecdc.europa.eu/public/AtlasService/rest"
HEADERS = {"Accept": "application/json"}

diseases = {
    "Campylobacteriosis": 9, "CCHF": 10, "Chikungunya": 11, "Cryptosporidiosis": 15,
    "Dengue": 16, "Giardiasis": 20, "Hantavirus": 24, "Hepatitis A": 25,
    "Legionnaires' disease": 30, "Leptospirosis": 31, "Listeriosis": 33, "Malaria": 34,
    "Rift Valley fever": 44, "Salmonellosis": 46, "Shigellosis": 48, "TBE": 56,
    "STEC/VTEC": 59, "West Nile": 60, "Zika": 70, "Lyme": 76,
}

countries = {
    "Austria": "AT", "Belgium": "BE", "Bulgaria": "BG", "Croatia": "HR", "Cyprus": "CY",
    "Czechia": "CZ", "Denmark": "DK", "Estonia": "EE", "Finland": "FI", "France": "FR",
    "Germany": "DE", "Greece": "EL", "Hungary": "HU", "Ireland": "IE", "Italy": "IT",
    "Latvia": "LV", "Lithuania": "LT", "Luxembourg": "LU", "Malta": "MT", "Netherlands": "NL",
    "Poland": "PL", "Portugal": "PT", "Romania": "RO", "Slovakia": "SK", "Slovenia": "SI",
    "Spain": "ES", "Sweden": "SE", "Iceland": "IS", "Norway": "NO",
}

years = ["2018", "2019", "2020", "2021", "2022", "2023"]

metadata = {
    "Campylobacteriosis":    {"group": "1",  "dark_figure": "Very high",    "eu_mandatory": "Yes",  "coverage": "High"},
    "Cryptosporidiosis":     {"group": "1",  "dark_figure": "Very high",    "eu_mandatory": "Yes",  "coverage": "Medium"},
    "STEC/VTEC":             {"group": "1",  "dark_figure": "High",         "eu_mandatory": "Yes",  "coverage": "Medium-High"},
    "Giardiasis":            {"group": "1",  "dark_figure": "Very high",    "eu_mandatory": "Yes",  "coverage": "Medium"},
    "Hepatitis A":           {"group": "1",  "dark_figure": "Medium-High",  "eu_mandatory": "Yes",  "coverage": "High"},
    "Listeriosis":           {"group": "1",  "dark_figure": "Low-Medium",   "eu_mandatory": "Yes",  "coverage": "High"},
    "Salmonellosis":         {"group": "1",  "dark_figure": "High",         "eu_mandatory": "Yes",  "coverage": "High"},
    "Shigellosis":           {"group": "1",  "dark_figure": "High",         "eu_mandatory": "Yes",  "coverage": "High"},
    "Norovirus":             {"group": "1",  "dark_figure": None,           "eu_mandatory": "No",   "coverage": None},
    "Chikungunya":           {"group": "2a", "dark_figure": "Low",          "eu_mandatory": "Yes",  "coverage": "High"},
    "Dengue":                {"group": "2a", "dark_figure": "Low-Medium",   "eu_mandatory": "Yes",  "coverage": "High"},
    "Malaria":               {"group": "2a", "dark_figure": "Low",          "eu_mandatory": "Yes",  "coverage": "High"},
    "West Nile":             {"group": "2a", "dark_figure": "Medium",       "eu_mandatory": "Yes",  "coverage": "High"},
    "Zika":                  {"group": "2a", "dark_figure": "Low-Medium",   "eu_mandatory": "Yes",  "coverage": "High"},
    "CCHF":                  {"group": "2a", "dark_figure": "Medium",       "eu_mandatory": "Yes",  "coverage": "Low"},
    "Legionnaires' disease": {"group": "2a", "dark_figure": "High",         "eu_mandatory": "Yes",  "coverage": "Medium-High"},
    "Leptospirosis":         {"group": "2a", "dark_figure": "High",         "eu_mandatory": "Yes",  "coverage": "Medium"},
    "Hantavirus":            {"group": "2a", "dark_figure": "High",         "eu_mandatory": "Yes",  "coverage": "Medium"},
    "TBE":                   {"group": "2b", "dark_figure": "Medium-High",  "eu_mandatory": "Yes",  "coverage": "Medium"},
    "Lyme":                  {"group": "2b", "dark_figure": "Very high",    "eu_mandatory": "No",   "coverage": "Low"},
    "Leishmaniasis":         {"group": "2c", "dark_figure": None,           "eu_mandatory": "No",   "coverage": None},
    "Usutu":                 {"group": "2c", "dark_figure": None,           "eu_mandatory": "No",   "coverage": None},
    "Vibriosis":             {"group": "2c", "dark_figure": None,           "eu_mandatory": "No",   "coverage": None},
    "Rift Valley fever":     {"group": "2c", "dark_figure": None,           "eu_mandatory": "No",   "coverage": None},
}


def get_measures(topic_id):
    r = requests.get(
        f"{BASE}/GetIndicatorMeasuresForHealthTopicAndDataset",
        params={"datasetId": 27, "healthTopicId": topic_id},
        headers=HEADERS, timeout=30,
    )
    return r.json().get("Measures") or []


def find_measure(topic_id, keywords):
    measures = get_measures(topic_id)
    for m in measures:
        label = m["Label"].lower()
        if any(kw in label for kw in keywords):
            return m["Id"]
    if measures and "cases" in keywords[0]:
        return measures[0]["Id"]
    return None


def extract():
    # find case and death measure IDs
    case_ids = {}
    death_ids = {}
    for name, topic in diseases.items():
        case_ids[name] = find_measure(topic, ["reported cases", "number of cases"])
        death_ids[name] = find_measure(topic, ["death", "fatal", "lethal", "mortality"])
        print(f"{name:25s} cases={case_ids[name]}  deaths={death_ids[name]}")
        time.sleep(0.2)

    # pull case data
    case_rows = []
    total = len(diseases) * len(countries) * len(years)
    done = 0
    for name, mid in case_ids.items():
        if mid is None:
            continue
        for cname, ccode in countries.items():
            for y in years:
                r = requests.get(
                    f"{BASE}/GetMeasureResultsForTimePeriodAndGeoRegion",
                    params={"measureId": mid, "timeCodes": y,
                            "startTimeCode": "", "endTimeCodeExcl": "", "geoCode": ccode},
                    headers=HEADERS, timeout=30,
                )
                try:
                    res = r.json().get("MeasureResults") or []
                    if res and res[0].get("N") is not None:
                        case_rows.append({"disease": name, "country": cname,
                                          "country_code": ccode, "year": y, "cases": res[0]["N"]})
                except:
                    pass
                done += 1
                if done % 200 == 0:
                    print(f"cases: {done}/{total}")
                time.sleep(0.15)

    df_cases = pd.DataFrame(case_rows)
    print(f"cases: {len(df_cases)} rows")

    # pull death data
    death_rows = []
    death_diseases = {k: v for k, v in death_ids.items() if v is not None}
    total = len(death_diseases) * len(countries) * len(years)
    done = 0
    for name, mid in death_diseases.items():
        for cname, ccode in countries.items():
            for y in years:
                r = requests.get(
                    f"{BASE}/GetMeasureResultsForTimePeriodAndGeoRegion",
                    params={"measureId": mid, "timeCodes": y,
                            "startTimeCode": "", "endTimeCodeExcl": "", "geoCode": ccode},
                    headers=HEADERS, timeout=30,
                )
                try:
                    res = r.json().get("MeasureResults") or []
                    if res and res[0].get("YValue") is not None:
                        death_rows.append({"disease": name, "country": cname,
                                           "country_code": ccode, "year": y,
                                           "deaths": int(res[0]["YValue"])})
                except:
                    pass
                done += 1
                if done % 200 == 0:
                    print(f"deaths: {done}/{total}")
                time.sleep(0.15)

    df_deaths = pd.DataFrame(death_rows)
    print(f"deaths: {len(df_deaths)} rows")

    # merge
    df_cases["year"] = df_cases["year"].astype(str)
    if len(df_deaths) > 0:
        df_deaths["year"] = df_deaths["year"].astype(str)
        df = df_cases.merge(df_deaths, on=["disease", "country", "country_code", "year"], how="left")
    else:
        df = df_cases
        df["deaths"] = None

    # add metadata
    df["group"] = df["disease"].map(lambda d: metadata.get(d, {}).get("group"))
    df["dark_figure"] = df["disease"].map(lambda d: metadata.get(d, {}).get("dark_figure"))
    df["eu_mandatory"] = df["disease"].map(lambda d: metadata.get(d, {}).get("eu_mandatory"))
    df["coverage"] = df["disease"].map(lambda d: metadata.get(d, {}).get("coverage"))

    # save and push
    df.to_csv("ecdc_cases.csv", index=False)
    print(f"final: {len(df)} rows, {df['disease'].nunique()} diseases, {df['country'].nunique()} countries")

    api = HfApi()
    api.upload_file(
        path_or_fileobj="ecdc_cases.csv",
        path_in_repo="ecdc_cases.csv",
        repo_id="SamridhAggarwal/ecdc-surveillance",
        repo_type="dataset",
        commit_message=f"monthly refresh {pd.Timestamp.now().strftime('%Y-%m-%d')}",
    )
    print("pushed to HuggingFace")


if __name__ == "__main__":
    extract()
