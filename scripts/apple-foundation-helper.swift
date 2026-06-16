import Foundation

struct HelperInput: Decodable {
    struct ChatMessage: Decodable {
        let role: String
        let content: String
        let model: String?
    }

    let systemPrompt: String
    let messages: [ChatMessage]
    let options: [String: JSONValue]

    enum CodingKeys: String, CodingKey {
        case systemPrompt = "system_prompt"
        case messages
        case options
    }
}

enum JSONValue: Decodable {
    case string(String)
    case number(Double)
    case bool(Bool)
    case array([JSONValue])
    case object([String: JSONValue])
    case null

    init(from decoder: Decoder) throws {
        let container = try decoder.singleValueContainer()
        if container.decodeNil() {
            self = .null
        } else if let value = try? container.decode(Bool.self) {
            self = .bool(value)
        } else if let value = try? container.decode(Double.self) {
            self = .number(value)
        } else if let value = try? container.decode(String.self) {
            self = .string(value)
        } else if let value = try? container.decode([JSONValue].self) {
            self = .array(value)
        } else {
            self = .object(try container.decode([String: JSONValue].self))
        }
    }

    var doubleValue: Double? {
        if case .number(let value) = self {
            return value
        }
        return nil
    }

    var intValue: Int? {
        guard let value = doubleValue else {
            return nil
        }
        return Int(value)
    }
}

func printJSON(_ object: [String: Any]) {
    let data = try! JSONSerialization.data(withJSONObject: object, options: [])
    FileHandle.standardOutput.write(data)
    FileHandle.standardOutput.write("\n".data(using: .utf8)!)
}

func readInput() throws -> HelperInput {
    let data = FileHandle.standardInput.readDataToEndOfFile()
    return try JSONDecoder().decode(HelperInput.self, from: data)
}

func flattenedPrompt(from messages: [HelperInput.ChatMessage]) -> String {
    messages.map { message in
        let role = message.role == "assistant" ? "Assistant" : "User"
        return "\(role): \(message.content)"
    }.joined(separator: "\n\n")
}

#if canImport(FoundationModels)
import FoundationModels

@available(macOS 26.0, iOS 26.0, *)
func runFoundationModels() async -> Int32 {
    if CommandLine.arguments.contains("--doctor") {
        let model = SystemLanguageModel.default
        switch model.availability {
        case .available:
            printJSON(["ok": true, "message": "Apple Foundation Model is available."])
            return 0
        default:
            printJSON(["ok": false, "error": "Apple Foundation Model is not available on this device/user/locale."])
            return 1
        }
    }

    do {
        let input = try readInput()
        let prompt = flattenedPrompt(from: input.messages)
        let model = SystemLanguageModel.default
        let session = LanguageModelSession(model: model, instructions: input.systemPrompt)

        var options = GenerationOptions()
        if let temperature = input.options["temperature"]?.doubleValue {
            options.temperature = temperature
        }
        if let maxTokens = input.options["maximum_response_tokens"]?.intValue {
            options.maximumResponseTokens = maxTokens
        }

        let response = try await session.respond(to: prompt, options: options)
        printJSON(["ok": true, "content": response.content])
        return 0
    } catch {
        printJSON(["ok": false, "error": String(describing: error)])
        return 1
    }
}

if #available(macOS 26.0, iOS 26.0, *) {
    exit(await runFoundationModels())
} else {
    printJSON(["ok": false, "error": "FoundationModels requires a supported Apple Intelligence OS."])
    exit(1)
}
#else
if CommandLine.arguments.contains("--doctor") {
    print("FoundationModels framework is not present in this Swift SDK.")
    exit(1)
}
printJSON(["ok": false, "error": "FoundationModels framework is not present in this Swift SDK. Build this helper with a supported Apple SDK."])
exit(1)
#endif
