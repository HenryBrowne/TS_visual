FREQ_TO_PANDAS = {
    "Yearly": "YS",
    "Quarterly": "QS",
    "Monthly": "MS",
    "Weekly": "W",
    "Daily": "D",
    "Hourly": "h",
}

# pandas' infer_freq returns aliases with anchor suffixes (e.g. "W-SUN",
# "Q-DEC") and both old- and new-style bases (e.g. "M" vs "MS"), so this
# maps the *base* alias back to one of our labels.
_PANDAS_BASE_TO_FREQ_LABEL = {
    "D": "Daily",
    "W": "Weekly",
    "M": "Monthly",
    "MS": "Monthly",
    "Q": "Quarterly",
    "QS": "Quarterly",
    "A": "Yearly",
    "AS": "Yearly",
    "Y": "Yearly",
    "YS": "Yearly",
    "H": "Hourly",
    "h": "Hourly",
}

DEFAULT_FREQ_LABEL = "Daily"


def infer_frequency_label(inferred_alias: str | None) -> str:
    """Maps a pandas-inferred frequency alias (from pd.infer_freq) to one
    of our known frequency labels, falling back to Daily when inference
    fails or returns something we don't recognize -- a reasonable v1
    default, not a claim that the data actually is daily.
    """
    if not inferred_alias:
        return DEFAULT_FREQ_LABEL
    base = inferred_alias.split("-")[0]
    return _PANDAS_BASE_TO_FREQ_LABEL.get(base, DEFAULT_FREQ_LABEL)
