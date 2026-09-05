from pydantic import BaseModel, Field

# "for" is a Python keyword - aliased to/from the JSON key "for" (matching
# the YAML field name it maps directly onto) via the Python attribute
# `for_`, populate_by_name so the service layer can construct these with
# for_=... directly too.


class AlertRuleCreate(BaseModel):
    model_config = {"populate_by_name": True}

    group: str
    alert: str
    expr: str
    for_: str = Field(default="0s", alias="for")
    severity: str = "warning"  # "warning" or "critical"
    summary: str = ""
    description: str = ""


class AlertRuleUpdate(BaseModel):
    model_config = {"populate_by_name": True}

    expr: str
    for_: str = Field(alias="for")
    severity: str
    summary: str = ""
    description: str = ""
