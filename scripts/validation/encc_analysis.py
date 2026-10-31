"""
Reproduce the ENCC 2022-2023 figures used in docs/validation.md.

Usage: python scripts/validation/encc_analysis.py <path/to/base-datos-encc-2022-2023.csv>
Source: https://datos.cultura.gob.ar/dataset/251c2ac2-e670-451c-9dbf-a4212af225b5
"""
import sys
import pandas as pd

DAILY = "Todos o casi todos los días"
WEEKLY = "Algunas veces a la semana"
PLATFORMS = {
    "int11_1": "YouTube",
    "int11_2": "Instagram",
    "int11_3": "Facebook",
    "int11_4": "TikTok",
    "int11_5": "Twitch",
    "int11_6": "Twitter/X",
    "int11_8": "WhatsApp",
    "int11_10": "LinkedIn",
}

def weighted_share(df: pd.DataFrame, mask: pd.Series) -> float:
    """
    Return the expansion-weighted percentage of rows in df matching mask.
    """
    weights = df["expansor"]
    return 100 * weights[mask].sum() / weights.sum()

def weighted_people(df: pd.DataFrame, mask: pd.Series) -> float:
    """
    Return the expanded number of people (in millions) matching mask.
    """
    return df["expansor"][mask].sum() / 1e6

def report(df: pd.DataFrame) -> None:
    """
    Print the headline indicators, platform usage and age breakdown.
    """
    uploads_weekly = df["int12.1"].isin([DAILY, WEEKLY])
    uploads_daily = df["int12.1"] == DAILY
    watches_daily = df["int12.4"] == DAILY
    uses_x = df["int11_6"] == 1
    print(f"Population 13+ represented: {df['expansor'].sum() / 1e6:.1f}M")
    for label, frame, mask in (
        ("Uploads weekly+", df, uploads_weekly),
        ("Uploads daily", df, uploads_daily),
        ("Watches influencers daily", df, watches_daily),
        ("Uses X", df, uses_x),
    ):
        print(f"{label}: {weighted_share(frame, mask):.1f}% ({weighted_people(frame, mask):.2f}M)")
    x_users = df[uses_x]
    x_uploads = x_users["int12.1"].isin([DAILY, WEEKLY])
    print(f"X users uploading weekly+: {weighted_share(x_users, x_uploads):.1f}% "
          f"({weighted_people(x_users, x_uploads):.2f}M)")
    for column, name in PLATFORMS.items():
        print(f"  {name}: {weighted_share(df, df[column] == 1):.1f}%")
    for group, sub in df.groupby("grupos_edad"):
        weekly = weighted_share(sub, sub["int12.1"].isin([DAILY, WEEKLY]))
        print(f"  {group}: uploads weekly+ {weekly:.1f}% | X {weighted_share(sub, sub['int11_6'] == 1):.1f}%")

def main() -> None:
    """
    Load the ENCC CSV given as first argument and print the report.
    """
    df = pd.read_csv(sys.argv[1], encoding="utf-8-sig", low_memory=False)
    report(df)

if __name__ == "__main__":
    main()
