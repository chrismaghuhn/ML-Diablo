#include <algorithm>
#include <cstdint>
#include <filesystem>
#include <iomanip>
#include <iostream>
#include <limits>
#include <expected>
#include <sstream>
#include <stdexcept>
#include <string>
#include <string_view>
#include <vector>

#if defined(_WIN32)
#define NOMINMAX
#include <windows.h>
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

namespace {

using namespace devilution;

enum class ProbeErrorCode {
	InvalidArgument,
	AssetDataUnavailable,
	EngineInitializationFailed,
	ObservationContractFailed,
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

Arguments ParseArguments(int argc, char **argv)
{
	Arguments arguments;
	for (int index = 1; index < argc; ++index) {
		const std::string_view option = argv[index];
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
		} else {
			throw ProbeFailure(ProbeErrorCode::InvalidArgument, "unknown option " + std::string(option));
		}
	}
	if (arguments.assets.empty() || arguments.coreAssets.empty() || arguments.task.empty())
		throw ProbeFailure(ProbeErrorCode::InvalidArgument, "--assets, --core-assets and --task are required");
	if (arguments.task != "combat.single_melee.v0")
		throw ProbeFailure(ProbeErrorCode::InvalidArgument, "unsupported M0.2 task");
	if (arguments.runtimeRoot.empty())
		arguments.runtimeRoot = std::filesystem::temp_directory_path() / "dxai-m02-probe";
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

std::string SerializeObservation(const Arguments &arguments)
{
	if (MyPlayer == nullptr)
		throw ProbeFailure(ProbeErrorCode::ObservationContractFailed, "local player is unavailable");
	std::ostringstream output;
	const Point playerPosition = MyPlayer->position.tile;
	output << "{\"schema_version\":\"dxai.observation.v1\""
	       << ",\"episode_id\":\"devilutionx-m02-" << arguments.seed << '"'
	       << ",\"task_id\":" << JsonEscape(arguments.task)
	       << ",\"seed\":" << arguments.seed
	       << ",\"step_id\":0,\"engine_tick\":0"
	       << ",\"decision_reason\":\"OBSERVATION_PROBE\",\"player\":";
	AppendPlayer(output, *MyPlayer);
	output << ",\"local_tiles\":";
	AppendTiles(output, playerPosition);
	output << ",\"entities\":";
	AppendVisibleMonsters(output, playerPosition);
	output << ",\"legal_actions\":[{\"candidate_id\":0,\"kind\":\"WAIT\""
	       << ",\"target_entity_id\":null,\"target_tile\":null"
	       << ",\"inventory_slot\":null,\"equipment_slot\":null,\"belt_slot\":null"
	       << ",\"spell_id\":null,\"store_item_id\":null,\"stat_id\":null"
	       << ",\"label\":\"WAIT\",\"features\":[]}]"
	       << ",\"recent_events\":[\"OBSERVATION_PROBE\"]}";
	return output.str();
}

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
		InitializeEngine(arguments);
		std::cout << SerializeObservation(arguments) << '\n';
		return 0;
	} catch (const ProbeFailure &failure) {
		WriteError(failure);
		return 2;
	} catch (const std::exception &error) {
		WriteError(ProbeFailure(ProbeErrorCode::Internal, error.what()));
		return 3;
	}
}
