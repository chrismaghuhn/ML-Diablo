#include <algorithm>
#include <array>
#include <chrono>
#include <cstdint>
#include <cstdlib>
#include <filesystem>
#include <iomanip>
#include <iostream>
#include <limits>
#include <expected>
#include <optional>
#include <sstream>
#include <stdexcept>
#include <string>
#include <string_view>
#include <vector>

#include "dxai_bridge/process_protocol.hpp"

#if defined(_WIN32)
#define NOMINMAX
#include <windows.h>
#include <bcrypt.h>
#endif

#include "diablo.h"
#include "engine/assets.hpp"
#include "engine/sound.h"
#include "game_mode.hpp"
#include "headless_mode.hpp"
#include "items.h"
#include "levels/gendung.h"
#include "levels/tile_properties.hpp"
#include "monster.h"
#include "multi.h"
#include "player.h"
#include "portal.h"
#include "quests.h"
#include "tables/itemdat.h"
#include "tables/misdat.h"
#include "tables/monstdat.h"
#include "tables/objdat.h"
#include "tables/playerdat.hpp"
#include "tables/spelldat.h"
#include "tables/textdat.h"
#include "utils/paths.h"

namespace devilution {
void ProcessPlayers();
void ProcessMonsters();
void ProcessTowners();
void ProcessObjects();
void ProcessMissiles();
void ProcessItems();
void ProcessLightList();
void ProcessVisionList();
void sound_update();
void CheckTriggers();
void CheckQuests();
void RedrawViewport();
void pfile_update(bool force_write);
void plrctrls_after_game_logic();
void ClearLastSentPlayerCmd();
}

namespace {

using namespace devilution;

enum class ProbeErrorCode {
	InvalidArgument,
	AssetDataUnavailable,
	EngineInitializationFailed,
	ObservationContractFailed,
	CandidateRejected,
	StateMismatch,
	StaleCandidate,
	NoSupportedCandidates,
	ActionResolutionFailed,
	Internal,
};

const char *ErrorCodeName(ProbeErrorCode code)
{
	switch (code) {
	case ProbeErrorCode::InvalidArgument:
		return "INVALID_ARGUMENT";
	case ProbeErrorCode::AssetDataUnavailable:
		return "ASSET_DATA_UNAVAILABLE";
	case ProbeErrorCode::EngineInitializationFailed:
		return "ENGINE_INITIALIZATION_FAILED";
	case ProbeErrorCode::ObservationContractFailed:
		return "OBSERVATION_CONTRACT_FAILED";
	case ProbeErrorCode::CandidateRejected:
		return "CANDIDATE_REJECTED";
	case ProbeErrorCode::StateMismatch:
		return "STATE_MISMATCH";
	case ProbeErrorCode::StaleCandidate:
		return "STALE_CANDIDATE";
	case ProbeErrorCode::NoSupportedCandidates:
		return "NO_SUPPORTED_CANDIDATES";
	case ProbeErrorCode::ActionResolutionFailed:
		return "ACTION_RESOLUTION_FAILED";
	case ProbeErrorCode::Internal:
		return "INTERNAL";
	}
	return "INTERNAL";
}

class ProbeFailure final : public std::runtime_error {
public:
	ProbeFailure(ProbeErrorCode code, std::string message)
	    : std::runtime_error(std::move(message))
	    , code_(code)
	{
	}

	[[nodiscard]] ProbeErrorCode code() const
	{
		return code_;
	}

private:
	ProbeErrorCode code_;
};

struct RuntimeDataPointers {
	uint32_t *dungeonSeeds {};
	DungeonFlag (*dFlags)[MAXDUNY] {};
	int8_t (*dPlayer)[MAXDUNY] {};
	int16_t (*dMonster)[MAXDUNY] {};
	int8_t (*dItem)[MAXDUNY] {};
	Monster *monsters {};
	unsigned *activeMonsters {};
	size_t *activeMonsterCount {};
};

RuntimeDataPointers runtimeData;

enum class ProbeMode {
	Observation,
	M03,
	EnvironmentStdio,
};

struct SemanticCandidate {
	std::uint32_t candidateId {};
	Point targetTile;
};

constexpr int ObservationTileRadius = 5;
constexpr std::uint64_t ActionResolutionSafetyBound = 256;

template <typename T>
T *LoadExportedData(std::string_view symbol)
{
#if defined(_WIN32)
	const HMODULE module = GetModuleHandleW(L"libdevilutionx_so.dll");
	if (module == nullptr)
		throw ProbeFailure(ProbeErrorCode::EngineInitializationFailed, "engine shared library is not loaded");
	const std::string symbolName(symbol);
	const FARPROC address = GetProcAddress(module, symbolName.c_str());
	if (address == nullptr)
		throw ProbeFailure(ProbeErrorCode::EngineInitializationFailed, "required engine data export is unavailable");
	return reinterpret_cast<T *>(reinterpret_cast<std::uintptr_t>(address));
#else
	(void)symbol;
	throw ProbeFailure(ProbeErrorCode::EngineInitializationFailed, "M0.2 probe requires Windows DLL data exports");
#endif
}

void InitializeRuntimeData()
{
	runtimeData.dungeonSeeds = LoadExportedData<uint32_t>("?DungeonSeeds@devilution@@3PAIA");
	runtimeData.dFlags = LoadExportedData<DungeonFlag[MAXDUNY]>("?dFlags@devilution@@3PAY0HA@W4DungeonFlag@1@A");
	runtimeData.dPlayer = LoadExportedData<int8_t[MAXDUNY]>("?dPlayer@devilution@@3PAY0HA@CA");
	runtimeData.dMonster = LoadExportedData<int16_t[MAXDUNY]>("?dMonster@devilution@@3PAY0HA@FA");
	runtimeData.dItem = LoadExportedData<int8_t[MAXDUNY]>("?dItem@devilution@@3PAY0HA@CA");
	runtimeData.monsters = LoadExportedData<Monster>("?Monsters@devilution@@3PAUMonster@1@A");
	runtimeData.activeMonsters = LoadExportedData<unsigned>("?ActiveMonsters@devilution@@3PAIA");
	runtimeData.activeMonsterCount = LoadExportedData<size_t>("?ActiveMonsterCount@devilution@@3_KA");
}

bool IsVisibleForObservation(Point position)
{
	return InDungeonBounds(position) && HasAnyOf(runtimeData.dFlags[position.x][position.y], DungeonFlag::Visible);
}

struct Arguments {
	std::filesystem::path assets;
	std::filesystem::path coreAssets;
	std::filesystem::path runtimeRoot;
	std::uint64_t seed {};
	std::string task;
	ProbeMode mode { ProbeMode::Observation };
	std::optional<std::int64_t> candidateId;
	std::optional<std::string> expectedEpisodeId;
	std::optional<std::uint64_t> expectedStepId;
	std::optional<std::string> expectedCandidateSetSha256;
};

std::string JsonEscape(std::string_view value)
{
	std::ostringstream result;
	result << '"';
	for (const unsigned char character : value) {
		switch (character) {
		case '"':
			result << "\\\"";
			break;
		case '\\':
			result << "\\\\";
			break;
		case '\b':
			result << "\\b";
			break;
		case '\f':
			result << "\\f";
			break;
		case '\n':
			result << "\\n";
			break;
		case '\r':
			result << "\\r";
			break;
		case '\t':
			result << "\\t";
			break;
		default:
			if (character < 0x20) {
				result << "\\u" << std::hex << std::setw(4) << std::setfill('0')
				       << static_cast<unsigned>(character) << std::dec << std::setfill(' ');
			} else {
				result << static_cast<char>(character);
			}
			break;
		}
	}
	result << '"';
	return result.str();
}

std::uint64_t ParseUnsigned(std::string_view value, std::string_view name)
{
	try {
		size_t parsed = 0;
		const std::uint64_t result = std::stoull(std::string(value), &parsed, 10);
		if (parsed != value.size())
			throw std::invalid_argument("trailing characters");
		return result;
	} catch (const std::exception &) {
		throw ProbeFailure(ProbeErrorCode::InvalidArgument, "invalid " + std::string(name));
	}
}

std::int64_t ParseSigned(std::string_view value, std::string_view name)
{
	try {
		size_t parsed = 0;
		const std::int64_t result = std::stoll(std::string(value), &parsed, 10);
		if (parsed != value.size())
			throw std::invalid_argument("trailing characters");
		return result;
	} catch (const std::exception &) {
		throw ProbeFailure(ProbeErrorCode::InvalidArgument, "invalid " + std::string(name));
	}
}

Arguments ParseArguments(int argc, char **argv)
{
	Arguments arguments;
	for (int index = 1; index < argc; ++index) {
		const std::string_view option = argv[index];
		if (option == "--env-stdio") {
			arguments.mode = ProbeMode::EnvironmentStdio;
			continue;
		}
		if (index + 1 >= argc)
			throw ProbeFailure(ProbeErrorCode::InvalidArgument, "missing value for " + std::string(option));
		const std::string_view value = argv[++index];
		if (option == "--assets") {
			arguments.assets = value;
		} else if (option == "--core-assets") {
			arguments.coreAssets = value;
		} else if (option == "--runtime-root") {
			arguments.runtimeRoot = value;
		} else if (option == "--seed") {
			const std::uint64_t parsedSeed = ParseUnsigned(value, "seed");
			if (parsedSeed > std::numeric_limits<std::uint32_t>::max())
				throw ProbeFailure(ProbeErrorCode::InvalidArgument, "seed must fit in uint32_t");
			arguments.seed = parsedSeed;
		} else if (option == "--task") {
			arguments.task = value;
		} else if (option == "--mode") {
			if (value == "observation") {
				arguments.mode = ProbeMode::Observation;
			} else if (value == "m03") {
				arguments.mode = ProbeMode::M03;
			} else if (value == "env-stdio") {
				arguments.mode = ProbeMode::EnvironmentStdio;
			} else {
				throw ProbeFailure(ProbeErrorCode::InvalidArgument, "unsupported probe mode");
			}
		} else if (option == "--candidate-id") {
			arguments.candidateId = ParseSigned(value, "candidate-id");
		} else if (option == "--expected-episode-id") {
			arguments.expectedEpisodeId = std::string(value);
		} else if (option == "--expected-step-id") {
			arguments.expectedStepId = ParseUnsigned(value, "expected-step-id");
		} else if (option == "--expected-candidate-set-sha256") {
			arguments.expectedCandidateSetSha256 = std::string(value);
		} else {
			throw ProbeFailure(ProbeErrorCode::InvalidArgument, "unknown option " + std::string(option));
		}
	}
	if (arguments.assets.empty() || arguments.coreAssets.empty())
		throw ProbeFailure(ProbeErrorCode::InvalidArgument, "--assets and --core-assets are required");
	if (arguments.task.empty()) {
		if (arguments.mode != ProbeMode::EnvironmentStdio)
			throw ProbeFailure(ProbeErrorCode::InvalidArgument, "--task is required");
		arguments.task = "combat.single_melee.v0";
	}
	if (arguments.task != "combat.single_melee.v0")
		throw ProbeFailure(ProbeErrorCode::InvalidArgument, "unsupported probe task");
	if (arguments.runtimeRoot.empty())
		arguments.runtimeRoot = std::filesystem::temp_directory_path() / "dxai-m02-probe";
	if (arguments.mode == ProbeMode::Observation
	    && (arguments.candidateId.has_value() || arguments.expectedEpisodeId.has_value()
	        || arguments.expectedStepId.has_value() || arguments.expectedCandidateSetSha256.has_value()))
		throw ProbeFailure(ProbeErrorCode::InvalidArgument, "action identity requires m03 mode");
	if (arguments.mode == ProbeMode::M03 && arguments.candidateId.has_value()
	    && (!arguments.expectedEpisodeId.has_value() || !arguments.expectedStepId.has_value()
        || !arguments.expectedCandidateSetSha256.has_value()))
		throw ProbeFailure(ProbeErrorCode::InvalidArgument, "m03 action identity is incomplete");
	if (arguments.mode == ProbeMode::EnvironmentStdio
	    && (arguments.candidateId.has_value() || arguments.expectedEpisodeId.has_value()
	        || arguments.expectedStepId.has_value() || arguments.expectedCandidateSetSha256.has_value()))
		throw ProbeFailure(ProbeErrorCode::InvalidArgument, "action identity belongs in env-stdio requests");
	return arguments;
}

void ConfigurePaths(const Arguments &arguments)
{
	std::error_code error;
	if (!std::filesystem::is_directory(arguments.assets, error))
		throw ProbeFailure(ProbeErrorCode::AssetDataUnavailable, "asset directory is unavailable");
	if (!std::filesystem::is_directory(arguments.coreAssets, error))
		throw ProbeFailure(ProbeErrorCode::AssetDataUnavailable, "core asset directory is unavailable");
	std::filesystem::create_directories(arguments.runtimeRoot, error);
	if (error)
		throw ProbeFailure(ProbeErrorCode::Internal, "unable to create runtime root");

	paths::SetBasePath(arguments.assets.string());
	paths::SetAssetsPath(arguments.coreAssets.string());
	paths::SetPrefPath(arguments.runtimeRoot.string());
	paths::SetConfigPath(arguments.runtimeRoot.string());
}

void InitializeEngine(const Arguments &arguments)
{
	HeadlessMode = true;
	// HeadlessMode skips UI but this pinned upstream still starts level music.
	// Keep the observation probe independent of an initialized SDL audio device.
	gbMusicOn = false;
	gbSoundOn = false;
	ConfigurePaths(arguments);
	InitializeRuntimeData();
	LoadCoreArchives();
	LoadGameArchives();
	if (!FindAsset("levels\\l1data\\l1.sol").ok())
		throw ProbeFailure(ProbeErrorCode::AssetDataUnavailable, "required Diablo level data is unavailable");

	LoadTextData();
	LoadPlayerDataFiles();
	LoadSpellData();
	LoadMissileData();
	LoadMonsterData();
	LoadItemData();
	LoadObjectData();
	LoadQuestData();

	gbIsHellfire = false;
	gbIsSpawn = false;
	gbIsMultiplayer = false;
	sgGameInitInfo = {};
	sgGameInitInfo.nDifficulty = DIFF_NORMAL;
	sgGameInitInfo.nTickRate = 20;
	sgGameInitInfo.bFriendlyFire = 0;
	sgGameInitInfo.fullQuests = 1;
	sgGameInitInfo.gameSeed[0] = static_cast<std::uint32_t>(arguments.seed);

	Players.clear();
	Players.resize(1);
	MyPlayerId = 0;
	MyPlayer = &Players[0];
	CreatePlayer(*MyPlayer, HeroClass::Warrior);
	MyPlayer->pOriginalCathedral = true;
	MyPlayer->plractive = true;
	MyPlayer->plrlevel = 1;

	InitLevels();
	InitQuests();
	InitPortals();
	InitDungMsgs(*MyPlayer);
	currlevel = 1;
	leveltype = GetLevelType(currlevel);
	runtimeData.dungeonSeeds[currlevel] = static_cast<std::uint32_t>(arguments.seed);

	const std::expected<void, std::string> loadResult = LoadGameLevel(false, ENTRY_MAIN);
	if (!loadResult.has_value())
		throw ProbeFailure(ProbeErrorCode::EngineInitializationFailed, loadResult.error());
	if (MyPlayer == nullptr || !MyPlayer->plractive || MyPlayer->plrlevel != currlevel)
		throw ProbeFailure(ProbeErrorCode::EngineInitializationFailed, "player was not initialized");
}

bool IsControllableDecisionBoundary()
{
	return MyPlayer != nullptr
	    && MyPlayer->plractive
	    && MyPlayer->plrlevel == currlevel
	    && PauseMode == 0
	    && MyPlayer->_pmode == PM_STAND
	    && MyPlayer->position.future == MyPlayer->position.tile
	    && MyPlayer->walkpath[0] == WALK_NONE
	    && MyPlayer->destAction == ACTION_NONE;
}

bool IsWithinObservationWindow(Point center, Point position)
{
	return std::abs(position.x - center.x) <= ObservationTileRadius
	    && std::abs(position.y - center.y) <= ObservationTileRadius;
}

bool IsObservableOpenTile(Point position)
{
	if (!InDungeonBounds(position) || !IsVisibleForObservation(position)
	    || !HasAnyOf(runtimeData.dFlags[position.x][position.y], DungeonFlag::Explored)
	    || TileHasAny(position, TileProperties::Solid))
		return false;

	// This is deliberately the same conservative occupancy projection used by
	// AppendTiles. It excludes items and non-solid objects too, even where the
	// native movement rules could otherwise permit the move, so candidate
	// presence cannot depend on an unprojected entity detail.
	return runtimeData.dPlayer[position.x][position.y] == 0
	    && runtimeData.dMonster[position.x][position.y] == 0
	    && runtimeData.dItem[position.x][position.y] == 0
	    && dObject[position.x][position.y] == 0;
}

std::vector<Point> NativeCornerTiles(Point start, Point destination)
{
	const int dx = destination.x - start.x;
	const int dy = destination.y - start.y;
	if (dx == 0 && std::abs(dy) == 1)
		return { { destination.x - 1, destination.y }, { destination.x + 1, destination.y } };
	if (dy == 0 && std::abs(dx) == 1)
		return { { destination.x, destination.y - 1 }, { destination.x, destination.y + 1 } };
	return {};
}

bool IsObservableNativeMove(Point start, Point destination)
{
	const int dx = destination.x - start.x;
	const int dy = destination.y - start.y;
	if (std::max(std::abs(dx), std::abs(dy)) != 1 || !IsWithinObservationWindow(start, destination))
		return false;
	if (!IsObservableOpenTile(destination))
		return false;
	for (const Point corner : NativeCornerTiles(start, destination)) {
		if (!IsObservableOpenTile(corner))
			return false;
	}

	// These are the pinned DevilutionX legality checks for a direct adjacent
	// movement candidate. No Python-side walkability rule is used.
	return CanStep(start, destination) && PosOkPlayer(*MyPlayer, destination);
}

std::vector<SemanticCandidate> GenerateMoveCandidates()
{
	if (!IsControllableDecisionBoundary())
		throw ProbeFailure(ProbeErrorCode::EngineInitializationFailed, "candidate generation requires a decision boundary");

	const Point start = MyPlayer->position.tile;
	std::vector<Point> destinations;
	for (int dy = -1; dy <= 1; ++dy) {
		for (int dx = -1; dx <= 1; ++dx) {
			if (dx == 0 && dy == 0)
				continue;
			const Point destination { start.x + dx, start.y + dy };
			if (IsObservableNativeMove(start, destination))
				destinations.push_back(destination);
		}
	}

	std::sort(destinations.begin(), destinations.end(), [](Point lhs, Point rhs) {
		if (lhs.x != rhs.x)
			return lhs.x < rhs.x;
		return lhs.y < rhs.y;
	});
	destinations.erase(std::unique(destinations.begin(), destinations.end()), destinations.end());

	std::vector<SemanticCandidate> result;
	result.reserve(destinations.size());
	for (std::size_t index = 0; index < destinations.size(); ++index)
		result.push_back({ static_cast<std::uint32_t>(index), destinations[index] });
	return result;
}

std::string CanonicalCandidateSetKey(const std::vector<SemanticCandidate> &candidates)
{
	std::ostringstream key;
	key << "dxai.observation.v1|dxai.action.v1|";
	for (std::size_t index = 0; index < candidates.size(); ++index) {
		if (index != 0)
			key << "||";
		const SemanticCandidate &candidate = candidates[index];
		if (candidate.candidateId != index)
			throw ProbeFailure(ProbeErrorCode::Internal, "candidate IDs are not dense");
		for (std::size_t previous = 0; previous < index; ++previous) {
			if (candidates[previous].targetTile == candidate.targetTile)
				throw ProbeFailure(ProbeErrorCode::Internal, "duplicate semantic move candidate");
		}
		key << "candidate_id=" << candidate.candidateId
		    << ";kind=MOVE_TO_TILE"
		    << ";target_entity_id=null"
		    << ";target_tile=" << candidate.targetTile.x << ',' << candidate.targetTile.y
		    << ";inventory_slot=null"
		    << ";equipment_slot=null"
		    << ";belt_slot=null"
		    << ";spell_id=null"
		    << ";store_item_id=null"
		    << ";stat_id=null";
	}
	return key.str();
}

std::string Sha256(std::string_view input)
{
#if defined(_WIN32)
	BCRYPT_ALG_HANDLE algorithm = nullptr;
	if (BCryptOpenAlgorithmProvider(&algorithm, BCRYPT_SHA256_ALGORITHM, nullptr, 0) != 0)
		throw ProbeFailure(ProbeErrorCode::Internal, "unable to initialize SHA-256");

	ULONG objectLength = 0;
	ULONG resultLength = 0;
	if (BCryptGetProperty(
			algorithm,
			BCRYPT_OBJECT_LENGTH,
			reinterpret_cast<PUCHAR>(&objectLength),
			static_cast<ULONG>(sizeof(objectLength)),
			&resultLength,
			0)
	    != 0) {
		BCryptCloseAlgorithmProvider(algorithm, 0);
		throw ProbeFailure(ProbeErrorCode::Internal, "unable to query SHA-256 state size");
	}

	std::vector<UCHAR> object(objectLength);
	BCRYPT_HASH_HANDLE hash = nullptr;
	if (BCryptCreateHash(algorithm, &hash, object.data(), objectLength, nullptr, 0, 0) != 0) {
		BCryptCloseAlgorithmProvider(algorithm, 0);
		throw ProbeFailure(ProbeErrorCode::Internal, "unable to create SHA-256 state");
	}
	if (BCryptHashData(hash, reinterpret_cast<PUCHAR>(const_cast<char *>(input.data())), static_cast<ULONG>(input.size()), 0) != 0) {
		BCryptDestroyHash(hash);
		BCryptCloseAlgorithmProvider(algorithm, 0);
		throw ProbeFailure(ProbeErrorCode::Internal, "unable to hash candidate set");
	}

	std::array<UCHAR, 32> digest {};
	if (BCryptFinishHash(hash, digest.data(), static_cast<ULONG>(digest.size()), 0) != 0) {
		BCryptDestroyHash(hash);
		BCryptCloseAlgorithmProvider(algorithm, 0);
		throw ProbeFailure(ProbeErrorCode::Internal, "unable to finalize candidate-set hash");
	}
	BCryptDestroyHash(hash);
	BCryptCloseAlgorithmProvider(algorithm, 0);

	std::ostringstream result;
	result << std::hex << std::setfill('0');
	for (const UCHAR value : digest)
		result << std::setw(2) << static_cast<unsigned>(value);
	return result.str();
#else
	(void)input;
	throw ProbeFailure(ProbeErrorCode::Internal, "M0.3 candidate hashing requires Windows");
#endif
}

const char *ClassId(HeroClass heroClass)
{
	switch (heroClass) {
	case HeroClass::Warrior:
		return "WARRIOR";
	case HeroClass::Rogue:
		return "ROGUE";
	case HeroClass::Sorcerer:
		return "SORCERER";
	case HeroClass::Monk:
		return "MONK";
	case HeroClass::Bard:
		return "BARD";
	case HeroClass::Barbarian:
		return "BARBARIAN";
	case HeroClass::NUM_MAX_CLASSES:
		break;
	}
	return "UNKNOWN";
}

const char *ItemTypeId(ItemType itemType)
{
	switch (itemType) {
	case ItemType::Misc:
		return "MISC";
	case ItemType::Sword:
		return "SWORD";
	case ItemType::Axe:
		return "AXE";
	case ItemType::Bow:
		return "BOW";
	case ItemType::Mace:
		return "MACE";
	case ItemType::Shield:
		return "SHIELD";
	case ItemType::LightArmor:
		return "LIGHT_ARMOR";
	case ItemType::Helm:
		return "HELM";
	case ItemType::MediumArmor:
		return "MEDIUM_ARMOR";
	case ItemType::HeavyArmor:
		return "HEAVY_ARMOR";
	case ItemType::Staff:
		return "STAFF";
	case ItemType::Gold:
		return "GOLD";
	case ItemType::Ring:
		return "RING";
	case ItemType::Amulet:
		return "AMULET";
	case ItemType::None:
		return "UNIDENTIFIED";
	}
	return "UNIDENTIFIED";
}

bool IsPotion(const Item &item)
{
	switch (item._iMiscId) {
	case IMISC_FULLHEAL:
	case IMISC_HEAL:
	case IMISC_MANA:
	case IMISC_FULLMANA:
	case IMISC_REJUV:
	case IMISC_FULLREJUV:
		return true;
	default:
		return false;
	}
}

struct InventoryEntry {
	const char *container;
	std::uint32_t slot;
	std::string typeId;
	bool identified;
	std::uint32_t quantity;
};

void AppendInventoryEntry(std::vector<InventoryEntry> &entries, const char *container, std::uint32_t slot, const Item &item)
{
	if (item.isEmpty())
		return;
	const bool identified = item._iIdentified;
	const std::uint32_t quantity = item.isGold() && item._ivalue > 0
	    ? static_cast<std::uint32_t>(item._ivalue)
	    : 1U;
	entries.push_back({
	    .container = container,
	    .slot = slot,
	    .typeId = identified ? ItemTypeId(item._itype) : "UNIDENTIFIED",
	    .identified = identified,
	    .quantity = quantity,
	});
}

std::vector<InventoryEntry> ProjectInventory(const Player &player)
{
	std::vector<InventoryEntry> entries;
	for (std::uint32_t slot = 0; slot < NUM_INVLOC; ++slot)
		AppendInventoryEntry(entries, "EQUIPPED", slot, player.InvBody[slot]);
	for (std::uint32_t slot = 0; slot < static_cast<std::uint32_t>(player._pNumInv); ++slot)
		AppendInventoryEntry(entries, "INVENTORY", slot, player.InvList[slot]);
	for (std::uint32_t slot = 0; slot < MaxBeltItems; ++slot)
		AppendInventoryEntry(entries, "BELT", slot, player.SpdList[slot]);
	return entries;
}

std::uint32_t CountPotions(const Player &player)
{
	std::uint32_t count = 0;
	auto countItem = [&count](const Item &item) {
		if (!item.isEmpty() && IsPotion(item))
			++count;
	};
	for (std::uint32_t slot = 0; slot < NUM_INVLOC; ++slot)
		countItem(player.InvBody[slot]);
	for (std::uint32_t slot = 0; slot < static_cast<std::uint32_t>(player._pNumInv); ++slot)
		countItem(player.InvList[slot]);
	for (std::uint32_t slot = 0; slot < MaxBeltItems; ++slot)
		countItem(player.SpdList[slot]);
	return count;
}

int WholeResource(int fixedPointValue)
{
	return std::max(0, fixedPointValue >> 6);
}

void AppendVec2(std::ostringstream &output, Point point)
{
	output << "{\"x\":" << point.x << ",\"y\":" << point.y << '}';
}

void AppendInventory(std::ostringstream &output, const std::vector<InventoryEntry> &entries)
{
	output << '[';
	for (std::size_t index = 0; index < entries.size(); ++index) {
		if (index != 0)
			output << ',';
		const InventoryEntry &entry = entries[index];
		output << "{\"container\":" << JsonEscape(entry.container)
		       << ",\"slot\":" << entry.slot
		       << ",\"type_id\":" << JsonEscape(entry.typeId)
		       << ",\"identified\":" << (entry.identified ? "true" : "false")
		       << ",\"quantity\":" << entry.quantity << '}';
	}
	output << ']';
}

void AppendPlayer(std::ostringstream &output, const Player &player)
{
	const Point position = player.position.tile;
	const auto inventory = ProjectInventory(player);
	output << "{\"position\":";
	AppendVec2(output, position);
	output << ",\"hp\":" << WholeResource(player._pHitPoints)
	       << ",\"hp_max\":" << WholeResource(player._pMaxHP)
	       << ",\"mana\":" << WholeResource(player._pMana)
	       << ",\"mana_max\":" << WholeResource(player._pMaxMana)
	       << ",\"level\":" << static_cast<unsigned>(player.getCharacterLevel())
	       << ",\"experience\":" << player._pExperience
	       << ",\"gold\":" << player._pGold
	       << ",\"potions\":" << CountPotions(player)
	       << ",\"class_id\":" << JsonEscape(ClassId(player._pClass))
	       << ",\"dungeon_level\":" << static_cast<unsigned>(currlevel)
	       << ",\"attributes\":{\"dexterity\":" << player._pDexterity
	       << ",\"magic\":" << player._pMagic
	       << ",\"strength\":" << player._pStrength
	       << ",\"vitality\":" << player._pVitality << "},\"inventory\":";
	AppendInventory(output, inventory);
	output << '}';
}

void AppendTiles(std::ostringstream &output, Point center)
{
	constexpr int TileRadius = 5;
	output << '[';
	bool first = true;
	for (int relativeY = -TileRadius; relativeY <= TileRadius; ++relativeY) {
		for (int relativeX = -TileRadius; relativeX <= TileRadius; ++relativeX) {
			const Point position { center.x + relativeX, center.y + relativeY };
			const bool inBounds = InDungeonBounds(position);
			const bool visible = inBounds && IsVisibleForObservation(position);
			const bool explored = inBounds && HasAnyOf(runtimeData.dFlags[position.x][position.y], DungeonFlag::Explored);
			const int terrainId = explored ? static_cast<int>(dPiece[position.x][position.y]) : -1;
			const bool walkable = explored && !TileHasAny(position, TileProperties::Solid);
			const bool occupied = visible
			    && (runtimeData.dPlayer[position.x][position.y] != 0 || runtimeData.dMonster[position.x][position.y] != 0
			        || runtimeData.dItem[position.x][position.y] != 0 || dObject[position.x][position.y] != 0);
			if (!first)
				output << ',';
			first = false;
			output << "{\"relative\":{\"x\":" << relativeX << ",\"y\":" << relativeY
			       << "},\"terrain_id\":" << terrainId
			       << ",\"walkable\":" << (walkable ? "true" : "false")
			       << ",\"visible\":" << (visible ? "true" : "false")
			       << ",\"explored\":" << (explored ? "true" : "false")
			       << ",\"occupied\":" << (occupied ? "true" : "false")
			       << ",\"hazard\":0.0}";
		}
	}
	output << ']';
}

void AppendVisibleMonsters(std::ostringstream &output, Point playerPosition)
{
	output << '[';
	bool first = true;
	for (std::size_t activeIndex = 0; activeIndex < *runtimeData.activeMonsterCount; ++activeIndex) {
		const unsigned monsterId = runtimeData.activeMonsters[activeIndex];
		const Monster &monster = runtimeData.monsters[monsterId];
		if (monster.isInvalid || monster.hasNoLife() || !InDungeonBounds(monster.position.tile)
		    || !IsVisibleForObservation(monster.position.tile))
			continue;
		if (!first)
			output << ',';
		first = false;
		const Point position = monster.position.tile;
		output << "{\"entity_id\":" << monsterId
		       << ",\"kind\":\"MONSTER\",\"position\":";
		AppendVec2(output, position);
		output << ",\"type_id\":\"MONSTER_LEVEL_TYPE_" << static_cast<unsigned>(monster.levelType)
		       << "\",\"hp\":" << WholeResource(monster.hitPoints)
		       << ",\"hp_max\":" << WholeResource(monster.maxHitPoints)
		       << ",\"hostile\":true,\"visible\":true,\"attributes\":{}}";
	}
	output << ']';
	(void)playerPosition;
}

void AppendActionCandidate(std::ostringstream &output, const SemanticCandidate &candidate)
{
	output << "{\"candidate_id\":" << candidate.candidateId
	       << ",\"kind\":\"MOVE_TO_TILE\""
	       << ",\"target_entity_id\":null,\"target_tile\":{\"x\":"
	       << candidate.targetTile.x << ",\"y\":" << candidate.targetTile.y << "}"
	       << ",\"inventory_slot\":null,\"equipment_slot\":null"
	       << ",\"belt_slot\":null,\"spell_id\":null"
	       << ",\"store_item_id\":null,\"stat_id\":null"
	       << ",\"label\":"
	       << JsonEscape("MOVE_TO_TILE:" + std::to_string(candidate.targetTile.x) + ":"
	           + std::to_string(candidate.targetTile.y))
	       << ",\"features\":[]}";
}

void AppendLegalActions(
	std::ostringstream &output,
	const Arguments &arguments,
	const std::vector<SemanticCandidate> &candidates)
{
	output << '[';
	if (arguments.mode == ProbeMode::Observation) {
		output << "{\"candidate_id\":0,\"kind\":\"WAIT\""
		       << ",\"target_entity_id\":null,\"target_tile\":null"
		       << ",\"inventory_slot\":null,\"equipment_slot\":null,\"belt_slot\":null"
		       << ",\"spell_id\":null,\"store_item_id\":null,\"stat_id\":null"
		       << ",\"label\":\"WAIT\",\"features\":[]}";
	} else {
		for (std::size_t index = 0; index < candidates.size(); ++index) {
			if (index != 0)
				output << ',';
			AppendActionCandidate(output, candidates[index]);
		}
	}
	output << ']';
}

std::string SerializeObservation(
	const Arguments &arguments,
	const std::vector<SemanticCandidate> &candidates,
	std::uint64_t stepId,
	std::uint64_t engineTick,
	std::string_view decisionReason,
	std::string_view recentEvent,
	std::string_view lifecycleEpisodeId = {})
{
	if (MyPlayer == nullptr)
		throw ProbeFailure(ProbeErrorCode::ObservationContractFailed, "local player is unavailable");
	std::ostringstream output;
	const Point playerPosition = MyPlayer->position.tile;
	const std::string episodeId = lifecycleEpisodeId.empty()
	    ? "devilutionx-" + std::string(arguments.mode == ProbeMode::M03 ? "m03-" : "m02-")
	          + std::to_string(arguments.seed)
	    : std::string(lifecycleEpisodeId);
	output << "{\"schema_version\":\"dxai.observation.v1\""
	       << ",\"episode_id\":" << JsonEscape(episodeId)
	       << ",\"task_id\":" << JsonEscape(arguments.task)
	       << ",\"seed\":" << arguments.seed
	       << ",\"step_id\":" << stepId << ",\"engine_tick\":" << engineTick
	       << ",\"decision_reason\":" << JsonEscape(decisionReason) << ",\"player\":";
	AppendPlayer(output, *MyPlayer);
	output << ",\"local_tiles\":";
	AppendTiles(output, playerPosition);
	output << ",\"entities\":";
	AppendVisibleMonsters(output, playerPosition);
	output << ",\"legal_actions\":";
	AppendLegalActions(output, arguments, candidates);
	output << ",\"recent_events\":[" << JsonEscape(recentEvent) << "]}";
	return output.str();
}

std::string SerializeFirstStep(
	const Arguments &arguments,
	const std::string &initialObservation,
	const SemanticCandidate &selectedCandidate,
	const std::string &nextObservation,
	const std::string &candidateSetSha256,
	const std::string &nextCandidateSetSha256,
	bool requestedTargetReached)
{
	std::ostringstream output;
	output << "{\"schema_version\":\"dxai.probe.step.v1\""
	       << ",\"episode_id\":\"devilutionx-m03-" << arguments.seed << '"'
	       << ",\"task_id\":" << JsonEscape(arguments.task)
	       << ",\"seed\":" << arguments.seed
	       << ",\"step_id\":0"
	       << ",\"candidate_set_sha256\":" << JsonEscape(candidateSetSha256)
	       << ",\"next_candidate_set_sha256\":" << JsonEscape(nextCandidateSetSha256)
	       << ",\"observation\":" << initialObservation
	       << ",\"action\":";
	AppendActionCandidate(output, selectedCandidate);
	output << ",\"next_observation\":" << nextObservation
	       << ",\"requested_target_reached\":"
	       << (requestedTargetReached ? "true" : "false") << '}';
	return output.str();
}

void AdvancePinnedGameLogicBody()
{
	// The pinned game_loop(false) calls multi_handle_delta(), then GameLogic(),
	// then ClearLastSentPlayerCmd(). NetInit is intentionally outside M0.3, so
	// the no-network fixture cannot safely call game_loop(false): its aggregate
	// network prelude dereferences state that NetInit would create. This single
	// adapter function therefore invokes the exported body calls in the exact
	// order of GameLogic() for the already-controlled, non-menu fixture. Input
	// has already been represented by the native MakePlrPath call; no synthetic
	// SDL input is introduced here.
	if (*LoadExportedData<bool>("?gbProcessPlayers@devilution@@3_NA"))
		ProcessPlayers();
	if (leveltype != DTYPE_TOWN) {
		ProcessMonsters();
		ProcessObjects();
		ProcessMissiles();
		ProcessItems();
		ProcessLightList();
		ProcessVisionList();
	} else {
		ProcessTowners();
		ProcessItems();
		ProcessMissiles();
	}
	sound_update();
	CheckTriggers();
	CheckQuests();
	RedrawViewport();
	pfile_update(false);
	plrctrls_after_game_logic();
	ClearLastSentPlayerCmd();
}

std::uint64_t AdvanceUntilDecisionBoundary()
{
	std::uint64_t logicTicks = 0;
	for (; logicTicks < ActionResolutionSafetyBound; ++logicTicks) {
		AdvancePinnedGameLogicBody();
		if (IsControllableDecisionBoundary()) {
			++logicTicks;
			break;
		}
	}
	if (!IsControllableDecisionBoundary()) {
		throw ProbeFailure(
		    ProbeErrorCode::ActionResolutionFailed,
		    "native action did not return to a controllable decision boundary within the safety bound");
	}
	return logicTicks;
}

void ExecuteMoveCandidate(const SemanticCandidate &candidate)
{
	ClrPlrPath(*MyPlayer);
	MakePlrPath(*MyPlayer, candidate.targetTile, true);
	*LoadExportedData<PlayerActionType>("?LastPlayerAction@devilution@@3W4PlayerActionType@1@A") = PlayerActionType::Walk;
	if (MyPlayer->walkpath[0] == WALK_NONE) {
		throw ProbeFailure(
		    ProbeErrorCode::ActionResolutionFailed,
		    "native MOVE_TO_TILE candidate did not queue a player path");
	}
}

std::string RunM03(const Arguments &arguments)
{
	*LoadExportedData<bool>("?gbRunGame@devilution@@3_NA") = true;
	*LoadExportedData<bool>("?gbProcessPlayers@devilution@@3_NA") = true;
	PauseMode = 0;
	if (!IsControllableDecisionBoundary())
		throw ProbeFailure(ProbeErrorCode::EngineInitializationFailed, "M0.3 state is not controllable");

	const std::vector<SemanticCandidate> issuedCandidates = GenerateMoveCandidates();
	if (issuedCandidates.empty()) {
		throw ProbeFailure(
		    ProbeErrorCode::NoSupportedCandidates,
		    "no supported visible adjacent MOVE_TO_TILE candidate at decision boundary");
	}
	const std::string issuedKey = CanonicalCandidateSetKey(issuedCandidates);
	const std::string issuedHash = Sha256(issuedKey);
	const std::string episodeId = "devilutionx-m03-" + std::to_string(arguments.seed);
	const std::string initialObservation = SerializeObservation(
	    arguments,
	    issuedCandidates,
	    0,
	    0,
	    "PLAYER_READY",
	    "M03_DECISION_BOUNDARY");

	if (!arguments.candidateId.has_value())
		return initialObservation;

	if (!arguments.expectedEpisodeId.has_value() || *arguments.expectedEpisodeId != episodeId)
		throw ProbeFailure(ProbeErrorCode::StaleCandidate, "candidate episode_id is stale");
	if (!arguments.expectedStepId.has_value() || *arguments.expectedStepId != 0)
		throw ProbeFailure(ProbeErrorCode::StaleCandidate, "candidate step_id is stale");
	if (!arguments.expectedCandidateSetSha256.has_value()
	    || *arguments.expectedCandidateSetSha256 != issuedHash)
		throw ProbeFailure(ProbeErrorCode::StateMismatch, "issued candidate set differs from regenerated state");

	const std::vector<SemanticCandidate> regeneratedCandidates = GenerateMoveCandidates();
	if (CanonicalCandidateSetKey(regeneratedCandidates) != issuedKey
	    || Sha256(CanonicalCandidateSetKey(regeneratedCandidates)) != issuedHash) {
		throw ProbeFailure(ProbeErrorCode::StateMismatch, "candidate set changed before execution");
	}

	if (*arguments.candidateId < 0
	    || static_cast<std::uint64_t>(*arguments.candidateId) >= issuedCandidates.size()) {
		throw ProbeFailure(ProbeErrorCode::CandidateRejected, "candidate_id is not legal for this decision");
	}
	const SemanticCandidate selectedCandidate = issuedCandidates[static_cast<std::size_t>(*arguments.candidateId)];

	ExecuteMoveCandidate(selectedCandidate);

	// game_loop(false) is the pinned upstream aggregate semantic tick: it handles
	// the network turn, calls the engine's GameLogic body, and clears the same
	// per-tick command throttle. Its NetInit-dependent network prelude is outside
	// this fixture, so AdvancePinnedGameLogicBody is the centralized lower-level
	// equivalent for the no-network controlled slice.
	const std::uint64_t logicTicks = AdvanceUntilDecisionBoundary();

	const bool requestedTargetReached = MyPlayer->position.tile == selectedCandidate.targetTile;
	const std::vector<SemanticCandidate> nextCandidates = GenerateMoveCandidates();
	if (nextCandidates.empty()) {
		throw ProbeFailure(
		    ProbeErrorCode::NoSupportedCandidates,
		    "next decision boundary has no supported visible adjacent MOVE_TO_TILE candidate");
	}
	const std::string nextKey = CanonicalCandidateSetKey(nextCandidates);
	const std::string nextHash = Sha256(nextKey);
	const std::string nextObservation = SerializeObservation(
	    arguments,
	    nextCandidates,
	    1,
	    logicTicks,
	    "PLAYER_READY",
	    "M03_ACTION_RESOLVED");

	return SerializeFirstStep(
	    arguments,
	    initialObservation,
	    selectedCandidate,
	    nextObservation,
	    issuedHash,
	    nextHash,
	    requestedTargetReached);
}

const char *ProcessStateName(dxai_bridge::ProcessState state)
{
	switch (state) {
	case dxai_bridge::ProcessState::Ready:
		return "READY";
	case dxai_bridge::ProcessState::EpisodeActive:
		return "EPISODE_ACTIVE";
	case dxai_bridge::ProcessState::Faulted:
		return "FAULTED";
	}
	return "FAULTED";
}

std::uint64_t ProcessId()
{
#if defined(_WIN32)
	return static_cast<std::uint64_t>(GetCurrentProcessId());
#else
	return 0;
#endif
}

std::string MakeLifecycleEpisodeId()
{
	static std::uint64_t counter = 0;
	++counter;
	std::uint64_t nonce = static_cast<std::uint64_t>(
	    std::chrono::high_resolution_clock::now().time_since_epoch().count());
#if defined(_WIN32)
	std::uint64_t systemNonce = 0;
	if (BCryptGenRandom(
		    nullptr,
		    reinterpret_cast<PUCHAR>(&systemNonce),
		    static_cast<ULONG>(sizeof(systemNonce)),
		    BCRYPT_USE_SYSTEM_PREFERRED_RNG)
	    == 0) {
		nonce = systemNonce;
	}
#endif
	std::ostringstream result;
	result << "dxai-m04-" << ProcessId() << '-' << counter << '-' << std::hex << nonce;
	return result.str();
}

std::string SerializeProcessError(
    std::optional<std::uint64_t> requestId,
    dxai_bridge::ProcessState state,
    dxai_bridge::ProcessErrorCode code,
    std::string_view message)
{
	std::ostringstream output;
	output << "{\"type\":\"error_response\",\"protocol_version\":"
	       << JsonEscape(dxai_bridge::kProcessProtocolVersion)
	       << ",\"request_id\":";
	if (requestId.has_value())
		output << *requestId;
	else
		output << "null";
	output << ",\"process_state\":" << JsonEscape(ProcessStateName(state))
	       << ",\"error_code\":" << JsonEscape(dxai_bridge::ProcessErrorCodeName(code))
	       << ",\"error_message\":" << JsonEscape(message) << '}';
	return output.str();
}

std::string SerializeHealthResponse(std::uint64_t requestId, dxai_bridge::ProcessState state)
{
	std::ostringstream output;
	output << "{\"type\":\"health_response\",\"protocol_version\":"
	       << JsonEscape(dxai_bridge::kProcessProtocolVersion)
       << ",\"request_id\":" << requestId
       << ",\"process_state\":" << JsonEscape(ProcessStateName(state))
       << ",\"adapter_revision\":\"m0.4\""
       << ",\"devilutionx_revision\":\"07385842840437cc9a785b195f5b40b121eaeb1c\""
       << ",\"build_fingerprint\":\"dxai-ml-diablo-m0.4\""
       << ",\"observation_version\":\"dxai.observation.v1\""
       << ",\"action_version\":\"dxai.action.v1\""
       << ",\"supported_task_versions\":[\"combat.single_melee.v0\"]"
       << ",\"supported_features\":[\"MOVE_TO_TILE\",\"cold_reset\",\"request_idempotency\"]"
       << ",\"pid\":" << ProcessId() << '}';
	return output.str();
}

std::string SerializeResetResponse(
    std::uint64_t requestId,
    std::string_view episodeId,
    std::string_view observation,
    std::string_view candidateSetSha256)
{
	std::ostringstream output;
	output << "{\"type\":\"reset_response\",\"protocol_version\":"
       << JsonEscape(dxai_bridge::kProcessProtocolVersion)
       << ",\"request_id\":" << requestId
       << ",\"process_state\":\"EPISODE_ACTIVE\""
       << ",\"episode_id\":" << JsonEscape(episodeId)
       << ",\"observation\":" << observation
       << ",\"candidate_set_sha256\":" << JsonEscape(candidateSetSha256) << '}';
	return output.str();
}

std::string SerializePersistentStepResponse(
    std::uint64_t requestId,
    std::string_view episodeId,
    std::uint64_t previousStepId,
    const SemanticCandidate &appliedCandidate,
    std::string_view previousCandidateSetSha256,
    std::string_view observation,
    std::string_view candidateSetSha256)
{
	std::ostringstream output;
	output << "{\"type\":\"step_response\",\"protocol_version\":"
       << JsonEscape(dxai_bridge::kProcessProtocolVersion)
       << ",\"request_id\":" << requestId
       << ",\"process_state\":\"EPISODE_ACTIVE\""
       << ",\"episode_id\":" << JsonEscape(episodeId)
       << ",\"previous_step_id\":" << previousStepId
       << ",\"applied_action\":";
	AppendActionCandidate(output, appliedCandidate);
	output << ",\"previous_candidate_set_sha256\":"
       << JsonEscape(previousCandidateSetSha256)
       << ",\"observation\":" << observation
       << ",\"candidate_set_sha256\":" << JsonEscape(candidateSetSha256) << '}';
	return output.str();
}

dxai_bridge::ProcessErrorCode ProcessErrorFromProbe(ProbeErrorCode code)
{
	switch (code) {
	case ProbeErrorCode::InvalidArgument:
		return dxai_bridge::ProcessErrorCode::InvalidField;
	case ProbeErrorCode::AssetDataUnavailable:
		return dxai_bridge::ProcessErrorCode::AssetDataUnavailable;
	case ProbeErrorCode::EngineInitializationFailed:
		return dxai_bridge::ProcessErrorCode::EngineInitializationFailed;
	case ProbeErrorCode::ObservationContractFailed:
		return dxai_bridge::ProcessErrorCode::ObservationContractFailed;
	case ProbeErrorCode::CandidateRejected:
		return dxai_bridge::ProcessErrorCode::CandidateRejected;
	case ProbeErrorCode::StateMismatch:
		return dxai_bridge::ProcessErrorCode::StateMismatch;
	case ProbeErrorCode::StaleCandidate:
		return dxai_bridge::ProcessErrorCode::StaleCandidate;
	case ProbeErrorCode::NoSupportedCandidates:
		return dxai_bridge::ProcessErrorCode::NoSupportedCandidates;
	case ProbeErrorCode::ActionResolutionFailed:
		return dxai_bridge::ProcessErrorCode::ActionResolutionFailed;
	case ProbeErrorCode::Internal:
		return dxai_bridge::ProcessErrorCode::Internal;
	}
	return dxai_bridge::ProcessErrorCode::Internal;
}

class EnvironmentWorker final {
public:
	explicit EnvironmentWorker(const Arguments &arguments)
		: arguments_(arguments)
	{
	}

	int Run()
	{
		for (;;) {
			std::string line;
			dxai_bridge::ProcessProtocolError lineError;
			const auto readResult = dxai_bridge::ReadProcessLine(std::cin, line, lineError);
			if (readResult == dxai_bridge::ReadLineResult::Eof)
				return 0;
			if (readResult == dxai_bridge::ReadLineResult::Error) {
				lifecycle_.Fault();
				WriteProtocolResponse(SerializeProcessError(
				    std::nullopt,
				    lifecycle_.state(),
				    lineError.code,
				    lineError.message));
				continue;
			}

			dxai_bridge::ProcessRequest request;
			dxai_bridge::ProcessProtocolError parseError;
			if (!dxai_bridge::ParseProcessRequest(line, request, parseError)) {
				lifecycle_.Fault();
				WriteProtocolResponse(SerializeProcessError(
				    std::nullopt,
				    lifecycle_.state(),
				    parseError.code,
				    parseError.message));
				continue;
			}

			const std::string fingerprint = request.Fingerprint();
			std::string replay;
			dxai_bridge::ProcessProtocolError cacheError;
			if (requestCache_.ReplayOrMiss(request.requestId, fingerprint, replay, cacheError)) {
				WriteProtocolResponse(replay);
				continue;
			}
			if (!cacheError.message.empty()) {
				WriteProtocolResponse(SerializeProcessError(
				    request.requestId,
				    lifecycle_.state(),
				    cacheError.code,
				    cacheError.message));
				continue;
			}

			std::string response;
			try {
				response = HandleRequest(request);
			} catch (const ProbeFailure &failure) {
				lifecycle_.Fault();
				response = SerializeProcessError(
				    request.requestId,
				    lifecycle_.state(),
				    ProcessErrorFromProbe(failure.code()),
				    failure.what());
			} catch (const std::exception &exception) {
				lifecycle_.Fault();
				response = SerializeProcessError(
				    request.requestId,
				    lifecycle_.state(),
				    dxai_bridge::ProcessErrorCode::Internal,
				    exception.what());
			}

			dxai_bridge::ProcessProtocolError rememberError;
			if (!requestCache_.Remember(request.requestId, fingerprint, response, rememberError)) {
				lifecycle_.Fault();
				response = SerializeProcessError(
				    request.requestId,
				    lifecycle_.state(),
				    rememberError.code,
				    rememberError.message);
			}
			WriteProtocolResponse(response);
		}
	}

private:
	std::string HandleRequest(const dxai_bridge::ProcessRequest &request)
	{
		switch (request.type) {
		case dxai_bridge::ProcessRequestType::Health:
			return SerializeHealthResponse(request.requestId, lifecycle_.state());
		case dxai_bridge::ProcessRequestType::Reset:
			return HandleReset(request);
		case dxai_bridge::ProcessRequestType::Step:
			return HandleStep(request);
		}
		return SerializeProcessError(
		    request.requestId,
		    lifecycle_.state(),
		    dxai_bridge::ProcessErrorCode::UnknownMessageType,
		    "unsupported process request type");
	}

	std::string HandleReset(const dxai_bridge::ProcessRequest &request)
	{
		if (lifecycle_.state() != dxai_bridge::ProcessState::Ready)
			return SerializeProcessError(
			    request.requestId,
			    lifecycle_.state(),
			    dxai_bridge::ProcessErrorCode::InvalidState,
			    "worker accepts exactly one Reset");
		if (request.taskId != "combat.single_melee.v0")
			return SerializeProcessError(
			    request.requestId,
			    lifecycle_.state(),
			    dxai_bridge::ProcessErrorCode::InvalidField,
			    "unsupported process task");

		activeArguments_ = arguments_;
		activeArguments_.mode = ProbeMode::EnvironmentStdio;
		activeArguments_.seed = request.seed;
		activeArguments_.task = request.taskId;
		InitializeEngine(activeArguments_);
		*LoadExportedData<bool>("?gbRunGame@devilution@@3_NA") = true;
		*LoadExportedData<bool>("?gbProcessPlayers@devilution@@3_NA") = true;
		PauseMode = 0;
		if (!IsControllableDecisionBoundary())
			throw ProbeFailure(ProbeErrorCode::EngineInitializationFailed, "environment reset is not controllable");

		currentCandidates_ = GenerateMoveCandidates();
		if (currentCandidates_.empty())
			throw ProbeFailure(
			    ProbeErrorCode::NoSupportedCandidates,
			    "reset boundary has no supported visible adjacent MOVE_TO_TILE candidate");
		currentCandidateKey_ = CanonicalCandidateSetKey(currentCandidates_);
		currentCandidateSetSha256_ = Sha256(currentCandidateKey_);
		episodeId_ = MakeLifecycleEpisodeId();
		engineTick_ = 0;
		dxai_bridge::ProcessProtocolError lifecycleError;
		if (!lifecycle_.BeginEpisode(episodeId_, currentCandidateSetSha256_, lifecycleError))
			throw std::runtime_error(lifecycleError.message);
		const std::string observation = SerializeObservation(
		    activeArguments_,
		    currentCandidates_,
		    lifecycle_.stepId(),
		    engineTick_,
		    "PLAYER_READY",
		    "EPISODE_RESET",
		    episodeId_);
		return SerializeResetResponse(
		    request.requestId,
		    episodeId_,
		    observation,
		    currentCandidateSetSha256_);
	}

	std::string HandleStep(const dxai_bridge::ProcessRequest &request)
	{
		dxai_bridge::ProcessProtocolError lifecycleError;
		if (!lifecycle_.ValidateStep(
		        request.episodeId,
		        request.expectedStepId,
		        request.candidateSetSha256,
		        lifecycleError))
			return SerializeProcessError(
			    request.requestId,
			    lifecycle_.state(),
			    lifecycleError.code,
			    lifecycleError.message);

		const std::vector<SemanticCandidate> regeneratedCandidates = GenerateMoveCandidates();
		const std::string regeneratedKey = CanonicalCandidateSetKey(regeneratedCandidates);
		if (regeneratedKey != currentCandidateKey_ || Sha256(regeneratedKey) != currentCandidateSetSha256_)
			return SerializeProcessError(
			    request.requestId,
			    lifecycle_.state(),
			    dxai_bridge::ProcessErrorCode::StateMismatch,
			    "candidate set changed before execution");
		if (request.candidateId >= currentCandidates_.size())
			return SerializeProcessError(
			    request.requestId,
			    lifecycle_.state(),
			    dxai_bridge::ProcessErrorCode::InvalidCandidate,
			    "candidate_id is not legal for this decision");

		const std::uint64_t previousStepId = lifecycle_.stepId();
		const std::string previousCandidateSetSha256 = currentCandidateSetSha256_;
		const SemanticCandidate selectedCandidate = currentCandidates_[request.candidateId];
		ExecuteMoveCandidate(selectedCandidate);
		const std::uint64_t logicTicks = AdvanceUntilDecisionBoundary();
		engineTick_ += logicTicks;

		std::vector<SemanticCandidate> nextCandidates = GenerateMoveCandidates();
		if (nextCandidates.empty())
			throw ProbeFailure(
			    ProbeErrorCode::NoSupportedCandidates,
			    "next decision boundary has no supported visible adjacent MOVE_TO_TILE candidate");
		const std::string nextKey = CanonicalCandidateSetKey(nextCandidates);
		const std::string nextHash = Sha256(nextKey);
		const std::uint64_t nextStepId = previousStepId + 1;
		const std::string nextObservation = SerializeObservation(
		    activeArguments_,
		    nextCandidates,
		    nextStepId,
		    engineTick_,
		    "PLAYER_READY",
		    "M04_ACTION_RESOLVED",
		    episodeId_);
		dxai_bridge::ProcessProtocolError completionError;
		if (!lifecycle_.CompleteStep(episodeId_, nextStepId, nextHash, completionError))
			throw std::runtime_error(completionError.message);
		currentCandidates_ = std::move(nextCandidates);
		currentCandidateKey_ = nextKey;
		currentCandidateSetSha256_ = nextHash;
		return SerializePersistentStepResponse(
		    request.requestId,
		    episodeId_,
		    previousStepId,
		    selectedCandidate,
		    previousCandidateSetSha256,
		    nextObservation,
		    currentCandidateSetSha256_);
	}

	static void WriteProtocolResponse(std::string_view response)
	{
		std::cout << response << '\n' << std::flush;
	}

	Arguments arguments_;
	Arguments activeArguments_;
	dxai_bridge::ProcessLifecycle lifecycle_;
	dxai_bridge::RequestCache requestCache_;
	std::string episodeId_;
	std::uint64_t engineTick_ {};
	std::vector<SemanticCandidate> currentCandidates_;
	std::string currentCandidateKey_;
	std::string currentCandidateSetSha256_;
};

void WriteError(const ProbeFailure &failure)
{
	std::cerr << "{\"error_code\":" << JsonEscape(ErrorCodeName(failure.code()))
	          << ",\"error_message\":" << JsonEscape(failure.what()) << "}\n";
}

} // namespace

int main(int argc, char **argv)
{
	try {
		const Arguments arguments = ParseArguments(argc, argv);
		if (arguments.mode == ProbeMode::EnvironmentStdio) {
			EnvironmentWorker worker(arguments);
			return worker.Run();
		}
		InitializeEngine(arguments);
		if (arguments.mode == ProbeMode::M03) {
			std::cout << RunM03(arguments) << '\n';
		} else {
			std::cout << SerializeObservation(
			    arguments,
			    {},
			    0,
			    0,
			    "OBSERVATION_PROBE",
			    "OBSERVATION_PROBE")
			          << '\n';
		}
		return 0;
	} catch (const ProbeFailure &failure) {
		WriteError(failure);
		return 2;
	} catch (const std::exception &error) {
		WriteError(ProbeFailure(ProbeErrorCode::Internal, error.what()));
		return 3;
	}
}
