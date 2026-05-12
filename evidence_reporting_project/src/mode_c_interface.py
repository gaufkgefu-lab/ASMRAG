from __future__ import annotations

from pydantic import BaseModel, Field


class ModeCFutureInput(BaseModel):
    microorganism_detection_results: dict = Field(default_factory=dict)
    filament_floc_descriptors: dict = Field(default_factory=dict)
    settling_state_observations: dict = Field(default_factory=dict)
    status: str = "future_extension"


def run_mode_c(*args, **kwargs):
    raise NotImplementedError(
        "Mode C is reserved as a future extension and is not implemented in the current stage."
    )
