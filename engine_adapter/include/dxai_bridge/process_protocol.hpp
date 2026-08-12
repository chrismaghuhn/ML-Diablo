#pragma once

#include <cstddef>
#include <cstdint>
#include <deque>
#include <istream>
#include <string>
#include <string_view>
#include <unordered_map>

namespace dxai_bridge {

inline constexpr const char *kProcessProtocolVersion = "dxai.process.v1";
inline constexpr std::size_t kMaxProcessFrameBytes = 1U * 1024U * 1024U;
inline constexpr std::size_t kProcessRequestCacheEntries = 128U;

enum class ProcessErrorCode : std::uint8_t {
	MalformedUtf8,
	MalformedJson,
	OversizedFrame,
	UnknownMessageType,
	UnknownField,
	MissingField,
	InvalidField,
	ProtocolVersionMismatch,
	RequestIdReuse,
	RequestIdExpired,
	InvalidState,
	EngineFaulted,
	StaleEpisode,
	StaleStep,
	StateMismatch,
	InvalidCandidate,
	NoSupportedCandidates,
	EngineFault,
	AssetDataUnavailable,
	EngineInitializationFailed,
	ObservationContractFailed,
	CandidateRejected,
	ActionResolutionFailed,
	StaleCandidate,
	Internal,
};

[[nodiscard]] const char *ProcessErrorCodeName(ProcessErrorCode code);

struct ProcessProtocolError {
	ProcessErrorCode code { ProcessErrorCode::Internal };
	std::string message;
};

enum class ReadLineResult : std::uint8_t {
	Line,
	Eof,
	Error,
};

[[nodiscard]] ReadLineResult ReadProcessLine(
	std::istream &input,
	std::string &line,
	ProcessProtocolError &error);

enum class ProcessRequestType : std::uint8_t {
	Health,
	Reset,
	Step,
};

struct ProcessRequest {
	ProcessRequestType type { ProcessRequestType::Health };
	std::uint64_t requestId {};
	std::uint64_t seed {};
	std::string taskId;
	std::string episodeId;
	std::uint64_t expectedStepId {};
	std::uint32_t candidateId {};
	std::string candidateSetSha256;

	[[nodiscard]] std::string Fingerprint() const;
};

[[nodiscard]] bool ParseProcessRequest(
	std::string_view line,
	ProcessRequest &request,
	ProcessProtocolError &error);

class RequestCache {
public:
	explicit RequestCache(std::size_t maxEntries = kProcessRequestCacheEntries);

	[[nodiscard]] bool ReplayOrMiss(
		std::uint64_t requestId,
		std::string_view fingerprint,
		std::string &response,
		ProcessProtocolError &error) const;

	[[nodiscard]] bool Remember(
		std::uint64_t requestId,
		std::string_view fingerprint,
		std::string_view response,
		ProcessProtocolError &error);

	[[nodiscard]] std::size_t size() const
	{
		return entries_.size();
	}

private:
	struct Entry {
		std::string fingerprint;
		std::string response;
	};

	std::size_t maxEntries_;
	std::uint64_t highestRequestId_ {};
	bool hasHighestRequestId_ { false };
	std::deque<std::uint64_t> insertionOrder_;
	std::unordered_map<std::uint64_t, Entry> entries_;
};

enum class ProcessState : std::uint8_t {
	Ready,
	EpisodeActive,
	Faulted,
};

class ProcessLifecycle {
public:
	[[nodiscard]] ProcessState state() const
	{
		return state_;
	}

	[[nodiscard]] const std::string &episodeId() const
	{
		return episodeId_;
	}

	[[nodiscard]] std::uint64_t stepId() const
	{
		return stepId_;
	}

	[[nodiscard]] const std::string &candidateSetSha256() const
	{
		return candidateSetSha256_;
	}

	[[nodiscard]] bool BeginEpisode(
		std::string_view episodeId,
		std::string_view candidateSetSha256,
		ProcessProtocolError &error);

	[[nodiscard]] bool ValidateStep(
		std::string_view episodeId,
		std::uint64_t expectedStepId,
		std::string_view candidateSetSha256,
		ProcessProtocolError &error) const;

	[[nodiscard]] bool CompleteStep(
		std::string_view episodeId,
		std::uint64_t nextStepId,
		std::string_view candidateSetSha256,
		ProcessProtocolError &error);

	void Fault()
	{
		state_ = ProcessState::Faulted;
	}

private:
	ProcessState state_ { ProcessState::Ready };
	std::string episodeId_;
	std::uint64_t stepId_ {};
	std::string candidateSetSha256_;
};

} // namespace dxai_bridge
