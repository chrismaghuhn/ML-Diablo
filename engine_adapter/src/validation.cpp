#include "dxai_bridge/validation.hpp"

#include <cmath>
#include <cstdint>
#include <set>
#include <utility>

namespace dxai_bridge {
namespace {

using PayloadMask = std::uint16_t;

constexpr PayloadMask NoPayload = 0;
constexpr PayloadMask TargetEntity = 1U << 0U;
constexpr PayloadMask TargetTile = 1U << 1U;
constexpr PayloadMask InventorySlot = 1U << 2U;
constexpr PayloadMask EquipmentSlot = 1U << 3U;
constexpr PayloadMask BeltSlot = 1U << 4U;
constexpr PayloadMask SpellId = 1U << 5U;
constexpr PayloadMask StoreItemId = 1U << 6U;
constexpr PayloadMask StatId = 1U << 7U;
constexpr std::size_t MaxCandidateFeatures = 64;

constexpr PayloadMask CombinePayloads(PayloadMask lhs, PayloadMask rhs)
{
    return static_cast<PayloadMask>(lhs | rhs);
}

PayloadMask PresentPayload(const ActionCandidate &action)
{
    PayloadMask result = NoPayload;
    if (action.targetEntityId.has_value())
        result |= TargetEntity;
    if (action.targetTile.has_value())
        result |= TargetTile;
    if (action.inventorySlot.has_value())
        result |= InventorySlot;
    if (action.equipmentSlot.has_value())
        result |= EquipmentSlot;
    if (action.beltSlot.has_value())
        result |= BeltSlot;
    if (action.spellId.has_value())
        result |= SpellId;
    if (action.storeItemId.has_value())
        result |= StoreItemId;
    if (action.statId.has_value())
        result |= StatId;
    return result;
}

std::pair<PayloadMask, PayloadMask> PayloadContract(ActionKind kind)
{
    switch (kind) {
    case ActionKind::Wait:
    case ActionKind::ReturnToTown:
        return { NoPayload, NoPayload };
    case ActionKind::MoveToTile:
        return { TargetTile, TargetTile };
    case ActionKind::AttackEntity:
    case ActionKind::PickUpItem:
    case ActionKind::OperateObject:
    case ActionKind::TakeStairs:
        return { TargetEntity, TargetEntity };
    case ActionKind::CastSpellAtEntity:
        return { CombinePayloads(TargetEntity, SpellId), CombinePayloads(TargetEntity, SpellId) };
    case ActionKind::CastSpellAtTile:
        return { CombinePayloads(TargetTile, SpellId), CombinePayloads(TargetTile, SpellId) };
    case ActionKind::UseBeltSlot:
        return { BeltSlot, BeltSlot };
    case ActionKind::EquipItem:
        return { InventorySlot, CombinePayloads(InventorySlot, EquipmentSlot) };
    case ActionKind::UnequipItem:
        return { EquipmentSlot, EquipmentSlot };
    case ActionKind::DropItem:
    case ActionKind::SellItem:
    case ActionKind::RepairItem:
        return { InventorySlot, InventorySlot };
    case ActionKind::BuyItem:
        return { StoreItemId, StoreItemId };
    case ActionKind::AllocateStat:
        return { StatId, StatId };
    }
    return { NoPayload, NoPayload };
}

} // namespace

std::string ValidateActionCandidate(const ActionCandidate &action)
{
    const auto [required, allowed] = PayloadContract(action.kind);
    const PayloadMask present = PresentPayload(action);
    if ((present & required) != required)
        return "required semantic payload is missing";
    if ((present & static_cast<std::uint16_t>(~allowed)) != 0)
        return "unexpected semantic payload is present";
    if (action.features.size() > MaxCandidateFeatures)
        return "too many candidate features";
    for (const float feature : action.features) {
        if (!std::isfinite(feature))
            return "candidate features must be finite";
    }
    return {};
}

std::string ValidateObservation(const Observation &observation)
{
    if (observation.schemaVersion != kObservationVersion)
        return "unsupported observation schema";
    if (observation.episodeId.empty() || observation.taskId.empty())
        return "episodeId and taskId are required";
    if (observation.player.hpMax <= 0 || observation.player.hp < 0
        || observation.player.hp > observation.player.hpMax)
        return "invalid player HP";
    if (observation.legalActions.empty())
        return "at least one legal action is required";

    std::set<std::uint32_t> ids;
    for (std::size_t index = 0; index < observation.legalActions.size(); ++index) {
        const auto &action = observation.legalActions[index];
        if (action.candidateId != index)
            return "candidate IDs must be dense and ordered";
        if (!ids.insert(action.candidateId).second)
            return "candidate IDs must be unique";
        const std::string actionError = ValidateActionCandidate(action);
        if (!actionError.empty())
            return "invalid action candidate: " + actionError;
    }
    return {};
}

std::string ValidateStepRequest(
    const Observation &currentObservation,
    const StepRequest &request)
{
    if (request.protocolVersion != kProtocolVersion)
        return "unsupported protocol version";
    if (request.episodeId != currentObservation.episodeId)
        return "episode mismatch";
    if (request.expectedStepId != currentObservation.stepId)
        return "stale or out-of-order step request";
    if (request.candidateId >= currentObservation.legalActions.size())
        return "candidate is not legal for this decision";
    return {};
}

} // namespace dxai_bridge
