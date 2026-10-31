import re
from typing import Annotated
from pydantic import AfterValidator, BaseModel, ConfigDict

HANDLE_PATTERN = re.compile(r"^[a-z0-9_.]{1,30}$")

class ContractModel(BaseModel):
    """
    Base class for every contract model: unknown fields are rejected so drift is caught early.
    """
    model_config = ConfigDict(extra="forbid", json_schema_serialization_defaults_required=True)

def normalize_handle(value: str) -> str:
    """
    Strip a leading "@", trim spaces and lowercase a handle, rejecting invalid characters.
    """
    handle = value.strip().removeprefix("@").lower()
    if not HANDLE_PATTERN.match(handle):
        raise ValueError(f"invalid handle: {value!r}")
    return handle

Handle = Annotated[str, AfterValidator(normalize_handle)]
