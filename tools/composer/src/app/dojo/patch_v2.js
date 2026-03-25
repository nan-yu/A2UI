/**
 * Copyright 2026 Google LLC
 *
 * Licensed under the Apache License, Version 2.0 (the "License");
 * you may not use this file except in compliance with the License.
 * You may obtain a copy of the License at
 *
 *     http://www.apache.org/licenses/LICENSE-2.0
 *
 * Unless required by applicable law or agreed to in writing, software
 * distributed under the License is distributed on an "AS IS" BASIS,
 * WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
 * See the License for the specific language governing permissions and
 * limitations under the License.
 */

const fs = require('fs');
const file = 'page.tsx';
let content = fs.readFileSync(file, 'utf8');

const target = `    messages: (scenarios[selectedScenario] as any) || [],
    autoPlay: false,
    baseIntervalMs: 1000
  });`;

const replacement = `    messages: (scenarios[selectedScenario] as any) || [],
    autoPlay: false,
    baseIntervalMs: 1000
  });

  useEffect(() => {
    const params = new URLSearchParams(window.location.search);
    const step = params.get('step');
    if (step) {
      seek(parseInt(step, 10));
    }
  }, []);`;

content = content.replace(target, replacement);
fs.writeFileSync(file, content);
console.log("Patched page.tsx with basic ?step=N support.");
