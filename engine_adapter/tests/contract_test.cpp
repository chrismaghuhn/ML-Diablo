#include <cstdlib>
#include <iostream>
#include <limits>
#include <stdexcept>

#include "dxai_bridge/environment.hpp"
#include "dxai_bridge/validation.hpp"

namespace {

class FakeEnvironment final : public dxai_bridge::Environment {
public:
    dxai_bridge::Observation Reset(const dxai_bridge::ResetRequest &request) override
    {
        current_ = {};
        current_.episodeId = "fake-" + std::to_string(request.seed);
        current_.taskId = request.taskId;
        current_.seed = request.seed;
        current_.decisionReason = "RESET";
        current_.player.hp = 20;
        current_.player.hpMax = 20;
        current_.legalActions = {
            dxai_bridge::ActionCandidate {
                .candidateId = 0,
                .kind = dxai_bridge::ActionKind::Wait,
            },
            dxai_bridge::ActionCandidate {
                .candidateId = 1,
                .kind = dxai_bridge::ActionKind::MoveToTile,
                .targetTile = dxai_bridge::Vec2 { 2, 1 },
            },
        };
        return current_;
    }

    dxai_bridge::StepResult Step(const dxai_bridge::StepRequest &request) override
    {
        const auto error = dxai_bridge::ValidateStepRequest(current_, request);
        if (!error.empty())
            throw std::invalid_argument(error);
        ++current_.stepId;
        ++current_.engineTick;
        current_.decisionReason = "PLAYER_READY";
        return dxai_bridge::StepResult { .observation = current_, .reward = -0.001 };
    }

private:
    dxai_bridge::Observation current_;
};

void Require(bool condition, const char *message)
{
    if (!condition)
        throw std::runtime_error(message);
}

} // namespace

int main()
{
    FakeEnvironment environment;
    const auto observation = environment.Reset(dxai_bridge::ResetRequest {
        .requestId = 1,
        .seed = 42,
        .taskId = "combat.single_melee.v0",
    });
    Require(dxai_bridge::ValidateObservation(observation).empty(), "observation must validate");

    const auto result = environment.Step(dxai_bridge::StepRequest {
        .requestId = 2,
        .episodeId = observation.episodeId,
        .expectedStepId = observation.stepId,
        .candidateId = 1,
    });
    Require(result.observation.stepId == 1, "step must advance once");

    const auto stale = dxai_bridge::ValidateStepRequest(
        result.observation,
        dxai_bridge::StepRequest {
            .requestId = 3,
            .episodeId = result.observation.episodeId,
            .expectedStepId = 0,
            .candidateId = 0,
        });
    Require(!stale.empty(), "stale requests must be rejected");

    dxai_bridge::ActionCandidate missingTarget {
        .candidateId = 0,
        .kind = dxai_bridge::ActionKind::AttackEntity,
    };
    Require(
        !dxai_bridge::ValidateActionCandidate(missingTarget).empty(),
        "required payload must be enforced");

    dxai_bridge::ActionCandidate pollutedWait {
        .candidateId = 0,
        .kind = dxai_bridge::ActionKind::Wait,
        .targetEntityId = 12,
    };
    Require(
        !dxai_bridge::ValidateActionCandidate(pollutedWait).empty(),
        "unexpected payload must be rejected");

    dxai_bridge::ActionCandidate nonFinite {
        .candidateId = 0,
        .kind = dxai_bridge::ActionKind::Wait,
        .features = { std::numeric_limits<float>::infinity() },
    };
    Require(
        !dxai_bridge::ValidateActionCandidate(nonFinite).empty(),
        "non-finite features must be rejected");

    std::cout << "dxai bridge contract OK\n";
    return EXIT_SUCCESS;
}
