// Copyright 2026 Google LLC
//
// Licensed under the Apache License, Version 2.0 (the "License");
// you may not use this file except in compliance with the License.
// You may obtain a copy of the License at
//
//      http://www.apache.org/licenses/LICENSE-2.0
//
// Unless required by applicable law or agreed to in writing, software
// distributed under the License is distributed on an "AS IS" BASIS,
// WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
// See the License for the specific language governing permissions and
// limitations under the License.

#include <gtest/gtest.h>
#include "a2ui/parser/parser.h"
#include "a2ui/parser/streaming.h"
#include "a2ui/schema/validator.h"
#include "a2ui/schema/catalog.h"
#include "a2ui/parser/payload_fixer.h"

#include "test_utils.h"
#include <filesystem>
#include <yaml-cpp/yaml.h>
#include <nlohmann/json.hpp>
#include <algorithm>
#include <regex>

#include <cctype>

namespace fs = std::filesystem;

namespace {
using namespace a2ui::tests;

inline std::string strip(const std::string& s) {
    auto start = std::find_if_not(s.begin(), s.end(), [](unsigned char ch) { return std::isspace(ch); });
    auto end = std::find_if_not(s.rbegin(), s.rend(), [](unsigned char ch) { return std::isspace(ch); }).base();
    return (start < end) ? std::string(start, end) : "";
}

// --- Validator Conformance ---

TEST(ValidatorConformanceTest, RunAll) {
    fs::path repo_root = find_repo_root();
    ASSERT_FALSE(repo_root.empty()) << "Could not find repo root";
    
    fs::path conformance_dir = repo_root / "agent_sdks" / "conformance";
    fs::path validator_tests_path = conformance_dir / "validator.yaml";
    
    YAML::Node yaml_tests = YAML::LoadFile(validator_tests_path.string());
    nlohmann::json tests = yaml_to_json(yaml_tests);
    
    for (const auto& test_case : tests) {
        std::string name = test_case["name"];
        SCOPED_TRACE("Test case: " + name);
        
        nlohmann::json catalog_config = test_case["catalog"];
        a2ui::A2uiCatalog catalog = setup_catalog(catalog_config, conformance_dir);
        a2ui::A2uiValidator validator(catalog);
        
        for (const auto& step : test_case["validate"]) {
            nlohmann::json payload = step["payload"];
            
            if (step.contains("expect_error")) {
                EXPECT_THROW(validator.validate(payload), std::runtime_error);
            } else {
                EXPECT_NO_THROW(validator.validate(payload));
            }
        }
    }
}

// --- Catalog Conformance ---
TEST(CatalogConformanceTest, RunAll) {
    fs::path repo_root = find_repo_root();
    ASSERT_FALSE(repo_root.empty()) << "Could not find repo root";
    
    fs::path conformance_dir = repo_root / "agent_sdks" / "conformance";
    fs::path catalog_tests_path = conformance_dir / "catalog.yaml";
    
    YAML::Node yaml_tests = YAML::LoadFile(catalog_tests_path.string());
    nlohmann::json tests = yaml_to_json(yaml_tests);
    
    for (const auto& test_case : tests) {
        std::string name = test_case["name"];
        SCOPED_TRACE("Test case: " + name);
        
        if (name == "test_load_examples_validation_fails_on_schema_error") {
            std::cout << "[SKIPPED] Validation failure test in C++: " << name << std::endl;
            continue;
        }
        
        nlohmann::json catalog_config = test_case["catalog"];

        a2ui::A2uiCatalog catalog = setup_catalog(catalog_config, conformance_dir);
        std::string action = test_case["action"];
        nlohmann::json args = test_case.contains("args") ? test_case["args"] : nlohmann::json::object();
        
        if (action == "prune") {
            std::vector<std::string> allowed_components;
            if (args.contains("allowed_components")) {
                allowed_components = args["allowed_components"].get<std::vector<std::string>>();
            }
            std::vector<std::string> allowed_messages;
            if (args.contains("allowed_messages")) {
                allowed_messages = args["allowed_messages"].get<std::vector<std::string>>();
            }
            
            auto pruned = std::move(catalog).with_pruning(allowed_components, allowed_messages);

            nlohmann::json expected = test_case["expect"];
            
            if (expected.contains("catalog_schema")) {
                EXPECT_EQ(pruned.catalog_schema(), expected["catalog_schema"]);
            }
            if (expected.contains("s2c_schema")) {
                EXPECT_EQ(pruned.s2c_schema(), expected["s2c_schema"]);
            }
            if (expected.contains("common_types_schema")) {
                EXPECT_EQ(pruned.common_types_schema(), expected["common_types_schema"]);
            }
        } else if (action == "render") {
            std::string output = catalog.render_as_llm_instructions();
            std::string expected_output = test_case["expect_output"];
            
            // Normalize whitespace for comparison
            std::string output_norm = std::regex_replace(strip(output), std::regex("\\s+"), " ");
            std::string expected_norm = std::regex_replace(strip(expected_output), std::regex("\\s+"), " ");
            
            EXPECT_EQ(output_norm, expected_norm);
        } else if (action == "load") {
            std::string path = "";
            if (args.contains("path") && !args["path"].is_null()) {
                path = args["path"].get<std::string>();
            }
            
            // Skip glob tests in C++ as it doesn't support them
            if (path.find('*') != std::string::npos || path.find('[') != std::string::npos) {
                std::cout << "[SKIPPED] Glob test in C++: " << name << std::endl;
                continue;
            }
            
            std::string full_path = "";
            if (!path.empty()) {
                full_path = (conformance_dir / path).string();
            }
            bool validate = args.value("validate", false);
            
            if (test_case.contains("expect_error")) {
                EXPECT_THROW(catalog.load_examples(full_path, validate), std::runtime_error);
            } else {
                std::string output = catalog.load_examples(full_path, validate);
                std::string expected_output = test_case["expect_output"];
                
                // Normalize whitespace for comparison
                std::string output_norm = std::regex_replace(strip(output), std::regex("\\s+"), " ");
                std::string expected_norm = std::regex_replace(strip(expected_output), std::regex("\\s+"), " ");

                
                EXPECT_EQ(output_norm, expected_norm);
            }
        }

    }
}


// --- Streaming Parser Conformance (v0.8) ---
TEST(StreamingParserConformanceTest, RunV08) {
    fs::path repo_root = find_repo_root();
    ASSERT_FALSE(repo_root.empty()) << "Could not find repo root";
    
    fs::path conformance_dir = repo_root / "agent_sdks" / "conformance";
    fs::path parser_tests_path = conformance_dir / "streaming_parser.yaml";
    
    YAML::Node yaml_tests = YAML::LoadFile(parser_tests_path.string());
    nlohmann::json tests = yaml_to_json(yaml_tests);
    
    for (const auto& test_case : tests) {
        std::string name = test_case["name"];
        if (name.find("_v08") == std::string::npos) {
            continue;
        }
        SCOPED_TRACE("Test case: " + name);
        
        nlohmann::json catalog_config = test_case["catalog"];
        a2ui::A2uiCatalog catalog = setup_catalog(catalog_config, conformance_dir);
        auto parser = a2ui::A2uiStreamParser::create(catalog);
        
        for (const auto& step : test_case["process_chunk"]) {
            std::string input = step["input"];
            
            if (step.contains("expect_error")) {
                EXPECT_THROW(parser->process_chunk(input), std::runtime_error);
            } else {
                auto parts = parser->process_chunk(input);
                nlohmann::json expected = step["expect"];
                
                ASSERT_EQ(parts.size(), expected.size());
                for (size_t i = 0; i < parts.size(); ++i) {
                    EXPECT_EQ(parts[i].text, expected[i].value("text", ""));
                    if (expected[i].contains("a2ui")) {
                        ASSERT_TRUE(parts[i].a2ui_json.has_value());
                        EXPECT_EQ(*parts[i].a2ui_json, expected[i]["a2ui"]);
                    } else {
                        EXPECT_FALSE(parts[i].a2ui_json.has_value());
                    }
                }
            }
        }
    }
}

// --- Streaming Parser Conformance (v0.9) ---
TEST(StreamingParserConformanceTest, RunV09) {
    fs::path repo_root = find_repo_root();
    ASSERT_FALSE(repo_root.empty()) << "Could not find repo root";
    
    fs::path conformance_dir = repo_root / "agent_sdks" / "conformance";
    fs::path parser_tests_path = conformance_dir / "streaming_parser.yaml";
    
    YAML::Node yaml_tests = YAML::LoadFile(parser_tests_path.string());
    nlohmann::json tests = yaml_to_json(yaml_tests);
    
    for (const auto& test_case : tests) {
        std::string name = test_case["name"];
        if (name.find("_v09") == std::string::npos) {
            continue;
        }
        SCOPED_TRACE("Test case: " + name);
        
        nlohmann::json catalog_config = test_case["catalog"];
        a2ui::A2uiCatalog catalog = setup_catalog(catalog_config, conformance_dir);
        auto parser = a2ui::A2uiStreamParser::create(catalog);
        
        for (const auto& step : test_case["process_chunk"]) {
            std::string input = step["input"];
            
            if (step.contains("expect_error")) {
                EXPECT_THROW(parser->process_chunk(input), std::runtime_error);
            } else {
                auto parts = parser->process_chunk(input);
                nlohmann::json expected = step["expect"];
                
                ASSERT_EQ(parts.size(), expected.size());
                for (size_t i = 0; i < parts.size(); ++i) {
                    EXPECT_EQ(parts[i].text, expected[i].value("text", ""));
                    if (expected[i].contains("a2ui")) {
                        ASSERT_TRUE(parts[i].a2ui_json.has_value());
                        EXPECT_EQ(*parts[i].a2ui_json, expected[i]["a2ui"]);
                    } else {
                        EXPECT_FALSE(parts[i].a2ui_json.has_value());
                    }
                }
            }
        }
    }
}

// --- Non-Streaming Parser Conformance ---
TEST(ParserConformanceTest, RunNonStreaming) {
    fs::path repo_root = find_repo_root();
    ASSERT_FALSE(repo_root.empty()) << "Could not find repo root";
    
    fs::path conformance_dir = repo_root / "agent_sdks" / "conformance";
    fs::path parser_tests_path = conformance_dir / "parser.yaml";
    
    YAML::Node yaml_tests = YAML::LoadFile(parser_tests_path.string());
    nlohmann::json tests = yaml_to_json(yaml_tests);
    
    for (const auto& test_case : tests) {
        std::string name = test_case["name"];
        std::string action = test_case.value("action", "parse_full");
        
        if (action != "parse_full" && action != "has_parts" && action != "fix_payload") {
            continue;
        }
        SCOPED_TRACE("Test case: " + name);
        
        std::string input = test_case["input"];
        
        if (action == "parse_full") {
            if (test_case.contains("expect_error")) {
                EXPECT_THROW(a2ui::parse_response(input), std::runtime_error);
            } else {
                auto parts = a2ui::parse_response(input);
                nlohmann::json expected = test_case["expect"];
                
                ASSERT_EQ(parts.size(), expected.size());
                for (size_t i = 0; i < parts.size(); ++i) {
                    std::string actual_text = parts[i].text;
                    actual_text.erase(actual_text.begin(), std::find_if(actual_text.begin(), actual_text.end(), [](unsigned char ch) {
                        return !std::isspace(ch);
                    }));
                    actual_text.erase(std::find_if(actual_text.rbegin(), actual_text.rend(), [](unsigned char ch) {
                        return !std::isspace(ch);
                    }).base(), actual_text.end());
                    
                    std::string expected_text = expected[i].value("text", "");
                    expected_text.erase(expected_text.begin(), std::find_if(expected_text.begin(), expected_text.end(), [](unsigned char ch) {
                        return !std::isspace(ch);
                    }));
                    expected_text.erase(std::find_if(expected_text.rbegin(), expected_text.rend(), [](unsigned char ch) {
                        return !std::isspace(ch);
                    }).base(), expected_text.end());

                    EXPECT_EQ(actual_text, expected_text);
                    
                    if (expected[i].contains("a2ui")) {
                        ASSERT_TRUE(parts[i].a2ui_json.has_value());
                        EXPECT_EQ(*parts[i].a2ui_json, expected[i]["a2ui"]);
                    } else {
                        EXPECT_FALSE(parts[i].a2ui_json.has_value());
                    }
                }
            }
        } else if (action == "has_parts") {
            bool expected = test_case["expect"];
            EXPECT_EQ(a2ui::has_a2ui_parts(input), expected);
        } else if (action == "fix_payload") {
            nlohmann::json expected = test_case["expect"];
            nlohmann::json result = a2ui::parse_and_fix(input);
            EXPECT_EQ(result, expected);
        }
    }


}

} // namespace
