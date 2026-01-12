import ngio
import pandas as pd
from ngio.tables import ConditionTable

plate_url = ""

poor_registration = [
    {"well": "B05", "FOV": "FOV_7", "reason": "sample detachment"},
    {"well": "B05", "FOV": "FOV_8", "reason": "sample detachment"},
    {"well": "B05", "FOV": "FOV_16", "reason": "sample detachment"},
    {"well": "B09", "FOV": "FOV_26", "reason": "sample detachment"},
    {"well": "B09", "FOV": "FOV_39", "reason": "sample detachment"},
    {"well": "B09", "FOV": "FOV_40", "reason": "sample detachment"},
    {"well": "B09", "FOV": "FOV_47", "reason": "sample detachment"},
    {"well": "B09", "FOV": "FOV_48", "reason": "sample detachment"},
    {"well": "B09", "FOV": "FOV_53", "reason": "sample detachment"},
    {"well": "B09", "FOV": "FOV_54", "reason": "sample detachment"},
    {"well": "B09", "FOV": "FOV_55", "reason": "sample detachment"},
    {"well": "B09", "FOV": "FOV_56", "reason": "sample detachment"},
    {"well": "B09", "FOV": "FOV_61", "reason": "sample detachment"},
    {"well": "B09", "FOV": "FOV_62", "reason": "sample detachment"},
    {"well": "B09", "FOV": "FOV_63", "reason": "sample detachment"},
    {"well": "B09", "FOV": "FOV_64", "reason": "sample detachment"},
    {"well": "B09", "FOV": "FOV_68", "reason": "sample detachment"},
    {"well": "B09", "FOV": "FOV_69", "reason": "sample detachment"},
    {"well": "B09", "FOV": "FOV_70", "reason": "sample detachment"},
    {"well": "B09", "FOV": "FOV_71", "reason": "sample detachment"},
    {"well": "B09", "FOV": "FOV_72", "reason": "sample detachment"},
    {"well": "C08", "FOV": "FOV_72", "reason": "sample detachment"},
    {"well": "D09", "FOV": "FOV_68", "reason": "sample detachment"},
    {"well": "D09", "FOV": "FOV_69", "reason": "sample detachment"},
    {"well": "E04", "FOV": "FOV_72", "reason": "sample detachment"},
    {"well": "E08", "FOV": "FOV_20", "reason": "sample detachment"},
    {"well": "E08", "FOV": "FOV_67", "reason": "sample detachment"},
    {"well": "F11", "FOV": "FOV_71", "reason": "sample detachment"},
    {"well": "G04", "FOV": "FOV_7", "reason": "sample detachment"},
    {"well": "G04", "FOV": "FOV_8", "reason": "sample detachment"},
    {"well": "G04", "FOV": "FOV_15", "reason": "sample detachment"},
    {"well": "G04", "FOV": "FOV_16", "reason": "sample detachment"},
    {"well": "G04", "FOV": "FOV_23", "reason": "sample detachment"},
]
df = pd.DataFrame(poor_registration)
df["row"] = df["well"].str[0]
df["column"] = df["well"].str[1:]

condition_table = ConditionTable(df)
plate_container = ngio.open_ome_zarr_plate(plate_url)
plate_container.add_table(
    name="registration_errors",
    table=condition_table,
    backend="csv",
    overwrite=True,
)
