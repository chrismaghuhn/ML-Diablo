#include "dxai_bridge/process_protocol.hpp"

#include <algorithm>
#include <charconv>
#include <cctype>
#include <limits>
#include <map>
#include <sstream>
#include <utility>

namespace dxai_bridge {
namespace {

struct JsonScalar {
	enum class Kind : std::uint8_t {
		String,
		Unsigned,
	};

	Kind kind { Kind::String };
	std::string stringValue;
	std::uint64_t unsignedValue {};
};

bool IsValidUtf8(std::string_view value)
{
	for (std::size_t index = 0; index < value.size();) {
		const auto first = static_cast<unsigned char>(value[index]);
		if (first <= 0x7F) {
			++index;
			continue;
		}
		if (first >= 0xC2 && first <= 0xDF) {
			if (index + 1 >= value.size())
				return false;
			const auto second = static_cast<unsigned char>(value[index + 1]);
			if ((second & 0xC0) != 0x80)
				return false;
			index += 2;
			continue;
		}
		if (first == 0xE0) {
			if (index + 2 >= value.size())
				return false;
			const auto second = static_cast<unsigned char>(value[index + 1]);
			const auto third = static_cast<unsigned char>(value[index + 2]);
			if (second < 0xA0 || second > 0xBF || (third & 0xC0) != 0x80)
				return false;
			index += 3;
			continue;
		}
		if ((first >= 0xE1 && first <= 0xEC) || (first >= 0xEE && first <= 0xEF)) {
			if (index + 2 >= value.size())
				return false;
			const auto second = static_cast<unsigned char>(value[index + 1]);
			const auto third = static_cast<unsigned char>(value[index + 2]);
			if ((second & 0xC0) != 0x80 || (third & 0xC0) != 0x80)
				return false;
			index += 3;
			continue;
		}
		if (first == 0xED) {
			if (index + 2 >= value.size())
				return false;
			const auto second = static_cast<unsigned char>(value[index + 1]);
			const auto third = static_cast<unsigned char>(value[index + 2]);
			if (second < 0x80 || second > 0x9F || (third & 0xC0) != 0x80)
				return false;
			index += 3;
			continue;
		}
		if (first == 0xF0) {
			if (index + 3 >= value.size())
				return false;
			const auto second = static_cast<unsigned char>(value[index + 1]);
			const auto third = static_cast<unsigned char>(value[index + 2]);
			const auto fourth = static_cast<unsigned char>(value[index + 3]);
			if (second < 0x90 || second > 0xBF || (third & 0xC0) != 0x80
			    || (fourth & 0xC0) != 0x80)
				return false;
			index += 4;
			continue;
		}
		if (first >= 0xF1 && first <= 0xF3) {
			if (index + 3 >= value.size())
				return false;
			const auto second = static_cast<unsigned char>(value[index + 1]);
			const auto third = static_cast<unsigned char>(value[index + 2]);
			const auto fourth = static_cast<unsigned char>(value[index + 3]);
			if ((second & 0xC0) != 0x80 || (third & 0xC0) != 0x80
			    || (fourth & 0xC0) != 0x80)
				return false;
			index += 4;
			continue;
		}
		if (first == 0xF4) {
			if (index + 3 >= value.size())
				return false;
			const auto second = static_cast<unsigned char>(value[index + 1]);
			const auto third = static_cast<unsigned char>(value[index + 2]);
			const auto fourth = static_cast<unsigned char>(value[index + 3]);
			if (second < 0x80 || second > 0x8F || (third & 0xC0) != 0x80
			    || (fourth & 0xC0) != 0x80)
				return false;
			index += 4;
			continue;
		}
		return false;
	}
	return true;
}

class JsonReader {
public:
	explicit JsonReader(std::string_view input)
		: input_(input)
	{
	}

	bool ParseObject(std::map<std::string, JsonScalar> &fields, ProcessProtocolError &error)
	{
		SkipWhitespace();
		if (!Consume('{'))
			return Fail(error, ProcessErrorCode::MalformedJson, "request must start with an object");
		SkipWhitespace();
		if (Consume('}'))
			return true;
		while (position_ < input_.size()) {
			std::string key;
			if (!ParseString(key, error))
				return false;
			SkipWhitespace();
			if (!Consume(':'))
				return Fail(error, ProcessErrorCode::MalformedJson, "request object requires a colon");
			JsonScalar value;
			if (!ParseScalar(value, error))
				return false;
			if (!fields.emplace(std::move(key), std::move(value)).second)
				return Fail(error, ProcessErrorCode::MalformedJson, "request contains a duplicate field");
			SkipWhitespace();
			if (Consume('}'))
				return true;
			if (!Consume(','))
				return Fail(error, ProcessErrorCode::MalformedJson, "request object requires a comma");
			SkipWhitespace();
		}
		return Fail(error, ProcessErrorCode::MalformedJson, "request object is incomplete");
	}

	bool AtEnd()
	{
		SkipWhitespace();
		return position_ == input_.size();
	}

private:
	template <typename T>
	static bool Fail(ProcessProtocolError &error, ProcessErrorCode code, T &&message)
	{
		error.code = code;
		error.message = std::forward<T>(message);
		return false;
	}

	void SkipWhitespace()
	{
		while (position_ < input_.size()
		       && (input_[position_] == ' ' || input_[position_] == '\t'
		           || input_[position_] == '\r' || input_[position_] == '\n')) {
			++position_;
		}
	}

	bool Consume(char expected)
	{
		if (position_ >= input_.size() || input_[position_] != expected)
			return false;
		++position_;
		return true;
	}

	bool ParseScalar(JsonScalar &value, ProcessProtocolError &error)
	{
		if (position_ >= input_.size())
			return Fail(error, ProcessErrorCode::MalformedJson, "request value is missing");
		if (input_[position_] == '"') {
			value.kind = JsonScalar::Kind::String;
			return ParseString(value.stringValue, error);
		}
		if (input_[position_] < '0' || input_[position_] > '9')
			return Fail(error, ProcessErrorCode::MalformedJson, "request values must be strings or unsigned integers");
		const std::size_t start = position_;
		while (position_ < input_.size() && input_[position_] >= '0' && input_[position_] <= '9')
			++position_;
		const auto number = input_.substr(start, position_ - start);
		std::uint64_t parsed = 0;
		const auto result = std::from_chars(number.data(), number.data() + number.size(), parsed);
		if (result.ec != std::errc {} || result.ptr != number.data() + number.size())
			return Fail(error, ProcessErrorCode::InvalidField, "unsigned request value is out of range");
		value.kind = JsonScalar::Kind::Unsigned;
		value.unsignedValue = parsed;
		return true;
	}

	bool ParseString(std::string &result, ProcessProtocolError &error)
	{
		if (!Consume('"'))
			return Fail(error, ProcessErrorCode::MalformedJson, "request string is missing");
		result.clear();
		while (position_ < input_.size()) {
			const unsigned char character = static_cast<unsigned char>(input_[position_++]);
			if (character == '"')
				return true;
			if (character < 0x20)
				return Fail(error, ProcessErrorCode::MalformedJson, "control character in request string");
			if (character != '\\') {
				result.push_back(static_cast<char>(character));
				continue;
			}
			if (position_ >= input_.size())
				return Fail(error, ProcessErrorCode::MalformedJson, "request string escape is incomplete");
			const char escaped = input_[position_++];
			switch (escaped) {
			case '"':
			case '\\':
			case '/':
				result.push_back(escaped);
				break;
			case 'b':
				result.push_back('\b');
				break;
			case 'f':
				result.push_back('\f');
				break;
			case 'n':
				result.push_back('\n');
				break;
			case 'r':
				result.push_back('\r');
				break;
			case 't':
				result.push_back('\t');
				break;
			case 'u':
				if (!ParseUnicodeEscape(result, error))
					return false;
				break;
			default:
				return Fail(error, ProcessErrorCode::MalformedJson, "unsupported request string escape");
			}
		}
		return Fail(error, ProcessErrorCode::MalformedJson, "request string is incomplete");
	}

	static int HexDigit(char value)
	{
		if (value >= '0' && value <= '9')
			return value - '0';
		if (value >= 'a' && value <= 'f')
			return value - 'a' + 10;
		if (value >= 'A' && value <= 'F')
			return value - 'A' + 10;
		return -1;
	}

	bool ParseUnicodeEscape(std::string &result, ProcessProtocolError &error)
	{
		auto parseUnit = [this, &error](std::uint16_t &unit) {
			if (position_ + 4 > input_.size())
				return Fail(error, ProcessErrorCode::MalformedJson, "unicode escape is incomplete");
			unit = 0;
			for (std::size_t index = 0; index < 4; ++index) {
				const int digit = HexDigit(input_[position_ + index]);
				if (digit < 0)
					return Fail(error, ProcessErrorCode::MalformedJson, "unicode escape is invalid");
				unit = static_cast<std::uint16_t>((unit << 4) | digit);
			}
			position_ += 4;
			return true;
		};

		std::uint16_t unit = 0;
		if (!parseUnit(unit))
			return false;
		std::uint32_t codePoint = unit;
		if (unit >= 0xD800 && unit <= 0xDBFF) {
			if (position_ + 6 > input_.size() || input_[position_] != '\\'
			    || input_[position_ + 1] != 'u')
				return Fail(error, ProcessErrorCode::MalformedJson, "unicode surrogate pair is incomplete");
			position_ += 2;
			std::uint16_t low = 0;
			if (!parseUnit(low) || low < 0xDC00 || low > 0xDFFF)
				return Fail(error, ProcessErrorCode::MalformedJson, "unicode surrogate pair is invalid");
			codePoint = 0x10000U + ((static_cast<std::uint32_t>(unit) - 0xD800U) << 10U)
			    + (static_cast<std::uint32_t>(low) - 0xDC00U);
		} else if (unit >= 0xDC00 && unit <= 0xDFFF) {
			return Fail(error, ProcessErrorCode::MalformedJson, "unicode low surrogate is invalid");
		}

		if (codePoint <= 0x7FU) {
			result.push_back(static_cast<char>(codePoint));
		} else if (codePoint <= 0x7FFU) {
			result.push_back(static_cast<char>(0xC0U | (codePoint >> 6U)));
			result.push_back(static_cast<char>(0x80U | (codePoint & 0x3FU)));
		} else if (codePoint <= 0xFFFFU) {
			result.push_back(static_cast<char>(0xE0U | (codePoint >> 12U)));
			result.push_back(static_cast<char>(0x80U | ((codePoint >> 6U) & 0x3FU)));
			result.push_back(static_cast<char>(0x80U | (codePoint & 0x3FU)));
		} else {
			result.push_back(static_cast<char>(0xF0U | (codePoint >> 18U)));
			result.push_back(static_cast<char>(0x80U | ((codePoint >> 12U) & 0x3FU)));
			result.push_back(static_cast<char>(0x80U | ((codePoint >> 6U) & 0x3FU)));
			result.push_back(static_cast<char>(0x80U | (codePoint & 0x3FU)));
		}
		return true;
	}

	std::string_view input_;
	std::size_t position_ {};
};

bool Fail(ProcessProtocolError &error, ProcessErrorCode code, std::string message)
{
	error.code = code;
	error.message = std::move(message);
	return false;
}

bool GetString(
	const std::map<std::string, JsonScalar> &fields,
	std::string_view name,
	std::string &value,
	ProcessProtocolError &error)
{
	const auto found = fields.find(std::string(name));
	if (found == fields.end())
		return Fail(error, ProcessErrorCode::MissingField, "missing request field: " + std::string(name));
	if (found->second.kind != JsonScalar::Kind::String)
		return Fail(error, ProcessErrorCode::InvalidField, "request field must be a string: " + std::string(name));
	value = found->second.stringValue;
	if (value.empty())
		return Fail(error, ProcessErrorCode::InvalidField, "request field must not be empty: " + std::string(name));
	return true;
}

bool GetUnsigned(
	const std::map<std::string, JsonScalar> &fields,
	std::string_view name,
	std::uint64_t &value,
	ProcessProtocolError &error)
{
	const auto found = fields.find(std::string(name));
	if (found == fields.end())
		return Fail(error, ProcessErrorCode::MissingField, "missing request field: " + std::string(name));
	if (found->second.kind != JsonScalar::Kind::Unsigned)
		return Fail(error, ProcessErrorCode::InvalidField, "request field must be an unsigned integer: " + std::string(name));
	value = found->second.unsignedValue;
	return true;
}

bool HasExactFields(
	const std::map<std::string, JsonScalar> &fields,
	std::initializer_list<std::string_view> expected,
	ProcessProtocolError &error)
{
	for (const auto &field : fields) {
		if (std::find(expected.begin(), expected.end(), field.first) == expected.end())
			return Fail(error, ProcessErrorCode::UnknownField, "unknown request field: " + field.first);
	}
	return true;
}

bool RequireDigest(std::string_view value, ProcessProtocolError &error)
{
	if (value.size() != 64
	    || std::any_of(value.begin(), value.end(), [](char character) {
			return !((character >= '0' && character <= '9') || (character >= 'a' && character <= 'f'));
		}))
		return Fail(error, ProcessErrorCode::InvalidField, "candidate_set_sha256 must be lowercase SHA-256");
	return true;
}

void AppendFingerprintPart(std::ostringstream &output, std::string_view value)
{
	output << value.size() << ':' << value << '|';
}

} // namespace

const char *ProcessErrorCodeName(ProcessErrorCode code)
{
	switch (code) {
	case ProcessErrorCode::MalformedUtf8:
		return "MALFORMED_UTF8";
	case ProcessErrorCode::MalformedJson:
		return "MALFORMED_JSON";
	case ProcessErrorCode::OversizedFrame:
		return "OVERSIZED_FRAME";
	case ProcessErrorCode::UnknownMessageType:
		return "UNKNOWN_MESSAGE_TYPE";
	case ProcessErrorCode::UnknownField:
		return "UNKNOWN_FIELD";
	case ProcessErrorCode::MissingField:
		return "MISSING_FIELD";
	case ProcessErrorCode::InvalidField:
		return "INVALID_FIELD";
	case ProcessErrorCode::ProtocolVersionMismatch:
		return "PROTOCOL_VERSION_MISMATCH";
	case ProcessErrorCode::RequestIdReuse:
		return "REQUEST_ID_REUSE";
	case ProcessErrorCode::RequestIdExpired:
		return "REQUEST_ID_EXPIRED";
	case ProcessErrorCode::InvalidState:
		return "INVALID_STATE";
	case ProcessErrorCode::EngineFaulted:
		return "ENGINE_FAULTED";
	case ProcessErrorCode::StaleEpisode:
		return "STALE_EPISODE";
	case ProcessErrorCode::StaleStep:
		return "STALE_STEP";
	case ProcessErrorCode::StateMismatch:
		return "STATE_MISMATCH";
	case ProcessErrorCode::InvalidCandidate:
		return "INVALID_CANDIDATE";
	case ProcessErrorCode::NoSupportedCandidates:
		return "NO_SUPPORTED_CANDIDATES";
	case ProcessErrorCode::EngineFault:
		return "ENGINE_FAULT";
	case ProcessErrorCode::AssetDataUnavailable:
		return "ASSET_DATA_UNAVAILABLE";
	case ProcessErrorCode::EngineInitializationFailed:
		return "ENGINE_INITIALIZATION_FAILED";
	case ProcessErrorCode::ObservationContractFailed:
		return "OBSERVATION_CONTRACT_FAILED";
	case ProcessErrorCode::CandidateRejected:
		return "CANDIDATE_REJECTED";
	case ProcessErrorCode::ActionResolutionFailed:
		return "ACTION_RESOLUTION_FAILED";
	case ProcessErrorCode::StaleCandidate:
		return "STALE_CANDIDATE";
	case ProcessErrorCode::Internal:
		return "INTERNAL";
	}
	return "INTERNAL";
}

ReadLineResult ReadProcessLine(std::istream &input, std::string &line, ProcessProtocolError &error)
{
	line.clear();
	bool readAny = false;
	bool oversized = false;
	std::size_t length = 0;
	for (;;) {
		const int next = input.get();
		if (next == std::char_traits<char>::eof()) {
			if (!readAny)
				return ReadLineResult::Eof;
			if (oversized) {
				Fail(error, ProcessErrorCode::OversizedFrame, "process frame exceeds 1 MiB");
				return ReadLineResult::Error;
			}
			return ReadLineResult::Line;
		}
		readAny = true;
		const char character = static_cast<char>(next);
		if (character == '\n') {
			if (oversized) {
				Fail(error, ProcessErrorCode::OversizedFrame, "process frame exceeds 1 MiB");
				return ReadLineResult::Error;
			}
			return ReadLineResult::Line;
		}
		++length;
		if (length > kMaxProcessFrameBytes) {
			oversized = true;
			continue;
		}
		line.push_back(character);
	}
}

bool ParseProcessRequest(std::string_view line, ProcessRequest &request, ProcessProtocolError &error)
{
	if (line.size() > kMaxProcessFrameBytes)
		return Fail(error, ProcessErrorCode::OversizedFrame, "process frame exceeds 1 MiB");
	if (!IsValidUtf8(line))
		return Fail(error, ProcessErrorCode::MalformedUtf8, "process frame is not valid UTF-8");
	std::map<std::string, JsonScalar> fields;
	JsonReader reader(line);
	if (!reader.ParseObject(fields, error) || !reader.AtEnd()) {
		if (error.message.empty())
			return Fail(error, ProcessErrorCode::MalformedJson, "process frame has trailing data");
		return false;
	}
	std::string type;
	if (!GetString(fields, "type", type, error))
		return false;
	std::string protocolVersion;
	if (!GetString(fields, "protocol_version", protocolVersion, error))
		return false;
	if (protocolVersion != kProcessProtocolVersion)
		return Fail(error, ProcessErrorCode::ProtocolVersionMismatch, "unsupported process protocol version");
	std::uint64_t requestId = 0;
	if (!GetUnsigned(fields, "request_id", requestId, error))
		return false;
	request = {};
	request.requestId = requestId;
	if (type == "health_request") {
		if (!HasExactFields(fields, { "type", "protocol_version", "request_id" }, error))
			return false;
		request.type = ProcessRequestType::Health;
		return true;
	}
	if (type == "reset_request") {
		if (!HasExactFields(fields, { "type", "protocol_version", "request_id", "seed", "task_id" }, error))
			return false;
		request.type = ProcessRequestType::Reset;
		if (!GetUnsigned(fields, "seed", request.seed, error))
			return false;
		if (request.seed > std::numeric_limits<std::uint32_t>::max())
			return Fail(error, ProcessErrorCode::InvalidField, "seed must fit in uint32_t");
		return GetString(fields, "task_id", request.taskId, error);
	}
	if (type != "step_request")
		return Fail(error, ProcessErrorCode::UnknownMessageType, "unsupported process request type");
	if (!HasExactFields(
			fields,
			{ "type", "protocol_version", "request_id", "episode_id", "expected_step_id", "candidate_id", "candidate_set_sha256" },
			error))
		return false;
	request.type = ProcessRequestType::Step;
	if (!GetString(fields, "episode_id", request.episodeId, error))
		return false;
	if (!GetUnsigned(fields, "expected_step_id", request.expectedStepId, error))
		return false;
	std::uint64_t candidateId = 0;
	if (!GetUnsigned(fields, "candidate_id", candidateId, error))
		return false;
	if (candidateId > std::numeric_limits<std::uint32_t>::max())
		return Fail(error, ProcessErrorCode::InvalidField, "candidate_id must fit in uint32_t");
	request.candidateId = static_cast<std::uint32_t>(candidateId);
	if (!GetString(fields, "candidate_set_sha256", request.candidateSetSha256, error))
		return false;
	return RequireDigest(request.candidateSetSha256, error);
}

std::string ProcessRequest::Fingerprint() const
{
	std::ostringstream result;
	AppendFingerprintPart(result, type == ProcessRequestType::Health
	                              ? "health_request"
	                              : type == ProcessRequestType::Reset ? "reset_request" : "step_request");
	AppendFingerprintPart(result, kProcessProtocolVersion);
	result << requestId << '|';
	if (type == ProcessRequestType::Reset) {
		result << seed << '|';
		AppendFingerprintPart(result, taskId);
	} else if (type == ProcessRequestType::Step) {
		AppendFingerprintPart(result, episodeId);
		result << expectedStepId << '|' << candidateId << '|';
		AppendFingerprintPart(result, candidateSetSha256);
	}
	return result.str();
}

RequestCache::RequestCache(std::size_t maxEntries)
	: maxEntries_(maxEntries)
{
	if (maxEntries_ == 0)
		maxEntries_ = 1;
}

bool RequestCache::ReplayOrMiss(
	std::uint64_t requestId,
	std::string_view fingerprint,
	std::string &response,
	ProcessProtocolError &error) const
{
	const auto found = entries_.find(requestId);
	if (found != entries_.end()) {
		if (found->second.fingerprint != fingerprint) {
			error = { ProcessErrorCode::RequestIdReuse, "request_id was already used with a different payload" };
			return false;
		}
		response = found->second.response;
		return true;
	}
	if (hasHighestRequestId_ && requestId <= highestRequestId_) {
		error = { ProcessErrorCode::RequestIdExpired, "request_id is older than the bounded request cache" };
	}
	return false;
}

bool RequestCache::Remember(
	std::uint64_t requestId,
	std::string_view fingerprint,
	std::string_view response,
	ProcessProtocolError &error)
{
	const auto found = entries_.find(requestId);
	if (found != entries_.end()) {
		if (found->second.fingerprint != fingerprint) {
			error = { ProcessErrorCode::RequestIdReuse, "request_id was already used with a different payload" };
			return false;
		}
		return true;
	}
	if (hasHighestRequestId_ && requestId <= highestRequestId_) {
		error = { ProcessErrorCode::RequestIdExpired, "request_id must increase monotonically after eviction" };
		return false;
	}
	highestRequestId_ = requestId;
	hasHighestRequestId_ = true;
	entries_.emplace(requestId, Entry { std::string(fingerprint), std::string(response) });
	insertionOrder_.push_back(requestId);
	while (entries_.size() > maxEntries_) {
		const std::uint64_t oldest = insertionOrder_.front();
		insertionOrder_.pop_front();
		entries_.erase(oldest);
	}
	return true;
}

bool ProcessLifecycle::BeginEpisode(
	std::string_view episodeId,
	std::string_view candidateSetSha256,
	ProcessProtocolError &error)
{
	if (state_ != ProcessState::Ready)
		return Fail(error, ProcessErrorCode::InvalidState, "worker already has an episode");
	if (episodeId.empty() || candidateSetSha256.empty())
		return Fail(error, ProcessErrorCode::InvalidField, "episode identity is incomplete");
	state_ = ProcessState::EpisodeActive;
	episodeId_ = episodeId;
	stepId_ = 0;
	candidateSetSha256_ = candidateSetSha256;
	return true;
}

bool ProcessLifecycle::ValidateStep(
	std::string_view episodeId,
	std::uint64_t expectedStepId,
	std::string_view candidateSetSha256,
	ProcessProtocolError &error) const
{
	if (state_ == ProcessState::Faulted)
		return Fail(error, ProcessErrorCode::EngineFaulted, "worker is faulted");
	if (state_ != ProcessState::EpisodeActive)
		return Fail(error, ProcessErrorCode::InvalidState, "worker has no active episode");
	if (episodeId != episodeId_)
		return Fail(error, ProcessErrorCode::StaleEpisode, "episode_id is stale");
	if (expectedStepId != stepId_)
		return Fail(error, ProcessErrorCode::StaleStep, "expected_step_id is stale");
	if (candidateSetSha256 != candidateSetSha256_)
		return Fail(error, ProcessErrorCode::StateMismatch, "candidate-set identity differs");
	return true;
}

bool ProcessLifecycle::CompleteStep(
	std::string_view episodeId,
	std::uint64_t nextStepId,
	std::string_view candidateSetSha256,
	ProcessProtocolError &error)
{
	if (state_ != ProcessState::EpisodeActive || episodeId != episodeId_)
		return Fail(error, ProcessErrorCode::InvalidState, "cannot complete an inactive episode");
	if (nextStepId != stepId_ + 1)
		return Fail(error, ProcessErrorCode::InvalidState, "step_id must increment exactly once");
	stepId_ = nextStepId;
	candidateSetSha256_ = candidateSetSha256;
	return true;
}

} // namespace dxai_bridge
