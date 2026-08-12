#include <cstdint>
#include <iostream>
#include <sstream>
#include <stdexcept>
#include <string>

#include "dxai_bridge/process_protocol.hpp"

namespace {

using dxai_bridge::ProcessErrorCode;

void Require(bool condition, const char *message)
{
    if (!condition)
        throw std::runtime_error(message);
}

void RequireError(
    const dxai_bridge::ProcessProtocolError &error,
    ProcessErrorCode expected,
    const char *message)
{
    Require(error.code == expected, message);
}

void TestStrictRequests()
{
    dxai_bridge::ProcessRequest request;
    dxai_bridge::ProcessProtocolError error;
    Require(
        dxai_bridge::ParseProcessRequest(
            R"({"type":"health_request","protocol_version":"dxai.process.v1","request_id":7})",
            request,
            error),
        "valid health request must parse");
    Require(request.requestId == 7, "request ID must parse");

    Require(
        dxai_bridge::ParseProcessRequest(
            R"({"type":"reset_request","protocol_version":"dxai.process.v1","request_id":8,"seed":123,"task_id":"\u0063ombat.single_melee.v0"})",
            request,
            error),
        "valid unicode escape must parse");
    Require(request.taskId == "combat.single_melee.v0", "unicode escape must decode");

    Require(
        !dxai_bridge::ParseProcessRequest(
            R"({"type":"health_request","protocol_version":"dxai.process.v1","request_id":7,"extra":1})",
            request,
            error),
        "unknown field must be rejected");
    RequireError(error, ProcessErrorCode::UnknownField, "unknown field error must be structured");

    Require(
        !dxai_bridge::ParseProcessRequest(
            R"({"type":"health_request","protocol_version":"dxai.process.v1","request_id":7,"request_id":8})",
            request,
            error),
        "duplicate field must be rejected");
    RequireError(error, ProcessErrorCode::MalformedJson, "duplicate field error must be structured");

    Require(
        !dxai_bridge::ParseProcessRequest(
            R"({"type":"health_request","protocol_version":"dxai.process.v0","request_id":7})",
            request,
            error),
        "wrong process version must be rejected");
    RequireError(error, ProcessErrorCode::ProtocolVersionMismatch, "wrong version error must be structured");

    Require(
        !dxai_bridge::ParseProcessRequest(
            R"({"type":"health_request","protocol_version":"dxai.process.v1","request_id":})",
            request,
            error),
        "malformed JSON must be rejected");
    RequireError(error, ProcessErrorCode::MalformedJson, "malformed JSON error must be structured");
}

void TestLineReader()
{
    std::string line;
    dxai_bridge::ProcessProtocolError error;
    std::istringstream input(
        "{\"type\":\"health_request\",\"protocol_version\":\"dxai.process.v1\",\"request_id\":1}\n");
    Require(
        dxai_bridge::ReadProcessLine(input, line, error) == dxai_bridge::ReadLineResult::Line,
        "a complete line must be read");
    Require(!line.empty(), "read line must not be empty");
    Require(
        dxai_bridge::ReadProcessLine(input, line, error) == dxai_bridge::ReadLineResult::Eof,
        "EOF must be reported cleanly");

    std::string oversized(dxai_bridge::kMaxProcessFrameBytes + 1, 'x');
    oversized.push_back('\n');
    std::istringstream oversizedInput(oversized);
    Require(
        dxai_bridge::ReadProcessLine(oversizedInput, line, error) == dxai_bridge::ReadLineResult::Error,
        "oversized line must be rejected");
    RequireError(error, ProcessErrorCode::OversizedFrame, "oversized line error must be structured");

    std::string invalidUtf8 = "{\"type\":\"health_request\",\"protocol_version\":\"dxai.process.v1\",\"request_id\":1,\"x\":\"";
    invalidUtf8.push_back(static_cast<char>(0xFF));
    invalidUtf8 += "\"}\n";
    std::istringstream invalidInput(invalidUtf8);
    Require(
        dxai_bridge::ReadProcessLine(invalidInput, line, error) == dxai_bridge::ReadLineResult::Line,
        "UTF-8 validation belongs to request parsing");
    dxai_bridge::ProcessRequest parsedRequest;
    Require(
        !dxai_bridge::ParseProcessRequest(line, parsedRequest, error),
        "invalid UTF-8 request must be rejected");
    RequireError(error, ProcessErrorCode::MalformedUtf8, "invalid UTF-8 error must be structured");
}

void TestRequestCache()
{
    dxai_bridge::RequestCache cache(2);
    dxai_bridge::ProcessProtocolError error;
    Require(cache.Remember(1, "a", "response-a", error), "first request must be cached");
    Require(cache.Remember(2, "b", "response-b", error), "second request must be cached");
    std::string response;
    Require(cache.ReplayOrMiss(1, "a", response, error), "exact duplicate must replay");
    Require(response == "response-a", "duplicate must return original response");
    Require(!cache.Remember(1, "changed", "response", error), "changed duplicate must be rejected");
    RequireError(error, ProcessErrorCode::RequestIdReuse, "changed duplicate error must be structured");
    Require(cache.Remember(3, "c", "response-c", error), "third request must evict oldest");
    Require(!cache.ReplayOrMiss(1, "a", response, error), "evicted request must not replay");
    RequireError(error, ProcessErrorCode::RequestIdExpired, "evicted request must be expired");
}

void TestLifecycle()
{
    dxai_bridge::ProcessLifecycle lifecycle;
    dxai_bridge::ProcessProtocolError error;
    Require(
        !lifecycle.ValidateStep("episode-a", 0, "hash-a", error),
        "step before reset must be rejected");
    RequireError(error, ProcessErrorCode::InvalidState, "pre-reset state error must be structured");
    Require(lifecycle.BeginEpisode("episode-a", "hash-a", error), "reset must activate episode");
    Require(lifecycle.ValidateStep("episode-a", 0, "hash-a", error), "current step must validate");
    Require(lifecycle.CompleteStep("episode-a", 1, "hash-b", error), "step must complete once");
    Require(lifecycle.stepId() == 1, "step ID must increment exactly once");
    Require(
        !lifecycle.ValidateStep("episode-a", 0, "hash-b", error),
        "stale step must be rejected");
    RequireError(error, ProcessErrorCode::StaleStep, "stale step error must be structured");
    lifecycle.Fault();
    Require(
        !lifecycle.ValidateStep("episode-a", 1, "hash-b", error),
        "faulted worker must reject steps");
    RequireError(error, ProcessErrorCode::EngineFaulted, "fault error must be structured");
}

} // namespace

int main()
{
    try {
        TestStrictRequests();
        TestLineReader();
        TestRequestCache();
        TestLifecycle();
        std::cout << "dxai process protocol OK\n";
        return 0;
    } catch (const std::exception &error) {
        std::cerr << error.what() << '\n';
        return 1;
    }
}
