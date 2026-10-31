from pydantic import ConfigDict, Field
from eduhub_shared.models.common import ContractModel

class AudienceFilters(ContractModel):
    """
    Restrict the simulated audience. Empty lists mean no restriction.
    """
    # One schema for requests and responses (it is also inside AnalysisReport.context), so the OpenAPI name stays
    # "AudienceFilters" instead of splitting into AudienceFilters-Input / -Output.
    model_config = ConfigDict(json_schema_serialization_defaults_required=False)
    age_groups: list[str] = Field(default_factory=list)
    genders: list[str] = Field(default_factory=list)
    provinces: list[str] = Field(default_factory=list)
