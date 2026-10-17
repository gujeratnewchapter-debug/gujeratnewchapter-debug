'use client';

import { useEffect, useState } from 'react';
import { getFeatureFlags } from './api';

const SESSION_CACHE_KEY = 'ess-feature-flags';

function readSessionCache(): Record<string, boolean> | null {
  if (typeof window === 'undefined') return null;
  try {
    const raw = window.sessionStorage.getItem(SESSION_CACHE_KEY);
    if (!raw) return null;
    const parsed: unknown = JSON.parse(raw);
    if (!parsed || typeof parsed !== 'object' || Array.isArray(parsed)) return null;
    return Object.fromEntries(
      Object.entries(parsed).filter((entry): entry is [string, boolean] => typeof entry[1] === 'boolean'),
    );
  } catch {
    return null;
  }
}

let sessionFlags = readSessionCache();
let flagsRequest: Promise<Record<string, boolean>> | null = null;

function loadFeatureFlags(): Promise<Record<string, boolean>> {
  if (!flagsRequest) {
    flagsRequest = getFeatureFlags()
      .then(({ data }) => data)
      .catch((error: unknown) => {
        console.error('Failed to load feature flags:', error);
        return {};
      })
      .then((flags) => {
        sessionFlags = flags;
        try {
          window.sessionStorage.setItem(SESSION_CACHE_KEY, JSON.stringify(flags));
        } catch (error) {
          console.warn('Could not cache feature flags for this session:', error);
        }
        return flags;
      });
  }
  return flagsRequest;
}

export function useFeatureFlagStatus(
  key: string,
  shouldLoad = true,
): { enabled: boolean; loading: boolean } {
  const [enabled, setEnabled] = useState(() => sessionFlags?.[key] ?? false);

  useEffect(() => {
    if (!shouldLoad) {
      setEnabled(false);
      return;
    }
    if (sessionFlags) {
      setEnabled(sessionFlags[key] ?? false);
      return;
    }
    let active = true;
    loadFeatureFlags().then((flags) => {
      if (active) setEnabled(flags[key] ?? false);
    });
    return () => {
      active = false;
    };
  }, [key, shouldLoad]);

  return {
    enabled: shouldLoad && (sessionFlags ? sessionFlags[key] ?? false : enabled),
    loading: shouldLoad && sessionFlags === null,
  };
}

export function useFeatureFlag(key: string, shouldLoad = true): boolean {
  return useFeatureFlagStatus(key, shouldLoad).enabled;
}
