export type HomeNoticesCallout = {
  visible: boolean;
  label: string;
  pulse: boolean;
};

const DEFAULT_CALLOUT: HomeNoticesCallout = {
  visible: true,
  label: 'New',
  pulse: true,
};

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === 'object' && value !== null && !Array.isArray(value);
}

export function getHomeNoticesCallout(content: unknown, lang = 'en'): HomeNoticesCallout {
  const rootContent = isRecord(content) ? content : {};
  const localizedContent = isRecord(rootContent[lang]) ? rootContent[lang] : rootContent;
  const configured = localizedContent.notices_callout ?? rootContent.notices_callout;
  const settings = isRecord(configured) ? configured : {};
  const configuredLabel = typeof settings.label === 'string' ? settings.label.trim() : '';

  return {
    visible: settings.visible !== false,
    label: configuredLabel || DEFAULT_CALLOUT.label,
    pulse: settings.pulse !== false,
  };
}
