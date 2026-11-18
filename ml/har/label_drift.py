"""Figure: annotated instances per month for selected activities (label drift).

    python -m har.label_drift      # -> results/label_drift.png, results/label_drift.csv
"""

from __future__ import annotations

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import pandas as pd  # noqa: E402

from .data import load_home  # noqa: E402
from .run import RESULTS_DIR  # noqa: E402

SHOW = {"aruba": ["Meal_Preparation", "Eating", "Wash_Dishes", "Housekeeping"],
        "milan": ["Kitchen_Activity", "Morning_Meds", "Eve_Meds", "Chores"]}


def main():
    fig, axes = plt.subplots(1, 2, figsize=(11, 3.8))
    rows = []
    for ax, home in zip(axes, SHOW):
        seg = load_home(home).segments
        month = seg["start"].dt.to_period("M")
        tab = pd.crosstab(month, seg["activity"])[SHOW[home]]
        for act in SHOW[home]:
            ax.plot(tab.index.astype(str), tab[act], "o-", label=act.replace("_", " "))
            rows += [{"home": home, "month": str(m), "activity": act, "count": int(c)}
                     for m, c in tab[act].items()]
        ax.set_title(home.capitalize())
        ax.set_ylabel("Annotated instances per month")
        ax.set_yscale("symlog", linthresh=10)
        ax.tick_params(axis="x", rotation=45)
        ax.grid(alpha=0.3)
        ax.legend(fontsize=8)
    fig.tight_layout()
    fig.savefig(RESULTS_DIR / "label_drift.png", dpi=150)
    pd.DataFrame(rows).to_csv(RESULTS_DIR / "label_drift.csv", index=False)
    print("wrote", RESULTS_DIR / "label_drift.png")


if __name__ == "__main__":
    main()
