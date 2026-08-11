#pragma once

#include <string>

#include "dxai_bridge/protocol.hpp"

namespace dxai_bridge {

[[nodiscard]] std::string ValidateActionCandidate(const ActionCandidate &action);
[[nodiscard]] std::string ValidateObservation(const Observation &observation);
[[nodiscard]] std::string ValidateStepRequest(
    const Observation &currentObservation,
    const StepRequest &request);

} // namespace dxai_bridge
