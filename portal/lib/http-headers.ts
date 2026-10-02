export function normalizePublicEnvironmentValue(
  value: string | undefined,
  name: string,
): string | undefined {
  if (value === undefined) return undefined;

  const normalized = value.replace(/^\uFEFF+|\uFEFF+$/g, '');
  if (normalized !== value && process.env.NODE_ENV === 'development') {
    console.warn(`Removed a UTF-8 BOM from ${name}. Check the deployment environment value.`);
  }
  return normalized;
}

export function assertValidHttpHeaderValue(name: string, value: string) {
  const invalidCharacter = Array.from(value).find((character) => {
    const codePoint = character.codePointAt(0)!;
    return !(codePoint === 0x09
      || codePoint >= 0x20 && codePoint <= 0x7e
      || codePoint >= 0x80 && codePoint <= 0xff);
  });

  if (invalidCharacter) {
    const codePoint = invalidCharacter.codePointAt(0)!.toString(16).toUpperCase().padStart(4, '0');
    throw new Error(`Request header "${name}" contains an invalid character (U+${codePoint})`);
  }
}
