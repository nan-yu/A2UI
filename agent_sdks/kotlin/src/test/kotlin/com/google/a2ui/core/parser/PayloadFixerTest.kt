/*
 * Copyright 2026 Google LLC
 *
 * Licensed under the Apache License, Version 2.0 (the "License");
 * you may not use this file except in compliance with the License.
 * You may obtain a copy of the License at
 *
 *      https://www.apache.org/licenses/LICENSE-2.0
 *
 * Unless required by applicable law or agreed to in writing, software
 * distributed under the License is distributed on an "AS IS" BASIS,
 * WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
 * See the License for the specific language governing permissions and
 * limitations under the License.
 */

package com.google.a2ui.core.parser

import kotlin.test.Test
import kotlin.test.assertEquals
import kotlin.test.assertFailsWith
import kotlinx.serialization.json.jsonArray
import kotlinx.serialization.json.jsonObject
import kotlinx.serialization.json.jsonPrimitive

class PayloadFixerTest {

  @Test
  fun arrayWithTrailingCommas_commasRemoved() {
    val invalidJson =
      """
            [
              {"foo": "bar"},
              {"foo": "baz"},
            ]
        """
        .trimIndent()
    val result = PayloadFixer.parseAndFix(invalidJson)
    assertEquals(2, result.size)
  }

  @Test
  fun objectWithTrailingCommas_commasRemoved() {
    val invalidJson =
      """
            {
              "foo": "bar",
              "foo2": "baz",
            }
        """
        .trimIndent()
    val result = PayloadFixer.parseAndFix(invalidJson)
    assertEquals(1, result.size)
  }

  @Test
  fun edgeCasesWithTrailingCommas_commasRemoved() {
    assertEquals("""{"a": 1}""", PayloadFixer.removeTrailingCommas("""{"a": 1,}"""))
    assertEquals("""[1, 2, 3]""", PayloadFixer.removeTrailingCommas("""[1, 2, 3,]"""))
    assertEquals("""{"a": [1, 2]}""", PayloadFixer.removeTrailingCommas("""{"a": [1, 2,]}"""))
  }

  @Test
  fun commasInStrings_notRemoved() {
    val jsonWithCommasInStrings = """{"text": "Hello, world", "array": ["a,b", "c"]}"""
    assertEquals(
      jsonWithCommasInStrings,
      PayloadFixer.removeTrailingCommas(jsonWithCommasInStrings),
    )

    val trickyJson = """{"text": "Ends with comma,]"}"""
    assertEquals(trickyJson, PayloadFixer.removeTrailingCommas(trickyJson))
  }

  @Test
  fun validJson_remainsUntouched() {
    val validJson = """[{"foo": "bar"}]"""
    val result = PayloadFixer.parseAndFix(validJson)
    assertEquals(1, result.size)
  }

  @Test
  fun unrecoverableJson_throwsException() {
    val badJson = "not_json_at_all"
    assertFailsWith<IllegalArgumentException> { PayloadFixer.parseAndFix(badJson) }
  }

  @Test
  fun normalizeSmartQuotes_replacesQuotesCorrectly() {
    val input = "“smart” ‘quotes’"
    val expected = "\"smart\" 'quotes'"
    assertEquals(expected, PayloadFixer.normalizeSmartQuotes(input))
  }

  @Test
  fun fixPathsForV08_prependsSlashToRelativePaths() {
    val input =
      """
      {
        "surfaceUpdate": {
          "components": [
            {
              "id": "root",
              "component": {
                "Text": {
                  "text": { "path": "some/relative/path" }
                }
              }
            }
          ]
        }
      }
    """
        .trimIndent()
    val parsed = kotlinx.serialization.json.Json.parseToJsonElement(input)
    val fixed = PayloadFixer.fixPathsForV08(parsed)
    val expectedPath =
      fixed.jsonObject["surfaceUpdate"]
        ?.jsonObject
        ?.get("components")
        ?.jsonArray
        ?.get(0)
        ?.jsonObject
        ?.get("component")
        ?.jsonObject
        ?.get("Text")
        ?.jsonObject
        ?.get("text")
        ?.jsonObject
        ?.get("path")
        ?.jsonPrimitive
        ?.content

    assertEquals("/some/relative/path", expectedPath)
  }
}
