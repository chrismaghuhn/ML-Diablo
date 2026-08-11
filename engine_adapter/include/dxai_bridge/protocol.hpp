#pragma once

#include <cstdint>
#include <optional>
#include <string>
#include <utility>
#include <vector>

namespace dxai_bridge {

inline constexpr const char *kProtocolVersion = "dxai.bridge.v1";
inline constexpr const char *kObservationVersion = "dxai.observation.v1";

struct Vec2 {
    std::int32_t x {};
    std::int32_t y {};

    friend bool operator==(const Vec2 &, const Vec2 &) = default;
};

enum class ActionKind : std::uint8_t {
    Wait,
    MoveToTile,
    AttackEntity,
    CastSpellAtEntity,
    CastSpellAtTile,
    UseBeltSlot,
    PickUpItem,
    OperateObject,
    EquipItem,
    UnequipItem,
    DropItem,
    BuyItem,
    SellItem,
    RepairItem,
    AllocateStat,
    TakeStairs,
    ReturnToTown,
};

struct ActionCandidate {
    std::uint32_t candidateId {};
    ActionKind kind { ActionKind::Wait };
    std::optional<std::uint32_t> targetEntityId;
    std::optional<Vec2> targetTile;
    std::optional<std::uint32_t> inventorySlot;
    std::optional<std::uint32_t> equipmentSlot;
    std::optional<std::uint32_t> beltSlot;
    std::optional<std::uint32_t> spellId;
    std::optional<std::uint32_t> storeItemId;
    std::optional<std::uint32_t> statId;
    std::vector<float> features;
    std::string label;
};

struct PlayerState {
    Vec2 position;
    std::int32_t hp {};
    std::int32_t hpMax {};
    std::int32_t mana {};
    std::int32_t manaMax {};
    std::int32_t level { 1 };
    std::int32_t dungeonLevel { 1 };
    std::int64_t experience {};
    std::int64_t gold {};
};

struct EntityState {
    std::uint32_t entityId {};
    std::string kind;
    Vec2 position;
    std::string typeId;
    std::optional<std::int32_t> hp;
    std::optional<std::int32_t> hpMax;
    bool hostile {};
};

struct Observation {
    std::string schemaVersion { kObservationVersion };
    std::string episodeId;
    std::string taskId;
    std::uint64_t seed {};
    std::uint64_t stepId {};
    std::uint64_t engineTick {};
    std::string decisionReason;
    PlayerState player;
    std::vector<EntityState> entities;
    std::vector<ActionCandidate> legalActions;
    std::vector<std::string> recentEvents;
};

struct ResetRequest {
    std::string protocolVersion { kProtocolVersion };
    std::uint64_t requestId {};
    std::uint64_t seed {};
    std::string taskId;
};

struct StepRequest {
    std::string protocolVersion { kProtocolVersion };
    std::uint64_t requestId {};
    std::string episodeId;
    std::uint64_t expectedStepId {};
    std::uint32_t candidateId {};
};

struct StepResult {
    Observation observation;
    double reward {};
    bool terminated {};
    bool truncated {};
    std::string outcome;
};

} // namespace dxai_bridge
