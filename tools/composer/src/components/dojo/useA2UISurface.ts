import { useMemo } from 'react';
import { transpileToV0_8 } from '@/lib/transcoder';

export interface ComponentInstance {
  id: string;
  component: Record<string, any>;
}

export interface A2UISurfaceState {
  root: string;
  components: ComponentInstance[];
  data: Record<string, any>;
}

export function useA2UISurface(messages: any[]): A2UISurfaceState {
  return useMemo(() => {
    let root = "root";
    const componentsMap = new Map<string, ComponentInstance>();
    let data: Record<string, any> = {};

    for (const msg of messages) {
      if (!msg) continue;
      const v0_8msg = transpileToV0_8(msg);

      // Handle beginRendering
      if (v0_8msg.beginRendering) {
        root = v0_8msg.beginRendering.root || "root";
      }

      // Handle surfaceUpdate
      if (v0_8msg.surfaceUpdate) {
        const newComponents = v0_8msg.surfaceUpdate.components || [];
        for (const rawComp of newComponents) {
          if (rawComp.id) {
            let normalizedComp: ComponentInstance;
            
            if (rawComp.component) {
              // Already in v0.8 format
              normalizedComp = {
                id: rawComp.id,
                component: rawComp.component
              };
            } else if (rawComp.type) {
              // v0.9-ish format (type/props) -> convert to v0.8 component map
              normalizedComp = {
                id: rawComp.id,
                component: {
                  [rawComp.type]: rawComp.props || {}
                }
              };
            } else {
              // Fallback or unknown format
              normalizedComp = {
                id: rawComp.id,
                component: rawComp
              };
            }
            
            componentsMap.set(rawComp.id, normalizedComp);
          }
        }
      }

      // Handle dataModelUpdate
      if (v0_8msg.dataModelUpdate) {
        const updates = v0_8msg.dataModelUpdate.contents || [];
        for (const update of updates) {
          const path = v0_8msg.dataModelUpdate.path || "/";
          if (path === "/" || !path) {
            data = { ...data, ...update };
          } else {
            // Simple path handling: "foo/bar" -> data.foo.bar
            const parts = path.split('/').filter(Boolean);
            let current = data;
            for (let i = 0; i < parts.length - 1; i++) {
              const part = parts[i];
              if (!current[part]) current[part] = {};
              current = current[part];
            }
            current[parts[parts.length - 1]] = update;
          }
        }
      }
    }

    return {
      root,
      components: Array.from(componentsMap.values()),
      data,
    };
  }, [messages]);
}
