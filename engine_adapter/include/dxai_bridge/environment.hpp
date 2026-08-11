#pragma once

#include "dxai_bridge/protocol.hpp"

namespace dxai_bridge {

class Environment {
public:
    virtual ~Environment() = default;
    virtual Observation Reset(const ResetRequest &request) = 0;
    virtual StepResult Step(const StepRequest &request) = 0;
};

} // namespace dxai_bridge
